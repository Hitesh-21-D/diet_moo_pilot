import { format,nutrients } from './api';
import { Stat,MealFoods } from './components';

export function DietComparison({input,recommendation}:{input:any;recommendation:any}){
 const mealCount=Object.keys(recommendation.diet).filter(m=>recommendation.diet[m]?.some((f:any)=>f.food_code!=='NONE'&&f.servings>0)).length;
 const before=input.input_totals||{},after=recommendation.totals,targets=input.targets;
 return <><div className="stats-grid user-kpis"><Stat label="Daily energy" value={format(after.energy_kcal,0)+' kcal'} detail={`Your target: ${format(targets.energy_kcal,0)} kcal`}/><Stat label="Daily protein" value={format(after.protein_g,1)+' g'} detail={`Your target: ${format(targets.protein_g,1)} g`}/><Stat label="Daily fibre" value={format(after.fibre_g,1)+' g'} detail={`Your target: ${format(targets.fibre_g,1)} g`}/><Stat label="Meals in your plan" value={mealCount} detail="Your suggested daily meal plan"/></div>
 <section className="panel nutrition-summary"><div className="section-head"><div><span className="eyebrow">YOUR DAY AT A GLANCE</span><h2>How your daily totals change</h2></div></div><div className="table-wrap"><table><thead><tr><th>Nutrient</th><th>Your current diet</th><th>Suggested diet</th><th>Your daily target</th></tr></thead><tbody>{Object.entries(nutrients).map(([key,label])=><tr key={key}><td>{label}</td><td>{format(before[key],1)}</td><td><strong>{format(after[key],1)}</strong>{before[key]!=null&&<small>{after[key]-before[key]>0?'+':''}{format(after[key]-before[key],1)} from current</small>}</td><td>{format(targets[key],1)}</td></tr>)}</tbody></table></div></section>
 <section className="panel side-by-side-plan"><div className="section-head"><div><span className="eyebrow">YOUR MEALS · {input.day.label}</span><h2>Your current and suggested diet</h2><p>Review the complete suggested meals alongside the diet you recorded.</p></div></div>
 {Object.keys(input.input_diet).map(meal=><section className="paired-meal" key={meal}><h3 className="capitalize">{meal}</h3><div className="paired-meal-columns"><div className="current-meal"><span className="meal-column-label">Current diet</span><MealFoods foods={input.input_diet[meal]}/></div><div className="suggested-meal"><span className="meal-column-label">Suggested diet</span><MealFoods foods={recommendation.diet[meal]}/></div></div></section>)}
 </section></>
}
