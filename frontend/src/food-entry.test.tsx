// @vitest-environment jsdom
import React,{useState} from 'react';
import { beforeAll,afterEach,it,expect } from 'vitest';
import { render,screen,fireEvent,cleanup } from '@testing-library/react';
import { MealEditor } from './food-entry';
import { DietComparison } from './diet-comparison';
import { Food } from './api';
beforeAll(()=>{HTMLDialogElement.prototype.showModal=function(){this.setAttribute('open','')};HTMLDialogElement.prototype.close=function(){this.removeAttribute('open')}});
afterEach(cleanup);
const food={food_code:'IDLI',food_name:'Idli',servings_unit:'idli',energy_kcal:34} as Food;
function Editor(){const [items,setItems]=useState<{food_code:string;servings:number}[]>([]);return <MealEditor meal="breakfast" foods={[food,{...food,food_code:'DOSA',food_name:'Plain dosa'}]} items={items} onChange={setItems}/>}
it('adds directly from search, adjusts portions and removes the food',()=>{
 render(<Editor/>);
 fireEvent.click(screen.getByRole('button',{name:'Add food'}));
 fireEvent.change(screen.getByRole('searchbox'),{target:{value:'idli'}});
 expect(screen.queryByRole('combobox')).toBeNull();
 expect(screen.queryByRole('button',{name:'Add Plain dosa to breakfast'})).toBeNull();
 fireEvent.click(screen.getByRole('button',{name:'Add Idli to breakfast'}));
 expect((screen.getByRole('spinbutton',{name:'Servings of Idli'}) as HTMLInputElement).value).toBe('1');
 fireEvent.click(screen.getByRole('button',{name:'Increase Idli'}));
 expect((screen.getByRole('spinbutton',{name:'Servings of Idli'}) as HTMLInputElement).value).toBe('1.25');
 expect(screen.queryByRole('button',{name:'Add Idli to breakfast'})).toBeNull();
 fireEvent.click(screen.getByRole('button',{name:'Remove Idli'}));
 expect(screen.queryByRole('spinbutton',{name:'Servings of Idli'})).toBeNull();
});
const item=(code:string,servings=1)=>({food_code:code,food_name:code,servings,serving_unit:'bowl'});
it('keeps search in a dialog and closes it without changing recorded foods',()=>{
 render(<Editor/>);
 fireEvent.click(screen.getByRole('button',{name:'Add food'}));
 expect(screen.getByRole('dialog',{name:'Add food to breakfast'})).toBeTruthy();
 expect(document.activeElement).toBe(screen.getByRole('searchbox'));
 fireEvent.change(screen.getByRole('searchbox'),{target:{value:'no match'}});
 expect(screen.getByText(/No matching foods/)).toBeTruthy();
 fireEvent.click(screen.getByRole('button',{name:'Close'}));
 expect(screen.queryByRole('dialog')).toBeNull();
 expect(screen.queryByRole('spinbutton')).toBeNull();
});
it('shows complete current and suggested meals without action labels',()=>{
 const totals={energy_kcal:2000,protein_g:90,fibre_g:30};
 render(<DietComparison input={{day:{label:'Day 1'},input_totals:totals,targets:totals,input_diet:{breakfast:[item('Rice'),item('Dal')]}}} recommendation={{totals,diet:{breakfast:[item('Rice'),item('Dal',2)]}}}/>);
 expect(screen.getAllByText('Rice')).toHaveLength(2);
 expect(screen.getAllByText('Dal')).toHaveLength(2);
 expect(screen.getByText('2 bowl')).toBeTruthy();
 expect(screen.queryByRole('checkbox')).toBeNull();
 expect(screen.queryByText('Adjust portion')).toBeNull();
 expect(screen.getAllByText('Current diet')).toHaveLength(1);
 expect(screen.getAllByText('Suggested diet')).toHaveLength(2);
});
