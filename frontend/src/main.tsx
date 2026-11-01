import React from 'react';
import ReactDOM from 'react-dom/client';
import { BrowserRouter,NavLink,Routes,Route,Navigate,useNavigate } from 'react-router-dom';
import { QueryClient,QueryClientProvider,useQuery,useQueryClient } from '@tanstack/react-query';
import { FlaskConical,LayoutDashboard,UserRound,NotebookPen,Utensils,ChartNoAxesCombined,History,LogOut,ArrowUpRight } from 'lucide-react';
import { api,ApiError } from './api';
import { ErrorBox,Loading } from './components';
import { Auth,Dashboard,ProfilePage } from './pages/home';
import { Diary } from './pages/diary';
import { Recommendations,Research,HistoryPage } from './pages/results';
import styles from './App.module.css';
import './theme.css';
const client=new QueryClient({defaultOptions:{queries:{retry:(count,error)=>!(error instanceof ApiError&&error.status<500)&&count<1,refetchOnWindowFocus:false}}});
function App(){
 const cache=useQueryClient(),navigate=useNavigate();
 const user=useQuery({queryKey:['me'],queryFn:()=>api('/auth/me'),retry:false});
 if(user.isPending)return <Loading/>;
 if(!user.error&&!user.data)return <Auth/>;
 if(user.error){if(user.error instanceof ApiError&&user.error.status===401)return <Auth/>;return <main className="connection-error"><h1>AmritAHARA is reconnecting</h1><ErrorBox error={user.error}/><button onClick={()=>user.refetch()}>Try again</button><p>Check that the local API and database are running.</p></main>}
 const links=[['/','Overview',LayoutDashboard],['/profile','My profile',UserRound],['/diary','Diet diary',NotebookPen],['/recommendations','Recommendations',Utensils],['/research','Research analysis',ChartNoAxesCombined],['/history','Run history',History]] as const;
 return <div className={styles.shell}><aside className={styles.sidebar}><NavLink to="/" className="brand"><div className="brand-mark"><FlaskConical size={23}/></div><div>AmritAHARA<small>NUTRITION RESEARCH</small></div></NavLink><div className="nav-caption">WORKSPACE</div><nav>{links.map(([path,label,Icon])=><NavLink key={path} to={path} end={path==='/'}><Icon size={18}/>{label}</NavLink>)}</nav><div className="sidebar-note"><span className="dot"/> Knowledge-grounded planning<p>Indian food composition.<br/>Personalized Pareto optimization.</p><small>Research application · v1.0</small></div><div className="account"><div className="avatar">{user.data.name.slice(0,1).toUpperCase()}</div><div><strong>{user.data.name}</strong><small>{user.data.email}</small></div><button aria-label="Sign out" className="icon-button" onClick={async()=>{await api('/auth/logout','POST');cache.clear();cache.setQueryData(['me'],null);navigate('/');window.location.reload()}}><LogOut size={17}/></button></div></aside><div className={styles.workspace}><div className="topbar"><span><span className="dot"/> PERSONALIZED NUTRITION WORKSPACE</span><span title="Research outputs are model-based, not clinical prescriptions">Academic research edition</span></div><main className={styles.content}><Routes><Route path="/" element={<Dashboard user={user.data}/>}/><Route path="/profile" element={<ProfilePage/>}/><Route path="/diary" element={<Diary/>}/><Route path="/recommendations/:id?" element={<Recommendations/>}/><Route path="/research/:id?" element={<Research/>}/><Route path="/history" element={<HistoryPage/>}/><Route path="*" element={<Navigate to="/"/>}/></Routes><footer className="page-footer"><span>AmritAHARA / KNOWLEDGE-GROUNDED OPTIMIZATION</span><span>Research recommendations, not clinical prescriptions.</span></footer></main></div></div>
}
ReactDOM.createRoot(document.getElementById('root')!).render(<React.StrictMode><QueryClientProvider client={client}><BrowserRouter><App/></BrowserRouter></QueryClientProvider></React.StrictMode>);

