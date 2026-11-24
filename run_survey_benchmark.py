"""Terminal interface for questionnaire import, resumable benchmarking and reports."""
import argparse
from pathlib import Path
import re
import sys
from research_batch.common import ROOT


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workspace',type=Path,default=ROOT/'.local/survey-benchmark',help='Private local data/checkpoints directory')
    commands=parser.add_subparsers(dest='command',required=True)
    imp=commands.add_parser('import',help='Audit and append/update respondents from an export directory')
    imp.add_argument('--export',type=Path,required=True)
    imp.add_argument('--corrections',type=Path)
    imp.add_argument('--calorie-adjustment',type=float,default=300)
    imp.add_argument('--restriction-policy',choices=['acknowledge-unmodelled','exclude'],default='acknowledge-unmodelled',
                     help='Default explicitly follows the agreed research-only protocol; does NOT enforce avoidances')
    run=commands.add_parser('run',help='Run all six algorithms; completed identical jobs are automatically skipped')
    run.add_argument('--batch',default='full-budget')
    run.add_argument('--budget',type=int,default=15000)
    run.add_argument('--seeds',nargs='+',type=int,default=[42])
    run.add_argument('--limit-participants',type=int,help='Select the first N ready pseudonymous participants for a test')
    run.add_argument('--max-jobs',type=int,help='Stop cleanly after N pending jobs; rerun to continue')
    run.add_argument('--retry-failed',action='store_true')
    run.add_argument('--timeout',type=int,default=1800,help='Seconds per isolated job before marking it failed')
    summary=commands.add_parser('summarize',help='Regenerate aggregate reports from existing checkpoints')
    summary.add_argument('--batch',default='full-budget')
    summary.add_argument('--show-partial',action='store_true',help='Explicitly display provisional metrics for incomplete cohorts')
    commands.add_parser('status',help='Show import eligibility and existing batches')
    worker=commands.add_parser('_worker',help=argparse.SUPPRESS)
    worker.add_argument('request',type=Path)
    args=parser.parse_args(argv)
    from research_batch.runner import exclusive, run_batch, worker as execute_worker
    from research_batch.reporting import summarize
    from research_batch.common import read_json
    if args.command=='_worker':
        execute_worker(args.request);return
    if hasattr(args,'batch') and not re.fullmatch(r'[A-Za-z0-9_-]+',args.batch):
        parser.error('--batch must contain only letters, numbers, underscores and hyphens')
    if args.command=='run':
        if args.budget<100 or len(args.seeds)!=len(set(args.seeds)) or any(s<0 or s>2**32-1 for s in args.seeds):
            parser.error('Use a budget >=100 and distinct unsigned 32-bit seeds')
        if any(v is not None and v<1 for v in (args.limit_participants,args.max_jobs,args.timeout)):
            parser.error('Limits and timeout must be positive')
    if args.command=='import' and not 0<=args.calorie_adjustment<=750:
        parser.error('Calorie adjustment must be between 0 and 750')
    try:
        with exclusive(args.workspace):
            if args.command=='import':
                from research_batch.importer import import_export
                result=import_export(args.export,args.workspace,args.corrections,args.calorie_adjustment,args.restriction_policy)
                print(f"Imported {result['imported']}: {result['ready']} ready, {result['blocked']} blocked; {result['registered_total']} registered.")
                print(f'Audit and correction template: {args.workspace / "audit"}')
                print('No custom foods were guessed; no missing profiles were imputed.')
            elif args.command=='run':
                try:
                    batch=run_batch(args.workspace,args.batch,args.budget,args.seeds,args.limit_participants,args.max_jobs,args.retry_failed,args.timeout)
                except KeyboardInterrupt:
                    print('\nINTERRUPTED (KeyboardInterrupt, usually Ctrl+C). This is not successful batch completion. Completed jobs are saved; the unfinished job will be retried on resume.')
                    summarize(args.workspace/'batches'/args.batch)
                    raise SystemExit(130)
                summarize(batch)
            elif args.command=='summarize':
                summarize(args.workspace/'batches'/args.batch,show_partial=args.show_partial)
            else:
                registry=read_json(args.workspace/'registry.json',{'participants':{}})['participants']
                ready=sum(r['status']=='ready' for r in registry.values())
                print(f'{len(registry)} participants: {ready} ready, {len(registry)-ready} blocked.')
                for p in sorted((args.workspace/'batches').glob('*/protocol.json')):
                    protocol=read_json(p); summary=read_json(p.parent/'reports/summary.json',{})
                    print(p.parent.name,'budget',protocol['budget'],'seeds',protocol['seeds'],'complete participants',summary.get('complete_participants','not summarized'))
    except (ValueError,FileNotFoundError) as e:
        parser.exit(2,f'Error: {e}\n')


if __name__=='__main__':
    main()
