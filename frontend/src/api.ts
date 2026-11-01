export class ApiError extends Error { constructor(public status:number,message:string){super(message)} }
export async function api<T=any>(path:string, method='GET', body?:unknown):Promise<T>{
  const response=await fetch('/api'+path,{method,credentials:'same-origin',headers:{'Content-Type':'application/json','X-DietLab-Request':'1'},body:body===undefined?undefined:JSON.stringify(body)});
  const data=await response.json().catch(()=>({detail:'Unexpected server response'}));
  if(!response.ok) throw new ApiError(response.status,typeof data.detail==='string'?data.detail:Array.isArray(data.detail)?data.detail.map((e:any)=>e.msg).join('; '):'Request failed');
  return data;
}
export const meals=['breakfast','lunch','snack','dinner'] as const;
export const algorithms=['NSGA-II','NSGA-III','MOEA/D','SPEA2','MOPSO','APPO','APPO-NoRepair'];
export const nutrients:Record<string,string>={energy_kcal:'Energy (kcal)',protein_g:'Protein (g)',carb_g:'Carbohydrate (g)',fat_g:'Fat (g)',fibre_g:'Fibre (g)'};
export const format=(value:any,digits=2)=>value==null||!Number.isFinite(Number(value))?'—':Number(value).toLocaleString(undefined,{maximumFractionDigits:digits});
export const dateLabel=(seconds:number)=>new Date(seconds*1000).toLocaleString();
export const active=(status:string)=>['queued','running'].includes(status);
export type Food={food_code:string;food_name:string;servings_unit:string;role:string;energy_kcal:number;protein_g:number;carb_g:number;fat_g:number;fibre_g:number;serving_rule:{min:number;max:number;step:number}};
export type Day={id?:string;label:string;date:string;diet:Record<string,{food_code:string;servings:number}[]>};
