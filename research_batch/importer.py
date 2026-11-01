"""Conservative import: unresolved food/quantity/profile records block that respondent."""
import csv
import hashlib
import json
import math
from collections import Counter, defaultdict
from pathlib import Path
from pydantic import ValidationError
from backend.schemas import ProfileInput
from src.full_catalog import load_full_catalog
from src.nutrient_targets import calculate_nutrient_targets
from research_batch.common import digest, read_json, write_json

ACTIVITY = {'Sedentary':1.2, 'Lightly active':1.375, 'Moderately active':1.55,
            'Very active':1.725, 'Extremely active':1.9}
GOALS = {'Weight maintenance':'maintenance', 'Weight gain':'weight_gain', 'Weight loss':'weight_loss'}
FILES = ['participants.csv','food_logs.csv','custom_foods.csv','export_errors.csv']


def read_csv(path):
    with Path(path).open(encoding='utf-8-sig', newline='') as f:
        return list(csv.DictReader(f))


def import_export(source, workspace, corrections_path=None, adjustment=300, restriction_policy='acknowledge-unmodelled'):
    source, workspace = Path(source), Path(workspace)
    tables = {name:read_csv(source/name) for name in FILES}
    participants = tables['participants.csv']
    if any(not p.get('response_id') for p in participants):
        raise ValueError('Participant rows must have response_id')
    ids = [p['response_id'] for p in participants]
    if len(ids)!=len(set(ids)):
        raise ValueError('Duplicate response_id in participants.csv; reconcile the export first')
    logs = defaultdict(list)
    for row in tables['food_logs.csv']:
        logs[row['response_id']].append(row)
    unknown = set(logs)-set(ids)
    if unknown:
        raise ValueError(f'{len(unknown)} food-log identities have no participant in this export')
    # custom_foods is a detail view of CUSTOM rows, never a second set of foods.
    key = lambda r:(r['response_id'],r['meal'],r['entry_index'])
    log_by_key = {key(r):r for r in tables['food_logs.csv']}
    if len(log_by_key)!=len(tables['food_logs.csv']):
        raise ValueError('Duplicate meal/entry keys in food_logs.csv')
    custom_issues = defaultdict(list)
    for row in tables['custom_foods.csv']:
        original = log_by_key.get(key(row))
        if not original or any(row.get(k)!=original.get(k) for k in ('source','food_name','quantity','serving_unit')):
            custom_issues[row['response_id']].append('custom_foods detail does not match food_logs')
    if set(custom_issues)-set(ids):
        raise ValueError('Orphan custom food details in export')
    export_errors = defaultdict(list)
    for row in tables['export_errors.csv']:
        if row.get('response_id') not in set(ids):
            raise ValueError('Unassigned export error; resolve export_errors.csv before import')
        export_errors[row['response_id']].append(row.get('reason','unspecified export error'))
    corrections = read_json(corrections_path, {}) if corrections_path else {}
    if set(corrections)-set(ids):
        raise ValueError('Corrections contain response IDs absent from this export')
    catalog = load_full_catalog()[0].set_index('food_code').to_dict('index')
    registry = read_json(workspace/'registry.json', {'version':1,'participants':{}})
    audit, issues, food_review, templates = [], [], [], {}
    export_hashes = {n:hashlib.sha256((source/n).read_bytes()).hexdigest() for n in FILES}
    for p in participants:
        identity = p['response_id']
        participant = 'p_'+hashlib.sha256(identity.encode()).hexdigest()[:20]
        correction = corrections.get(identity, {})
        reasons = list(custom_issues[identity])+['export error: '+x for x in export_errors[identity]]
        warnings = []
        if correction and not correction.get('reason','').strip():
            reasons.append('correction requires an explicit reason/source')
        if set(correction)-{'reason','profile','entries','skip_policy','replace_logs'}:
            reasons.append('unknown correction field')
        profile = dict(age=p.get('age'), sex=p.get('sex'), height_cm=p.get('height_cm'), weight_kg=p.get('weight_kg'),
                       activity_factor=ACTIVITY.get(p.get('activity')), goal=GOALS.get(p.get('goal')),
                       calorie_adjustment=adjustment)
        profile.update(correction.get('profile', {}))
        try:
            profile = ProfileInput(**profile).model_dump()
            targets = calculate_nutrient_targets(profile)
            if any(not math.isfinite(v) or v<=0 for v in targets.values()):
                reasons.append('profile produces a non-positive nutrient target')
        except ValidationError as e:
            reasons.extend('profile '+'.'.join(str(v) for v in x['loc'])+': '+x['msg'] for x in e.errors())
            targets = None
        if not p.get('consent_version') or not p.get('consent_timestamp'):
            reasons.append('missing consent metadata')
        restrictions = {k:p.get(k,'') for k in ('diet','foods_avoided','other_avoided')}
        warnings.append('Dietary preferences and avoidances are NOT enforced; research-only benchmark')
        if restriction_policy == 'exclude' and (p.get('diet')!='Non-vegetarian' or p.get('foods_avoided') not in ('','None')):
            reasons.append('dietary restrictions require unsupported food classification')
        order = p.get('meal_order','').split(';')
        try:
            labels = json.loads(p.get('meal_labels','[]'))
            if not order or len(order)!=len(set(order)) or len(order)!=len(labels) or int(p.get('meal_count','0'))!=len(order):
                raise ValueError()
        except (ValueError, TypeError):
            reasons.append('invalid meal order/count/labels')
            labels = order
        skipped = set(filter(None,p.get('skipped_meals','').split(';')))
        if skipped-set(order):
            reasons.append('skipped meal absent from meal_order')
        # Prefix with position so duplicate respondent labels cannot merge meals.
        meal_keys = {m:f'{i+1}. {str(labels[i]).strip() or m}' for i,m in enumerate(order)}
        diet = {m:[] for m in meal_keys.values()}
        entries = correction.get('replace_logs', logs[identity])
        if 'replace_logs' in correction:
            warnings.append('All food logs explicitly replaced by reviewed correction')
        used_corrections = set()
        for entry in entries:
            ek = entry.get('meal','')+':'+str(entry.get('entry_index',''))
            fix = correction.get('entries',{}).get(ek)
            if fix is not None:
                used_corrections.add(ek)
                if not fix.get('reason','').strip():
                    reasons.append(ek+': food correction requires reason/source and unit conversion rationale')
            meal = entry.get('meal')
            if meal not in meal_keys:
                reasons.append(ek+': meal is absent from meal_order')
                continue
            if meal in skipped:
                if correction.get('skip_policy')=='skip-meals':
                    warnings.append(ek+': explicitly discarded because meal marked skipped')
                    continue
                if correction.get('skip_policy')!='recorded-foods':
                    reasons.append(ek+': food recorded in a skipped meal; resolve skip_policy')
            if not fix and str(entry.get('meal_index'))!=str(order.index(meal)):
                reasons.append(ek+': meal_index disagrees with meal_order')
            mapped = fix.get('foods',[]) if fix else [dict(food_code=entry.get('food_code'),servings=entry.get('quantity'),unit=entry.get('serving_unit'))]
            if fix and not mapped:
                reasons.append(ek+': a food entry cannot be silently dropped; supply its resolved foods')
            for item in mapped:
                code = item.get('food_code')
                error = None
                if code not in catalog:
                    error = 'custom/unavailable food requires reviewed catalogue mapping'
                else:
                    try:
                        amount = float(item.get('servings'))
                        if not math.isfinite(amount) or not 0<amount<=20:
                            raise ValueError()
                        if not fix and str(item.get('unit','')).strip().lower()!=catalog[code]['servings_unit']:
                            error = 'serving unit mismatch; explicit conversion required'
                    except (TypeError, ValueError):
                        error = 'invalid quantity (expected 0 < servings <= 20)'
                if error:
                    reasons.append(ek+': '+error)
                    food_review.append(dict(participant=participant,response_id=identity,entry_key=ek,
                                            food_code=entry.get('food_code'),food_name=entry.get('food_name'),
                                            quantity=entry.get('quantity'),unit=entry.get('serving_unit'),reason=error))
                else:
                    diet[meal_keys[meal]].append(dict(food_code=code,servings=amount))
        if set(correction.get('entries',{}))-used_corrections:
            reasons.append('unused entry correction key; check meal:entry_index')
        for meal, foods in diet.items():
            merged = defaultdict(float)
            for f in foods:
                merged[f['food_code']] += f['servings']
            diet[meal] = [dict(food_code=c,servings=q) for c,q in merged.items()]
            if any(q>20 for q in merged.values()):
                reasons.append(meal+': merged quantity exceeds 20 servings')
        if not any(diet.values()):
            reasons.append('no usable recorded foods')
        empty_unskipped = [m for m in order if not diet[meal_keys[m]] and m not in skipped]
        if empty_unskipped:
            reasons.append('unskipped meals without usable foods: '+','.join(empty_unskipped))
        if sum(len(fs)+2 for fs in diet.values() if fs)>256:
            reasons.append('day exceeds 256 search slots')
        reasons = list(dict.fromkeys(reasons))
        case = dict(participant=participant,profile=profile,targets=targets,diet=diet,
                    restrictions=restrictions,restriction_policy=restriction_policy,calorie_adjustment_policy=adjustment,
                    survey_metadata={k:p.get(k) for k in ('schema_version','catalog_version','day_type','day_representativeness','pattern')},
                    correction=correction,warnings=warnings)
        case_hash = digest(case)
        case.update(case_hash=case_hash,status='blocked' if reasons else 'ready',issues=reasons)
        # The active registry is updated, old case versions and results remain intact.
        write_json(workspace/'cases'/f'{participant}_{case_hash}.json', case)
        registry['participants'][participant] = dict(case_hash=case_hash,status=case['status'])
        audit.append(dict(participant=participant,response_id=identity,status=case['status'],issues=' | '.join(reasons),
                          meals=len(diet),food_entries=sum(map(len,diet.values()))))
        for reason in reasons:
            issues.append(dict(participant=participant,response_id=identity,reason=reason))
        if reasons:
            templates[identity] = correction or dict(reason='',profile={},entries={})
    write_json(workspace/'registry.json',registry)
    write_json(workspace/'audit'/'corrections.template.json',templates)
    for name, rows, fields in [('participants',audit,['participant','response_id','status','issues','meals','food_entries']),
                               ('issues',issues,['participant','response_id','reason']),
                               ('food_review',food_review,['participant','response_id','entry_key','food_code','food_name','quantity','unit','reason'])]:
        with (workspace/'audit'/f'{name}.csv').open('w',encoding='utf-8',newline='') as f:
            writer=csv.DictWriter(f,fieldnames=fields);writer.writeheader();writer.writerows(rows)
    summary = dict(imported=len(participants),ready=sum(x['status']=='ready' for x in audit),blocked=sum(x['status']=='blocked' for x in audit),
                   registered_total=len(registry['participants']),source_hashes=export_hashes,restriction_policy=restriction_policy,
                   calorie_adjustment=adjustment,issue_counts=dict(Counter(x['reason'] for x in issues)))
    write_json(workspace/'audit'/'summary.json',summary)
    write_json(workspace/'imports'/f'{digest(export_hashes)}.json',dict(source_hashes=export_hashes,corrections=corrections,summary=summary))
    return summary
