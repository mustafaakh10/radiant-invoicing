/* Radiant Billing — device layer: local database, images, sharing, AI provider, backup.
   Works inside the Android app (Capacitor) and in a normal browser for testing. */
"use strict";
const NATIVE=!!(window.Capacitor&&window.Capacitor.isNativePlatform&&window.Capacitor.isNativePlatform());
const Plug=n=>(window.Capacitor&&window.Capacitor.Plugins&&window.Capacitor.Plugins[n])||null;

/* ---------- local database (IndexedDB) with the small API the app uses ---------- */
const LocalStore=(()=>{
  let dbp=null;const mem=new Map(),subs=new Set();
  const open=()=>dbp||(dbp=new Promise((res,rej)=>{const r=indexedDB.open("radiant-billing",1);
    r.onupgradeneeded=()=>r.result.createObjectStore("kv");r.onsuccess=()=>res(r.result);r.onerror=()=>rej(r.error)}));
  async function load(){const db=await open();await new Promise((res,rej)=>{const rq=db.transaction("kv").objectStore("kv").openCursor();
    rq.onsuccess=()=>{const c=rq.result;if(c){mem.set(c.key,c.value);c.continue()}else res()};rq.onerror=()=>rej(rq.error)})}
  async function writeMany(entries){/* [[path,value|undefined]] in one transaction */
    const db=await open();
    await new Promise((res,rej)=>{const tx=db.transaction("kv","readwrite"),st=tx.objectStore("kv");
      for(const[p,v]of entries)v===undefined?st.delete(p):st.put(v,p);tx.oncomplete=res;tx.onerror=()=>rej(tx.error);tx.onabort=()=>rej(tx.error)});
    for(const[p,v]of entries)v===undefined?mem.delete(p):mem.set(p,v);
    const touched=new Set(entries.map(([p])=>p));for(const s of subs)for(const p of touched)if(s.match(p)){s.fire();break}
  }
  const write=(p,v)=>writeMany([[p,v]]);
  const parent=p=>p.slice(0,p.lastIndexOf("/"));
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
  return{load,doc,collection,write,writeMany,entries:()=>[...mem.entries()],has:p=>mem.has(p),get:p=>mem.get(p),
    async clearAll(){await writeMany([...mem.keys()].map(k=>[k,undefined]))}};
})();

/* ---------- images: stored as Blobs in the database, referenced as "rl:<id>" ---------- */
const BLOBURL=new Map();
function imgSrc(v){if(!v)return"";if(typeof v==="string"&&v.startsWith("rl:"))return BLOBURL.get(v.slice(3))||"";return v}
function registerBlobs(){for(const[k,v]of LocalStore.entries())if(k.startsWith("blobs/")&&v instanceof Blob&&!BLOBURL.has(k.slice(6)))BLOBURL.set(k.slice(6),URL.createObjectURL(v))}
async function storeImageLocal(blob){const id="i"+Date.now().toString(36)+Math.random().toString(36).slice(2,6);
  await LocalStore.write("blobs/"+id,blob);BLOBURL.set(id,URL.createObjectURL(blob));return"rl:"+id}

/* ---------- files out: Android share sheet (WhatsApp, Drive, Files…) or a browser download ---------- */
const blobToB64=b=>new Promise((res,rej)=>{const f=new FileReader();f.onload=()=>res(String(f.result).split(",")[1]);f.onerror=rej;f.readAsDataURL(b)});
async function shareFile(filename,blob,title){
  const FS=Plug("Filesystem"),SH=Plug("Share");
  if(NATIVE&&FS&&SH){
    const safe=filename.replace(/[\\/:*?"<>|]/g,"").trim()||"file";
    const w=await FS.writeFile({path:"share/"+safe,data:await blobToB64(blob),directory:"CACHE",recursive:true});
    try{await SH.share({title:title||safe,files:[w.uri],dialogTitle:"Share "+safe})}
    catch(e){if(/cancel/i.test(String(e?.message||e)))return"cancelled";throw e}
    return"shared";
  }
  const a=document.createElement("a");a.href=URL.createObjectURL(blob);a.download=filename;document.body.appendChild(a);a.click();
  setTimeout(()=>{URL.revokeObjectURL(a.href);a.remove()},4000);return"downloaded";
}

/* ---------- AI provider (optional; user's own key, stored only on this phone) ---------- */
const AI_PRESETS={
  none:{label:"Off — built-in matching only",base:"",model:""},
  groq:{label:"Groq (free tier)",base:"https://api.groq.com/openai/v1",model:"llama-3.3-70b-versatile",keys:"console.groq.com/keys"},
  gemini:{label:"Google Gemini (free tier)",base:"https://generativelanguage.googleapis.com/v1beta/openai",model:"gemini-2.5-flash",keys:"aistudio.google.com/apikey"},
  openrouter:{label:"OpenRouter (has free models)",base:"https://openrouter.ai/api/v1",model:"meta-llama/llama-3.3-70b-instruct:free",keys:"openrouter.ai/keys"},
  deepseek:{label:"DeepSeek",base:"https://api.deepseek.com/v1",model:"deepseek-chat",keys:"platform.deepseek.com"},
  openai:{label:"OpenAI",base:"https://api.openai.com/v1",model:"gpt-4.1-mini",keys:"platform.openai.com/api-keys"},
  anthropic:{label:"Anthropic (Claude)",base:"https://api.anthropic.com/v1",model:"claude-haiku-5-5",keys:"console.anthropic.com"},
  custom:{label:"Other (OpenAI-compatible)",base:"",model:""}
};
const aiConf=()=>{const s=(typeof S!=="undefined"&&S.settings)||{};const p=s.aiProvider||"none";
  return{provider:p,base:(s.aiBase||AI_PRESETS[p]?.base||"").replace(/\/+$/,""),model:s.aiModel||AI_PRESETS[p]?.model||"",key:s.aiKey||""}};
const aiReady=()=>{const c=aiConf();return c.provider!=="none"&&!!c.key&&!!c.base&&!!c.model};
async function httpPost(url,headers,body){
  const H=Plug("CapacitorHttp");
  if(NATIVE&&H){const r=await H.request({url,method:"POST",headers:{"Content-Type":"application/json",...headers},data:body,connectTimeout:20000,readTimeout:60000});
    return{status:r.status,data:typeof r.data==="string"?(()=>{try{return JSON.parse(r.data)}catch{return{raw:r.data}}})():r.data}}
  const r=await fetch(url,{method:"POST",headers:{"Content-Type":"application/json",...headers},body:JSON.stringify(body)});
  let data;try{data=await r.json()}catch{data={}}return{status:r.status,data};
}
class AIError extends Error{constructor(code,msg){super(msg);this.code=code}}
async function aiText(prompt){
  const c=aiConf();if(!aiReady())throw new AIError("not_configured","No AI key set");
  let r,text="";
  if(c.provider==="anthropic"){
    r=await httpPost(c.base+"/messages",{"x-api-key":c.key,"anthropic-version":"2023-06-01","anthropic-dangerous-direct-browser-access":"true"},{model:c.model,max_tokens:1500,temperature:0,messages:[{role:"user",content:prompt}]});
    if(r.status===200)text=(r.data.content||[]).map(b=>b.text||"").join("");
  }else{
    r=await httpPost(c.base+"/chat/completions",{"Authorization":"Bearer "+c.key},{model:c.model,temperature:0,messages:[{role:"user",content:prompt}]});
    if(r.status===200)text=r.data?.choices?.[0]?.message?.content||"";
  }
  if(r.status===401||r.status===403)throw new AIError("bad_key","The AI key was rejected. Check it in Settings.");
  if(r.status===429)throw new AIError("rate_limited","AI limit reached. Wait a minute and try again.");
  if(r.status===404||r.status===400){const m=JSON.stringify(r.data||{}).slice(0,160);throw new AIError("bad_model",/model/i.test(m)?"The AI model name wasn't accepted. Check it in Settings.":"The AI request was refused: "+m)}
  if(r.status!==200)throw new AIError("failed","AI request failed ("+r.status+").");
  return text;
}
async function aiJson(prompt){
  const t=await aiText(prompt);const m=t.match(/\{[\s\S]*\}/);
  if(!m)throw new AIError("invalid_json","The AI reply had no data.");
  try{return JSON.parse(m[0])}catch{throw new AIError("invalid_json","The AI reply couldn't be read.")}
}

/* ---------- backup / restore (everything incl. photos, one JSON file) ---------- */
async function exportBackup(){
  const records={},blobs={};
  for(const[k,v]of LocalStore.entries()){if(k.startsWith("blobs/")){if(v instanceof Blob)blobs[k.slice(6)]={type:v.type,b64:await blobToB64(v)}}else records[k]=v}
  const out={app:"radiant-billing",version:1,exportedAt:new Date().toISOString(),records,blobs};
  const stamp=new Date().toISOString().slice(0,16).replace(/[T:]/g,"-");
  return shareFile(`Radiant-Billing-backup-${stamp}.json`,new Blob([JSON.stringify(out)],{type:"application/json"}),"Radiant Billing backup");
}
function b64ToBlob(b64,type){const s=atob(b64),u=new Uint8Array(s.length);for(let i=0;i<s.length;i++)u[i]=s.charCodeAt(i);return new Blob([u],{type})}
async function readBackup(file){const j=JSON.parse(await file.text());if(j.app!=="radiant-billing"||!j.records)throw new Error("Not a Radiant Billing backup file.");return j}
async function restoreBackup(j){
  await LocalStore.clearAll();
  const entries=Object.entries(j.records).map(([k,v])=>[k,v]);
  for(const[id,b]of Object.entries(j.blobs||{}))entries.push(["blobs/"+id,b64ToBlob(b.b64,b.type)]);
  for(let i=0;i<entries.length;i+=200)await LocalStore.writeMany(entries.slice(i,i+200));
}

/* ---------- first run: load the data brought over from the web app ---------- */
async function seedIfEmpty(){
  if(LocalStore.has("meta/seeded"))return;
  try{const r=await fetch("seed.json");if(r.ok){const j=await r.json();await LocalStore.writeMany(Object.entries(j.records))}}catch{}
  await LocalStore.write("meta/seeded",{at:Date.now()});
}

/* ---------- Android chrome: status bar + back button ---------- */
async function setupNative(onBack){
  if(!NATIVE)return;
  try{const SB=Plug("StatusBar");if(SB){await SB.setStyle({style:"DARK"});await SB.setBackgroundColor({color:"#2b3a2f"})}}catch{}
  try{const A=Plug("App");if(A)A.addListener("backButton",()=>{if(!onBack())A.exitApp()})}catch{}
}
