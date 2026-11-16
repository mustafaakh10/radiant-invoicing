/* Radiant Billing — web layer: same interface as platform.js (the Android one),
   but data, photos and AI live on your Django server. */
"use strict";
const NATIVE=false;
const csrf=()=>(document.cookie.match(/(?:^|;\s*)csrftoken=([^;]+)/)||[])[1]||"";
async function api(path,opts={}){
  const isForm=opts.body instanceof FormData;
  const r=await fetch(path,{credentials:"same-origin",...opts,headers:{...(opts.body&&!isForm?{"Content-Type":"application/json"}:{}),"X-CSRFToken":csrf(),...(opts.headers||{})}});
  if(r.status===401||r.status===403&&/csrf/i.test(await r.clone().text())){location.href="/login/?next=/";throw new Error("Please sign in again.")}
  let data={};try{data=await r.json()}catch{}
  if(!r.ok){const e=new Error(data.error||("Server error ("+r.status+")"));e.code=data.code;e.status=r.status;throw e}
  return data;
}

/* ---------- database: the whole data set is small, so keep it in memory and sync with the server ---------- */
const LocalStore=(()=>{
  const mem=new Map(),subs=new Set();let rev=0,timer=null;
  const parent=p=>p.slice(0,p.lastIndexOf("/"));
  const fire=paths=>{for(const s of subs)for(const p of paths)if(s.match(p)){s.fire();break}};
  async function pull(){
    const j=await api("/api/records");const changed=new Set();
    for(const k of mem.keys())if(!(k in j.records)){mem.delete(k);changed.add(k)}
    for(const[k,v]of Object.entries(j.records))if(JSON.stringify(mem.get(k))!==JSON.stringify(v)){mem.set(k,v);changed.add(k)}
    rev=j.rev;return changed;
  }
  async function load(){await pull();
    /* another phone or tab saved something: refresh quietly */
    const check=async()=>{if(document.visibilityState!=="visible")return;try{const j=await api("/api/rev");if(j.rev!==rev)fire(await pull())}catch{}};
    timer=setInterval(check,20000);document.addEventListener("visibilitychange",check);
  }
  async function writeMany(entries){
    const before=entries.map(([p])=>[p,mem.has(p)?mem.get(p):undefined]);
    for(const[p,v]of entries)v===undefined?mem.delete(p):mem.set(p,structuredClone(v));
    const paths=entries.map(([p])=>p);fire(paths);
    try{const j=await api("/api/write",{method:"POST",body:JSON.stringify({writes:entries.map(([p,v])=>[p,v===undefined?null:v])})});
      if(j.rev!==rev+1){rev=j.rev;fire(await pull())}else rev=j.rev}
    catch(e){for(const[p,v]of before)v===undefined?mem.delete(p):mem.set(p,v);fire(paths);throw e}
  }
  const write=(p,v)=>writeMany([[p,v]]);
  const snapDoc=p=>({id:p.slice(p.lastIndexOf("/")+1),exists:mem.has(p),data:()=>mem.has(p)?structuredClone(mem.get(p)):undefined,metadata:{fromCache:false,hasPendingWrites:false}});
  function doc(p){return{id:p.slice(p.lastIndexOf("/")+1),path:p,
    get:async()=>snapDoc(p),set:async d=>write(p,structuredClone(d)),update:async d=>write(p,{...(mem.get(p)||{}),...structuredClone(d)}),delete:async()=>write(p,undefined),
    onSnapshot(fn){const s={match:x=>x===p,fire:()=>fn(snapDoc(p))};subs.add(s);setTimeout(s.fire,0);return()=>subs.delete(s)}}}
  function collection(col){
    const mk=(ord,lim)=>{const snap=()=>{let d=[];for(const k of mem.keys())if(parent(k)===col)d.push(snapDoc(k));
        if(ord){const[f,dir]=ord;d.sort((a,b)=>{const x=a.data()[f],y=b.data()[f];return(x>y?1:x<y?-1:0)*(dir==="desc"?-1:1)})}
        if(lim)d=d.slice(0,lim);return{docs:d,size:d.length,empty:!d.length,docChanges:()=>[],metadata:{fromCache:false,hasPendingWrites:false}}};
      return{path:col,orderBy:(f,dir)=>mk([f,dir],lim),limit:n=>mk(ord,n),get:async()=>snap(),
        onSnapshot(fn){const s={match:x=>parent(x)===col,fire:()=>fn(snap())};subs.add(s);setTimeout(s.fire,0);return()=>subs.delete(s)},
        doc:id=>doc(col+"/"+(id||("x"+Date.now().toString(36)+Math.random().toString(36).slice(2,6)))),
        add:async data=>{const r=doc(col+"/x"+Date.now().toString(36)+Math.random().toString(36).slice(2,6));await r.set(data);return r}}};
    return mk(null,null);
  }
  return{load,doc,collection,write,writeMany,entries:()=>[...mem.entries()],has:p=>mem.has(p),get:p=>mem.get(p),refresh:async()=>fire(await pull())};
})();

/* ---------- photos: uploaded to the server, referenced by URL ---------- */
function imgSrc(v){return v||""}
function registerBlobs(){}
async function storeImageLocal(blob){
  const f=new FormData();f.append("file",blob,"image."+((blob.type||"image/jpeg").split("/")[1]||"jpg"));
  return(await api("/api/upload",{method:"POST",body:f})).url;
}

/* ---------- files out: phone browsers get the share sheet (WhatsApp…), computers download ---------- */
async function shareFile(filename,blob,title){
  const safe=filename.replace(/[\\/:*?"<>|]/g,"").trim()||"file";
  const mobile=/Android|iPhone|iPad|iPod/i.test(navigator.userAgent);
  if(mobile&&navigator.canShare){const file=new File([blob],safe,{type:blob.type});
    if(navigator.canShare({files:[file]})){try{await navigator.share({files:[file],title:title||safe});return"shared"}catch(e){if(e&&e.name==="AbortError")return"cancelled"}}}
  const a=document.createElement("a");a.href=URL.createObjectURL(blob);a.download=safe;document.body.appendChild(a);a.click();
  setTimeout(()=>{URL.revokeObjectURL(a.href);a.remove()},4000);return"downloaded";
}

/* ---------- AI: settings and calls go through the server; the key is never sent to the browser ---------- */
let AIS={provider:"none",base:"",model:"",hasKey:false,keyHint:"",limit:0,ready:false,usage:{calls:0,cached:0,failed:0,input:0,output:0},presets:{none:{label:"Off: built-in matching only"}}};
let AI_PRESETS=AIS.presets;
async function aiLoad(){try{AIS=await api("/api/ai/config");AI_PRESETS=AIS.presets}catch{}}
async function aiSave(o){AIS=await api("/api/ai/config",{method:"POST",body:JSON.stringify(o)});AI_PRESETS=AIS.presets;return AIS}
const aiReady=()=>!!AIS.ready;
class AIError extends Error{constructor(code,msg){super(msg);this.code=code}}
async function aiText(prompt,opts={}){
  if(!aiReady())throw new AIError("not_configured","No AI key set");
  try{const r=await api("/api/ai/complete",{method:"POST",body:JSON.stringify({prompt,maxTokens:opts.maxTokens||600,cache:opts.cache!==false})});
    if(!r.cached){AIS.usage.calls++;AIS.usage.input+=r.input||0;AIS.usage.output+=r.output||0}else AIS.usage.cached++;
    return r.text||""}
  catch(e){throw new AIError(e.code||"failed",e.message)}
}
async function aiJson(prompt,opts){
  const t=await aiText(prompt,opts);const m=t.match(/\{[\s\S]*\}/);
  if(!m)throw new AIError("invalid_json","The AI reply had no data.");
  try{return JSON.parse(m[0])}catch{throw new AIError("invalid_json","The AI reply couldn't be read.")}
}
const fmtTok=n=>n>=1e6?(n/1e6).toFixed(1)+"M":n>=1e3?(n/1e3).toFixed(1)+"k":String(n||0);

/* ---------- backup / restore ---------- */
async function exportBackup(){
  const r=await fetch("/api/backup",{credentials:"same-origin"});if(!r.ok)throw new Error("Backup failed");
  const stamp=new Date().toISOString().slice(0,16).replace(/[T:]/g,"-");
  return shareFile(`Radiant-Billing-backup-${stamp}.json`,await r.blob(),"Radiant Billing backup");
}
async function readBackup(file){const j=JSON.parse(await file.text());if(j.app!=="radiant-billing"||!j.records)throw new Error("Not a Radiant Billing backup file.");return j}
async function restoreBackup(j){await api("/api/restore",{method:"POST",body:JSON.stringify(j)})}

async function seedIfEmpty(){}
async function setupNative(){}

/* ---------- extra Settings sections for the web app ---------- */
const restoreBoxHTML=(j,where)=>{const n=k=>Object.keys(j.records).filter(x=>x.startsWith(k+"/")).length;
  return`<div class="banner" style="margin:0">Backup from ${esc(fdate(String(j.exportedAt).slice(0,10)))}: ${n("docs")} documents, ${n("products")} products, ${n("customers")} customers.<div class="row" style="margin-top:8px"><button class="btn danger armed" data-act="restoreok">Replace all data ${where}</button><button class="btn ghost" data-act="restorecancel">Cancel</button></div></div>`};
const aiUsageHTML=()=>{const u=AIS.usage||{};return`<div class="aiuse"><div><b>${u.calls||0}</b><span>AI calls</span></div><div><b>${fmtTok((u.input||0)+(u.output||0))}</b><span>tokens used</span></div><div><b>${u.cached||0}</b><span>answered free from memory</span></div>${AIS.limit?`<div><b>${fmtTok(AIS.limit)}</b><span>monthly limit</span></div>`:""}</div>`};
const SETTINGS_EXTRA=[
  {id:"ai",label:"AI assistant",sub:"Optional help for lines the built-in matching can't place.",html:()=>{const cur=AIS.provider||"none",p=AI_PRESETS[cur]||{};
    return sCard(`AI provider <span class="pill ${aiReady()?"INV":"QT"}" style="margin-left:6px" id="aiPill">${aiReady()?"On":"Off"}</span>`,`
      <label class="f">Provider<select id="aiProvider">${Object.entries(AI_PRESETS).map(([k,x])=>`<option value="${k}" ${cur===k?"selected":""}>${esc(x.label)}</option>`).join("")}</select></label>
      <div id="aiFields" class="stack" style="gap:12px" ${cur==="none"?"hidden":""}>
        <label class="f">API key <span class="muted fh" id="aiKeyHint">${p.keys?"get one at "+esc(p.keys):""}</span><input id="aiKey" type="password" autocomplete="off" value="" placeholder="${AIS.hasKey?"Saved ("+esc(AIS.keyHint)+"). Leave blank to keep it":"Paste your key"}"></label>
        <div class="g2"><label class="f">Model<input id="aiModel" value="${esc(AIS.model)}" placeholder="${esc(p.model||"model name")}"></label>
        <label class="f">Monthly token limit <span class="muted fh">0 = none</span><input id="aiLimit" inputmode="numeric" value="${esc(AIS.limit||0)}"></label></div>
        <details class="adv"><summary>Advanced</summary><label class="f" style="margin-top:10px">API address<input id="aiBase" value="${esc(AIS.base)}" placeholder="${esc(p.base||"https://…/v1")}"></label></details>
        <div class="row"><button class="btn pri" data-act="aitest">Save &amp; test</button>${AIS.hasKey?`<button class="btn ghost danger" data-act="aiclear">Remove key</button>`:""}<span id="aiTestMsg" class="muted" style="font-size:13px"></span></div></div>`,
      "Your key is stored on your server and never sent to the browser.")
    +sCard("This month",aiUsageHTML(),"Built-in matching places most lines for free. Only lines it can't place go to the AI, with just the few matching products and a short reply, so each call stays small. Repeating the same entry is answered from memory at no cost.")}},
  {id:"backup",label:"Backup & restore",sub:"Your records are saved on your server.",html:()=>sCard("Backup",`<div class="row"><button class="btn" data-act="backup">Download backup</button><label class="btn">Restore from file<input type="file" accept="application/json,.json" id="restoreFile" hidden></label></div><div id="restoreBox"></div>`,
      "Download a backup now and then and keep it on Drive. It includes photos. You can also restore a backup from the Android app here.")},
  {id:"account",label:"Account",sub:"Your sign-in.",html:()=>sCard("Signed in",`<div class="row"><button class="btn" data-act="logout">Sign out</button><a class="btn ghost" href="/admin/password_change/">Change password</a><a class="btn ghost" href="/admin/">Admin panel</a></div>`,
      "You stay signed in on this device for 60 days.")}
];
const PLATFORM_ACTS={
  async aitest(){const m=$("#aiTestMsg");const v=id=>($("#"+id)?.value||"").trim();
    const o={provider:v("aiProvider"),model:v("aiModel"),base:v("aiBase"),limit:v("aiLimit")||0};if(v("aiKey"))o.key=v("aiKey");
    m.textContent="Saving…";try{await aiSave(o)}catch(e){m.textContent=e.message;return}
    if(!aiReady()){vSettings();toast(o.provider==="none"?"AI turned off":"Saved. Add a key to turn AI on.");return}
    m.textContent="Testing…";let msg;try{const t=await aiText("Reply with just the word OK.",{maxTokens:5,cache:false});msg=/ok/i.test(t)?"Working ✓":"Connected, unexpected reply: "+t.slice(0,40)}catch(e){msg=e.message||"Test failed."}
    await aiLoad();vSettings();const m2=$("#aiTestMsg");if(m2)m2.textContent=msg},
  async aiclear(){await aiSave({clearKey:true});vSettings();toast("Key removed")},
  async backup(){try{const r=await exportBackup();if(r==="downloaded")toast("Backup downloaded")}catch{toast("Couldn't create the backup.")}},
  async restoreok(){try{toast("Restoring…");await restoreBackup(S.pendingRestore);toast("Restored. Reloading…");setTimeout(()=>location.reload(),600)}catch(e){toast(e.message||"Restore failed. Nothing was changed.")}},
  async restorecancel(){S.pendingRestore=null;$("#restoreBox").innerHTML=""},
  async logout(){const f=document.createElement("form");f.method="post";f.action="/logout/";const i=document.createElement("input");i.type="hidden";i.name="csrfmiddlewaretoken";i.value=csrf();f.appendChild(i);document.body.appendChild(f);f.submit()}
};
async function PLATFORM_CHANGE(t){
  if(t.id==="aiProvider"){const p=AI_PRESETS[t.value]||{};$("#aiFields").hidden=t.value==="none";$("#aiModel").placeholder=p.model||"model name";$("#aiBase").placeholder=p.base||"https://…/v1";$("#aiKeyHint").textContent=p.keys?"get one at "+p.keys:"";
    if(t.value==="none"){await aiSave({provider:"none"});vSettings();toast("AI turned off")}return true}
  if(t.id==="restoreFile"&&t.files[0]){const box=$("#restoreBox");try{const j=await readBackup(t.files[0]);S.pendingRestore=j;box.innerHTML=restoreBoxHTML(j,"on the server")}
    catch(e){box.innerHTML=`<div class="banner" style="margin:0">${esc(e.message||"Couldn't read that file.")}</div>`}t.value="";return true}
  return false;
}
/* small styles only the web build needs */
document.head.insertAdjacentHTML("beforeend",`<style>
.aiuse{display:grid;grid-template-columns:repeat(auto-fit,minmax(120px,1fr));gap:10px}
.aiuse div{background:var(--sunk);border-radius:10px;padding:12px}.aiuse b{display:block;font-size:20px}.aiuse span{font-size:12px;color:var(--muted)}
details.adv summary{cursor:pointer;font-size:13px;font-weight:600;color:var(--muted)}
</style>`);
