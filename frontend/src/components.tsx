import { useEffect,useRef } from 'react';
import { AlertCircle,CheckCircle2,Clock3,LoaderCircle } from 'lucide-react';
import { format,nutrients } from './api';

export function Notice({children,kind='info'}:{children:React.ReactNode;kind?:string}){return <div role={kind==='error'?'alert':undefined} className={'notice '+kind}><AlertCircle size={18}/><div>{children}</div></div>}
export function Loading(){return <div className="loading" role="status"><LoaderCircle className="spin" size={20}/> Loading your workspace…</div>}
export function ErrorBox({error}:{error:any}){return <Notice kind="error">{error?.message||'Something went wrong.'}</Notice>}
export function PageTitle({eyebrow,title,description,action}:{eyebrow:string;title:string;description:string;action?:React.ReactNode}){return <header className="page-title"><div><div className="eyebrow">{eyebrow}</div><h1>{title}</h1><p>{description}</p></div>{action}</header>}
export function Badge({status}:{status:string}){return <span className={'badge '+status}>{status==='completed'?<CheckCircle2 size={12}/>:status==='running'?<LoaderCircle size={12} className="spin"/>:<Clock3 size={12}/>} {status.replaceAll('_',' ')}</span>}
export function Stat({label,value,detail}:{label:string;value:React.ReactNode;detail?:string}){return <div className="stat"><span>{label}</span><strong>{value}</strong>{detail&&<small>{detail}</small>}</div>}
export function Nutrition({totals,targets}:{totals:any;targets:any}){return <div className="nutrition">{Object.entries(nutrients).map(([key,label])=><div key={key}><div><span>{label}</span><strong>{format(totals?.[key],1)} <small>/ {format(targets?.[key],1)}</small></strong></div><div className="meter"><i style={{width:Math.min(100,100*(totals?.[key]||0)/(targets?.[key]||1))+'%'}}/></div></div>)}</div>}
export function MealFoods({foods}:{foods:any[]}){return <ul className="food-list">{foods?.filter(f=>f.food_code!=='NONE').map((f,i)=><li key={i}><span>{f.food_name}</span><strong>{format(f.servings)} {f.serving_unit}</strong></li>)}{!foods?.filter(f=>f.food_code!=='NONE').length&&<li className="muted">No food recorded</li>}</ul>}
export function Chart({data,title,xlabel,ylabel,onPoint}:{data:any[];title:string;xlabel:string;ylabel:string;onPoint?:(index:number)=>void}){
 const el=useRef<HTMLDivElement>(null);
 useEffect(()=>{let disposed=false;let plot:any; const render=async()=>{const module=await import('plotly.js-dist-min');plot=module.default; if(disposed||!el.current)return;
 await plot.newPlot(el.current,data,{title:{text:title,font:{size:15,color:'#253b38'}},font:{family:'Arial, sans-serif',size:12,color:'#596664'},paper_bgcolor:'#fff',plot_bgcolor:'#fff',margin:{t:55,r:25,b:60,l:60},xaxis:{title:{text:xlabel},gridcolor:'#edf0ee',zeroline:false},yaxis:{title:{text:ylabel},gridcolor:'#edf0ee',zeroline:false},colorway:['#245e53','#bc8952','#6c7fa0','#9b5d58','#62733f','#555c73','#918472'],legend:{orientation:'h',y:-.3},autosize:true},{responsive:true,displaylogo:false,modeBarButtonsToRemove:['lasso2d','select2d']});
 if(onPoint)(el.current as any).on('plotly_click',(event:any)=>onPoint(event.points[0].customdata??event.points[0].pointIndex));};render();return()=>{disposed=true;if(plot&&el.current)plot.purge(el.current)}},[data,title,xlabel,ylabel,onPoint]);
 return <div className="chart" ref={el} aria-label={title}/>;
}
