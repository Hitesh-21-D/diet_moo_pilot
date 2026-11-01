// @vitest-environment jsdom
import React from 'react';
import { afterEach,describe,it,expect,vi } from 'vitest';
import { cleanup,render,screen } from '@testing-library/react';
import { MemoryRouter,Routes,Route } from 'react-router-dom';
import { QueryClient,QueryClientProvider } from '@tanstack/react-query';
import { Recommendations } from './pages/results';
import { api } from './api';

vi.mock('./api',async importOriginal=>({...await importOriginal<typeof import('./api')>(),api:vi.fn()}));
afterEach(()=>{cleanup();vi.clearAllMocks()});
const totals={energy_kcal:2100,protein_g:90,carb_g:260,fat_g:70,fibre_g:30};
function mount(id:string){
 return render(<QueryClientProvider client={new QueryClient({defaultOptions:{queries:{retry:false}}})}><MemoryRouter initialEntries={['/recommendations/'+id]}><Routes><Route path="/recommendations/:id" element={<Recommendations/>}/></Routes></MemoryRouter></QueryClientProvider>);
}
describe('per-day recommendation contract',()=>{
 it.each(['day-one','day-two'])('shows only the input and result linked to %s',async(id)=>{
  vi.mocked(api).mockImplementation(async(path)=>{
   if(path==='/experiments')return [{id,label:id,created:1,day_date:'2026-10-31'}];
   if(path==='/experiments/'+id)return {id,runs:[{id:'run-'+id,status:'completed',algorithm:'APPO',seed:42}],snapshot:{day:{label:id,date:'2026-10-31'},profile:{age:30,weight_kg:70,goal:'maintenance'},targets:totals,input_diet:{breakfast:[{food_code:'INPUT',food_name:'Original '+id,servings:1,serving_unit:'bowl'}]}}};
   if(path==='/runs/run-'+id)return {result:{representatives:[{label:'Balanced Compromise',totals,interventions:1,objectives:[1,2,3,4],diet:{breakfast:[{food_code:'OUTPUT',food_name:'Recommended '+id,servings:1,serving_unit:'bowl'}]}}]}};
   throw new Error('Unexpected request '+path);
  });
  mount(id);
  expect(await screen.findByText('Original '+id)).toBeTruthy();
  expect(await screen.findByText('Recommended '+id)).toBeTruthy();
  expect(screen.queryByText('Recommended '+(id==='day-one'?'day-two':'day-one'))).toBeNull();
 });
 it('does not manufacture a recommendation when no feasible diet was found',async()=>{
  vi.mocked(api).mockImplementation(async(path)=>path==='/experiments'?[{id:'none',label:'None',created:1,day_date:'2026-10-31'}]:{runs:[{id:'run-none',status:'no_feasible',algorithm:'APPO',seed:42,progress:15000,budget:15000}],snapshot:{day:{label:'None',date:'2026-10-31'},profile:{age:30,weight_kg:70,goal:'maintenance'},targets:totals}});
  mount('none');
  expect(await screen.findByText(/No feasible recommendations are available/)).toBeTruthy();
  expect(screen.queryByText('33 / 33')).toBeNull();
 });
});
