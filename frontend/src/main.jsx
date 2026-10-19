import React,{useState,useEffect} from 'react';

import {createRoot} from 'react-dom/client';

import './style.css';

const API=import.meta.env.VITE_API_URL||'http://127.0.0.1:8000/api/';

function App(){ 

 const [metrics,setMetrics]=useState(null);

 const [config,setConfig]=useState({departments:[],categories:[]});

 const [editing,setEditing]=useState(false),[success,setSuccess]=useState('');

 const [token,setToken]=useState(sessionStorage.getItem('token')||''),[user,setUser]=useState(null),[page,setPage]=useState('dashboard'),[error,setError]=useState(''),[loading,setLoading]=useState(false),[rows,setRows]=useState([]),[item,setItem]=useState(null),[meta,setMeta]=useState({categories:[],statuses:[],priorities:[],departments:[]}),[people,setPeople]=useState([]),[notes,setNotes]=useState([]),[reply,setReply]=useState(''),[chat,setChat]=useState([]),[search,setSearch]=useState(''),[status,setStatus]=useState(''),[register,setRegister]=useState(false);

 async function api(path,method='GET',data){let r=await fetch(API+path,{method,headers:{Authorization:token?'Token '+token:'','Content-Type':'application/json'},body:data?JSON.stringify(data):undefined});let d=r.status===204?null:await r.json();if(!r.ok)throw Error(typeof d.detail==='string'?d.detail:JSON.stringify(d));return d;}

 async function run(fn){setError('');setLoading(true);try{await fn();}catch(e){setError(e.message);}finally{setLoading(false);}}

 async function load(){setRows(await api('complaints/?search='+encodeURIComponent(search)+'&status='+encodeURIComponent(status)));}

 useEffect(()=>{if(token)run(async()=>{let u=await api('me/');setUser(u);setMeta(await api('metadata/'));await load();if(u.role==='admin')setPeople(await api('users/'));});},[token]);

 async function open(id){setEditing(false);setItem(await api('complaints/'+id+'/'));setPage('detail');}

 function fields(e){return Object.fromEntries(new FormData(e.currentTarget));}

 async function auth(e){e.preventDefault();let data=fields(e);await run(async()=>{let d=await api(register?'register/':'login/','POST',data);sessionStorage.setItem('token',d.token);setToken(d.token);setUser(d.user);});}

 async function logout(){await run(async()=>{await api('logout/','POST');sessionStorage.removeItem('token');setToken('');setUser(null);setItem(null);setPage('dashboard');});}

 const select=(name,values,value)=> <select name={name} defaultValue={value}>{values.map(v=><option key={v} value={v}>{v||'No department'}</option>)}</select>;

 if(!user)return <main className="login"><div className="brand">CS / COMPLAINT SUPPORT</div><h1>{register?'Create your account':'Welcome back'}</h1><p>One place to submit, track and resolve complaints.</p>{error&&<aside role="alert">{error}</aside>}<form onSubmit={auth}><label>Username<input name="username" required maxLength="150" autoComplete="username"/></label>{register&&<label>Email<input name="email" type="email" required/></label>}<label>Password<input name="password" type="password" required minLength={register?8:1} autoComplete={register?'new-password':'current-password'}/></label><button disabled={loading}>{loading?'Please wait…':register?'Register':'Login'}</button></form><button className="secondary" onClick={()=>{setRegister(!register);setError('');}}>{register?'Already have an account? Login':'Create an account'}</button><small>Demo accounts: admin, staff, customer · DemoPass123!</small></main>;

 return <><header><div className="brand">CS / COMPLAINT SUPPORT</div><nav>{['dashboard','new','chat','notifications',...(user.role==='admin'?['users','settings','evaluation']:[])].map(p=><button className={page===p?'active':'ghost'} key={p} onClick={()=>run(async()=>{setPage(p);if(p==='dashboard')await load();if(p==='notifications')setNotes(await api('notifications/'));if(p==='users')setPeople(await api('users/'));if(p==='settings')setConfig(await api('configuration/'));if(p==='evaluation')setMetrics(await api('evaluation/'));})}>{p==='new'?'New complaint':p}</button>)}</nav><span>{user.username} · {user.role}</span><button className="ghost" onClick={logout}>Logout</button></header><main>{success&&<aside className="success" role="status">{success}<button className="link" onClick={()=>setSuccess('')}> Dismiss</button></aside>}{error&&<aside role="alert">{error}</aside>}{loading&&<p aria-live="polite">Loading…</p>}

 {page==='dashboard'&&<><div className="heading"><div><p className="eyebrow">SUPPORT WORKSPACE</p><h1>Complaint dashboard</h1></div><button onClick={()=>setPage('new')}>+ New complaint</button></div><div className="grid">{['Total','Submitted','In Progress','Resolved'].map(s=><section key={s}><b className="number">{s==='Total'?rows.length:rows.filter(r=>r.status===s).length}</b><p>{s}</p></section>)}</div><section><form className="filters" onSubmit={e=>{e.preventDefault();run(load);}}><input placeholder="Search complaints" value={search} onChange={e=>setSearch(e.target.value)}/><select value={status} onChange={e=>setStatus(e.target.value)}><option value="">All statuses</option>{meta.statuses.map(s=><option key={s}>{s}</option>)}</select><button>Search</button></form><p className="muted">Counts reflect the currently filtered list.</p><div className="table"><table><thead><tr><th>Complaint</th><th>Category</th><th>Priority</th><th>Department</th><th>Status</th></tr></thead><tbody>{rows.map(r=><tr key={r.id}><td><button className="link" onClick={()=>run(()=>open(r.id))}>#{r.id} {r.title}</button></td><td>{r.category}</td><td><span className={'badge '+r.priority}>{r.priority}</span></td><td>{r.department}</td><td>{r.status}</td></tr>)}</tbody></table>{!rows.length&&<p>No complaints found. Submit one to get started.</p>}</div>{user.role==='admin'&&<button className="secondary" onClick={()=>run(async()=>{let r=await fetch(API+'export/',{headers:{Authorization:'Token '+token}});if(!r.ok)throw Error('Export failed');let url=URL.createObjectURL(await r.blob());let a=document.createElement('a');a.href=url;a.download='complaints.csv';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);})}>Download CSV report</button>}</section></>}

 {page==='new'&&<>
  <h1>Submit a complaint</h1>
  <section>
    <form onSubmit={e=>{
      e.preventDefault();
      const formData=new FormData(e.currentTarget);
      const file=formData.get('file');
      const data={title:formData.get('title'),description:formData.get('description')};
      if(file&&file.size>5*1024*1024){setError('File must be 5 MB or smaller.');return;}
      run(async()=>{
        const c=await api('complaints/','POST',data);
        let uploadError='';
        if(file&&file.size>0){
          try{
            const uploadData=new FormData();
            uploadData.append('file',file);
            const r=await fetch(API+'complaints/'+c.id+'/upload/',{
              method:'POST',
              headers:{Authorization:'Token '+token},
              body:uploadData
            });
            if(!r.ok){
              const result=await r.json().catch(()=>({}));
              throw Error(result.detail||JSON.stringify(result)||'Upload failed');
            }
          }catch(err){uploadError=err.message;}
        }
        await open(c.id);
        if(uploadError){
          setError('Complaint #'+c.id+' was created, but the file upload failed: '+uploadError+'. You can try uploading again from Supporting files.');
        }else{
          setSuccess(file&&file.size>0?'Complaint and supporting file submitted successfully.':'Complaint submitted successfully.');
        }
      });
    }}>
      <label>Title<input name="title" required maxLength="150" placeholder="A short summary of your issue"/></label>
      <label>Details in English<textarea name="description" required minLength="10" maxLength="10000" placeholder="Explain what happened and what help you need"/></label>
      <label>Supporting file (optional)<input type="file" name="file" accept=".pdf,.png,.jpg,.jpeg"/></label>
      <p className="muted">PDF, PNG or JPEG; maximum 5 MB per file. You can add more evidence from the complaint detail page (up to 3 files).</p>
      <p className="muted">The model suggests a category and routes the complaint. Staff can review the result.</p>
      <button disabled={loading}>Submit complaint</button>
    </form>
  </section>
</>}

 {page==='detail'&&item&&<><h1>#{item.id} {item.title}</h1>{(item.can_edit||item.can_delete)&&<section><div className="tags">{item.can_edit&&<button disabled={loading} onClick={()=>setEditing(!editing)}>{editing?'Cancel edit':'Edit complaint'}</button>}{item.can_delete&&<button className="danger" disabled={loading} onClick={()=>{if(window.confirm('Delete complaint #'+item.id+'? It will be removed from your dashboard; its record will be archived.'))run(async()=>{await api('complaints/'+item.id+'/','DELETE');setItem(null);setEditing(false);await load();setPage('dashboard');setSuccess('Complaint deleted from your dashboard.');});}}>Delete complaint</button>}</div><p className="muted">Editing and deletion are available only while Submitted and unassigned.</p></section>}{editing&&<section><h2>Edit complaint</h2><form onSubmit={e=>{e.preventDefault();let data=fields(e);run(async()=>{setItem(await api('complaints/'+item.id+'/','PATCH',data));setEditing(false);setSuccess('Complaint updated. Category and department were re-analyzed.');});}}><label>Title<input name="title" required maxLength="150" defaultValue={item.title}/></label><label>Details in English<textarea name="description" required minLength="10" maxLength="10000" defaultValue={item.description}/></label><button disabled={loading}>Save changes</button></form></section>}<section><div className="tags"><span className="badge">{item.status}</span><span className={'badge '+item.priority}>{item.priority} priority</span><span>{item.department}</span></div><p className="pre">{item.description}</p><p className="muted">{item.category} · {item.sentiment} · Model score: {Math.round(item.confidence * 100)}% (not measured accuracy)</p><p>Assigned staff: {item.assigned_name||'Unassigned'}</p><small>Created: {new Date(item.created).toLocaleString()}</small></section>{['admin','staff'].includes(user.role)&&<section><h2>Staff review</h2><form key={item.id+item.updated} onSubmit={e=>{e.preventDefault();let data=fields(e);if(user.role==='admin')data.assigned_to=data.assigned_to?Number(data.assigned_to):null;run(async()=>{setItem(await api('complaints/'+item.id+'/review/','POST',data));});}}><label>Status{select('status',meta.statuses,item.status)}</label><label>Category{select('category',meta.categories,item.category)}</label><label>Priority{select('priority',meta.priorities,item.priority)}</label>{user.role==='admin'&&<label>Assign staff (must match category department)<select name="assigned_to" defaultValue={item.assigned_to||''}><option value="">Unassigned</option>{people.filter(p=>p.role==='staff'&&p.active).map(p=><option key={p.id} value={p.id}>{p.username} · {p.department}</option>)}</select></label>}<button disabled={loading}>Save review</button></form></section>}<section><h2>Conversation</h2>{item.messages.map(m=><article key={m.id}><strong>{m.name}</strong><small> · {new Date(m.created).toLocaleString()}</small><p className="pre">{m.body}</p></article>)}<form onSubmit={e=>{e.preventDefault();run(async()=>{await api('complaints/'+item.id+'/reply/','POST',{body:reply});setReply('');await open(item.id);});}}><textarea value={reply} onChange={e=>setReply(e.target.value)} required maxLength="5000" placeholder="Write a response"/><button disabled={loading}>Send response</button></form></section><section><h2>Activity history</h2>{item.history.map((h,i)=><p key={i}>{h.body}<br/><small>{new Date(h.created).toLocaleString()}</small></p>)}</section></>}

 {page==='detail'&&item&&<section><h2>Supporting files</h2>{item.attachments?.map(a=><p key={a.id}><button className="link" onClick={()=>run(async()=>{let r=await fetch(API+'complaints/'+item.id+'/attachments/'+a.id+'/',{headers:{Authorization:'Token '+token}});if(!r.ok)throw Error('Download failed');let url=URL.createObjectURL(await r.blob());let link=document.createElement('a');link.href=url;link.download=a.name;link.click();setTimeout(()=>URL.revokeObjectURL(url),1000);})}>{a.name} ↓ Download</button></p>)}{item.can_edit&&<form onSubmit={e=>{e.preventDefault();let data=new FormData(e.currentTarget);run(async()=>{let r=await fetch(API+'complaints/'+item.id+'/upload/',{method:'POST',headers:{Authorization:'Token '+token},body:data});let d=await r.json();if(!r.ok)throw Error(d.detail||JSON.stringify(d));await open(item.id);setSuccess('Supporting file uploaded.');});}}><label>Add evidence<input type="file" name="file" accept=".pdf,.png,.jpg,.jpeg" required/></label><p className="muted">Up to 3 files, 5 MB each. PDF, PNG or JPEG. Files are downloaded only by authorized users.</p><button disabled={loading}>Upload file</button></form>}</section>}

 {page==='settings'&&<><h1>Departments & categories</h1><section><p>Names identify records. Enter an existing name to change its active state or routing; enter a new name to create it. Disabling preserves historical complaints.</p><h2>Department</h2><form onSubmit={e=>{e.preventDefault();let d=fields(e);run(async()=>{setConfig(await api('configuration/','POST',{kind:'department',name:d.name,active:d.active==='true'}));setMeta(await api('metadata/'));setSuccess('Department saved.');});}}><input name="name" required maxLength="50" placeholder="Department name"/><select name="active"><option value="true">Active</option><option value="false">Inactive</option></select><button disabled={loading}>Save department</button></form>{config.departments.map(d=><p key={d.id}>{d.name} · {d.active?'Active':'Inactive'}</p>)}</section><section><h2>Category routing</h2><p className="muted">New categories are available for manual staff review. Automatic classification needs labeled training examples and a backend restart.</p><form onSubmit={e=>{e.preventDefault();let d=fields(e);run(async()=>{setConfig(await api('configuration/','POST',{kind:'category',name:d.name,active:d.active==='true',department:Number(d.department)}));setMeta(await api('metadata/'));setSuccess('Category saved.');});}}><input name="name" required maxLength="50" placeholder="Category name"/><select name="department" required>{config.departments.map(d=><option key={d.id} value={d.id}>{d.name}</option>)}</select><select name="active"><option value="true">Active</option><option value="false">Inactive</option></select><button disabled={loading}>Save category</button></form>{config.categories.map(c=><p key={c.id}>{c.name} → {config.departments.find(d=>d.id===c.department_id)?.name} · {c.active?'Active':'Inactive'}</p>)}</section></>}

 {page==='evaluation'&&metrics&&<><h1>Model evaluation</h1><section><p className="muted">{metrics.limitations}</p><div className="table"><table><thead><tr><th>Model</th><th>Test examples</th><th>Sample accuracy</th></tr></thead><tbody>{['category','priority','sentiment'].map(k=><tr key={k}><td>{k}</td><td>{metrics[k].sample_count}</td><td>{(metrics[k].accuracy *100).toFixed(1)}%</td></tr>)}</tbody></table></div><p>Category mean inference: {metrics.category.mean_inference_ms.toFixed(2)} ms</p><p>Combined inference + FAQ: {metrics.combined_model_and_faq_mean_ms.toFixed(2)} ms</p><h2>Category scores</h2><div className="table"><table><thead><tr><th>Category</th><th>Precision</th><th>Recall</th><th>F1</th></tr></thead><tbody>{metrics.category.labels.map(k=><tr key={k}><td>{k}</td><td>{metrics.category.report[k].precision.toFixed(2)}</td><td>{metrics.category.report[k].recall.toFixed(2)}</td><td>{metrics.category.report[k]['f1-score'].toFixed(2)}</td></tr>)}</tbody></table></div></section></>}

 {page==='chat'&&<><h1>FAQ assistant</h1><section><p className="muted">NLP retrieval assistant for tracking, billing, accounts, internet and submitting complaints.</p>{chat.map((c,i)=><article key={i}><strong>{c.role}</strong><p>{c.text}</p></article>)}<form onSubmit={e=>{e.preventDefault();let data=fields(e);e.currentTarget.reset();run(async()=>{let d=await api('chat/','POST',data);setChat(c=>[...c,{role:'You',text:data.question},{role:'Assistant',text:d.answer}]);});}}><input name="question" required maxLength="1000" placeholder="How do I track my complaint?"/><button disabled={loading}>Ask</button></form></section></>}

 {page==='notifications'&&<><h1>Notifications</h1><section>{notes.length?notes.map(n=><article key={n.id}><button className="link" onClick={()=>run(()=>open(n.complaint))}>{n.body}</button><p className="muted">{new Date(n.created).toLocaleString()}</p></article>):<p>No notifications yet.</p>}</section></>}

 {page==='users'&&<><h1>User management</h1>{people.map(p=><section key={p.id}><h2>{p.username}</h2><form onSubmit={e=>{e.preventDefault();let d=fields(e);run(async()=>{setPeople(await api('users/','POST',{...d,id:p.id,active:d.active==='true'}));});}}><label>Role{select('role',['user','staff','admin'],p.role)}</label><label>Department{select('department',['',...meta.departments],p.department)}</label><label>Account<select name="active" defaultValue={String(p.active)}><option value="true">Active</option><option value="false">Disabled</option></select></label><button disabled={loading||p.id===user.id}>Save user</button></form></section>)}</>}

 <footer>Complaint Support · ML-assisted routing · Human-reviewed resolution</footer></main></>;

}

createRoot(document.getElementById('root')).render(<App/>);