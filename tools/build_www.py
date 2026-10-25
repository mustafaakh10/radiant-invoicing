#!/usr/bin/env python3
"""Builds www/ (the app shipped inside the APK) from the web-app source + device layer."""
import json, os, re, shutil, glob

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "src", "app.src.html")
WWW = os.path.join(ROOT, "www")
NM = os.path.join(ROOT, "node_modules")

s = open(SRC, encoding="utf-8").read()

def R(a, b, cnt=1):
    global s
    n = s.count(a)
    assert n == cnt, f"expected {cnt}x, found {n}: {a[:90]!r}"
    s = s.replace(a, b)

def RX(pat, repl, cnt=1, flags=re.S):
    global s
    s, n = re.subn(pat, repl, s, flags=flags)
    assert n == cnt, f"regex expected {cnt}, got {n}: {pat[:90]!r}"

# --- head / fonts ---
R('<title>Radiant Lighting Invoicing</title>\n', '')
R('<meta name="claude:viewport-fit-sides" content="cover">\n', '')
R('<link rel="preconnect" href="https://fonts.googleapis.com">\n', '')
RX(r'<link rel="stylesheet" href="https://fonts\.googleapis\.com/css2[^"]*">\n', '')

# --- platform bits ---
R('const LOGO="__LOGO__";', 'const LOGO="img/logo.jpg";')
R('esc(it.img)', 'esc(imgSrc(it.img))', 2)
R('esc(p.img)', 'esc(imgSrc(p.img))', 2)
R('esc(s.logo||LOGO)', 'esc(imgSrc(s.logo)||LOGO)', 2)
R('await image(s.logo||LOGO,', 'await image(imgSrc(s.logo)||LOGO,')
R('  async function image(src,x,y,w,h){\n    if(!src)return false;', '  async function image(src,x,y,w,h){\n    src=imgSrc(src);if(!src)return false;')
RX(r'async function storeImage\(blob\)\{.*?\n\}\n', 'async function storeImage(blob){return storeImageLocal(blob)}\n')
R('const LIBS={pdf:"https://cdn.jsdelivr.net/npm/pdf-lib@1.17.1/dist/pdf-lib.min.js",fk:"https://cdn.jsdelivr.net/npm/@pdf-lib/fontkit@1.1.1/dist/fontkit.umd.min.js"};',
  'const LIBS={pdf:"vendor/pdf-lib.min.js",fk:"vendor/fontkit.umd.min.js"};')

# defaults: AI settings
R('  logo:""\n};', '  logo:"",aiProvider:"none",aiBase:"",aiModel:"",aiKey:""\n};')

# --- PDF: share sheet instead of claude.ai download ---
RX(r'async function makePDF\(d\)\{.*?\n\}\n', '''async function makePDF(d){
  toast("Building PDF…");
  let bytes;
  try{bytes=await buildPDF(d)}catch(e){toast("Couldn't create the PDF.");return}
  try{
    const name=`${d.number||"Draft-"+d.type} - ${(d.customer?.name||"Customer").replace(/[\\\\/:*?"<>|]/g,"")}.pdf`;
    const r=await shareFile(name,new Blob([bytes],{type:"application/pdf"}),`${TYPE_NAME[d.type]} ${d.number||""}`);
    if(r==="downloaded")toast("PDF downloaded");
  }catch(e){toast("Couldn't share the PDF.")}
}
''')
R('${S.ed.id?"Download PDF":"Save & download PDF"}', '${S.ed.id?"Share PDF":"Save & share PDF"}')
R('<button class="btn sm" data-act="pdf" data-id="${d.id}">PDF</button>', '<button class="btn sm" data-act="pdf" data-id="${d.id}">Share PDF</button>')
R('if(/\\b(download|export)\\b.*\\bpdf\\b|^pdf$/.test(lc)){S.ed.after="pdf";return"Will save & download PDF"}',
  'if(/\\b(download|export|share|send|whatsapp)\\b.*\\bpdf\\b|^(pdf|share|whatsapp|share pdf|send)$/.test(lc)){S.ed.after="pdf";return"Will save & share PDF"}')
R('“save” · “pdf” · “convert to invoice”', '“save” · “share” · “convert to invoice”')
R('<b>New items</b> (uses AI):', '<b>New items</b> (built-in matching; AI only if set up):')
R("Couldn't save. Check your connection and try again.", "Couldn't save on this phone. Try again.")

# --- quick entry wording ---
R('Edits are done instantly on your device; only new items use AI. Totals are always computed here.',
  'Everything runs on this phone. New items are matched to your catalogue; AI is only used for lines it can\'t place, and only if you add a key in Settings. Totals are always computed here.')

# --- AI: local-first, provider from Settings ---
RX(r'async function aiItems\(txt,d\)\{.*?\n\}\nasync function runAI\(\)\{.*?\n\}\n', r'''async function aiItems(clauses,d){
  const done=[],asks=[];
  const cat=S.products.map(p=>({id:p.id,name:p.name,specs:p.spec||"",model:p.model||"",keywords:p.keywords||"",price:num(p.price),unit:p.unit||"Pcs"}));
  const cus=S.customers.map(c=>({id:c.id,name:c.name,attn:c.attn||""}));
  const prompt=`You turn shorthand order notes from a lighting company in Multan, Pakistan into structured data. Do not do any arithmetic or totals.
CATALOGUE (JSON): ${JSON.stringify(cat)}
SAVED CUSTOMERS (JSON): ${JSON.stringify(cus)}
ORDER TEXT: """${clauses.join(", ")}"""
Rules:
- Match each product mention to a catalogue id by series name, keyword, wattage, model or description. Use null productId only if nothing in the catalogue fits; then give a clean description.
- A small number right before a product is the quantity. A larger number (usually 3+ digits) after a product is the unit rate in PKR. If no rate is written, rate is null. If no quantity is written, qty is null.
- If the text names a person and/or business, match a saved customer (fuzzy) and return its customerId; otherwise newCustomer with a Title Case company name and attn like "Mr. Mashood". If no customer is mentioned, both are null.
Reply with JSON only, exactly this shape:
{"customerId": string|null, "newCustomer": {"name": string, "attn": string}|null, "items": [{"productId": string|null, "description": string, "qty": number|null, "rate": number|null}]}`;
  try{
    const r=await aiJson(prompt);
    applyParsed({customer:r.customerId?{id:r.customerId}:r.newCustomer?.name?{name:r.newCustomer.name,attn:r.newCustomer.attn}:null,items:Array.isArray(r.items)?r.items:[]},d,done,asks);
    if(!done.length&&!asks.length)asks.push("No items found in that text.");
  }catch(e){
    asks.push((e?.message||"AI request failed.")+" Used built-in matching instead.");
    for(const cl of clauses)applyParsed(localParse(cl,d),d,done,asks);
  }
  return{done,asks};
}
async function runAI(){
  const box=$("#aiText"),txt=box.value.trim();S.ed.aiText=txt;if(!txt)return;
  const d=S.ed.doc,snap=clone(d);S.ed.after=null;
  const done=[],asks=[],rest=[];let help=false;
  for(const cl of splitClauses(txt)){let r;try{r=runCommand(cl,d)}catch{r=null}
    if(r===null)rest.push(cl);else if(r?.help)help=true;else if(r?.ask)asks.push(`“${cl}”: ${r.ask}`);else if(r)done.push(r)}
  const itemClauses=rest.filter(c=>looksLikeItems(c,d));
  rest.filter(c=>!itemClauses.includes(c)).forEach(c=>asks.push(`Didn't understand “${c}”. Tap “What can I type?” for examples.`));
  const forAI=[];
  for(const cl of itemClauses){const r=localParse(cl,d);
    if(!r.items.length){asks.push(`Didn't understand “${cl}”. Try “45 trail 4850”.`);continue}
    if(r.ok||!aiReady())applyParsed(r,d,done,asks);else forAI.push(cl)}
  if(forAI.length){const b=$("#aiBtn");if(b)b.disabled=true;const busy=$("#aiBusy");if(busy)busy.textContent="Asking AI about "+forAI.length+" line"+(forAI.length>1?"s":"")+"…";
    const r=await aiItems(forAI,d);done.push(...r.done);asks.push(...r.asks)}
  const changed=JSON.stringify(snap)!==JSON.stringify(d);
  if(changed){S.ed.undo=snap;S.ed.dirty=true}
  if(!asks.length&&!help)S.ed.aiText="";
  S.ed.cmdLog={done,asks,help};
  vEditor();
  const after=S.ed.after;S.ed.after=null;
  if(after==="save")await saveDoc();
  if(after==="pdf"){if(!S.ed.id||S.ed.dirty){if(!(await saveDoc()))return}makePDF(S.ed.doc)}
  if(after==="inv"||after==="dn"){if((!S.ed.id||S.ed.dirty)&&!(await saveDoc()))return;convert(S.ed.doc,after==="inv"?"INV":"DN")}
}
''')

# --- Settings: AI + backup cards ---
R('''    <div class="card stack"><h2>Numbering ${y}</h2>''', '''    <div class="card stack" id="aiCard"><div class="spread"><h2 style="margin:0">AI for new items</h2><span class="pill ${aiReady()?"INV":"QT"}">${aiReady()?"On":"Off"}</span></div>
      <div class="muted" style="font-size:13px">Optional. Built-in matching handles your catalogue on its own. With a key, lines it can't place are sent to the AI. The key stays on this phone.</div>
      <label class="f">Provider<select data-sf="aiProvider" id="aiProvider">${Object.entries(AI_PRESETS).map(([k,p])=>`<option value="${k}" ${(s.aiProvider||"none")===k?"selected":""}>${esc(p.label)}</option>`).join("")}</select></label>
      <div id="aiFields" ${(s.aiProvider||"none")==="none"?"hidden":""}>
        <div class="stack" style="gap:10px">
        <label class="f">API key<input data-sf="aiKey" id="aiKey" type="password" autocomplete="off" value="${esc(s.aiKey)}" placeholder="Paste your key"></label>
        <div class="muted" style="font-size:12px" id="aiKeyHint">${AI_PRESETS[s.aiProvider]?.keys?"Get a key at "+esc(AI_PRESETS[s.aiProvider].keys):""}</div>
        <label class="f">Model<input data-sf="aiModel" id="aiModel" value="${esc(s.aiModel)}" placeholder="${esc(AI_PRESETS[s.aiProvider]?.model||"model name")}"></label>
        <label class="f">API address<input data-sf="aiBase" id="aiBase" value="${esc(s.aiBase)}" placeholder="${esc(AI_PRESETS[s.aiProvider]?.base||"https://…/v1")}"></label>
        <div class="row"><button class="btn sm" data-act="aitest">Save &amp; test</button><span id="aiTestMsg" class="muted" style="font-size:13px"></span></div></div></div></div>
    <div class="card stack"><h2>Backup</h2>
      <div class="muted" style="font-size:13px">Your records live only on this phone. Share a backup file to Drive or WhatsApp regularly; restoring replaces everything on this phone.</div>
      <div class="row"><button class="btn" data-act="backup">Share backup file</button><label class="btn">Restore from file<input type="file" accept="application/json,.json" id="restoreFile" hidden></label></div>
      <div id="restoreBox"></div></div>
    <div class="card stack"><h2>Numbering ${y}</h2>''')

# --- events: AI test, backup, restore, provider switch ---
R('''    case"savecounters":''', '''    case"aitest":{const o={...S.settings};document.querySelectorAll("[data-sf]").forEach(i=>o[i.dataset.sf]=i.value);o.gstRate=num(o.gstRate);o.quoteValidDays=num(o.quoteValidDays)||7;delete o.id;
      await saveSettings(o);S.settings={...DEFAULTS,...o};const m=$("#aiTestMsg");if(!aiReady()){m.textContent="Add a key first.";break}
      m.textContent="Testing…";try{const t=await aiText("Reply with just the word OK.");m.textContent=/ok/i.test(t)?"Working ✓":"Connected, unexpected reply: "+t.slice(0,40)}catch(e){m.textContent=e.message||"Test failed."}break}
    case"backup":try{const r=await exportBackup();if(r==="downloaded")toast("Backup downloaded")}catch{toast("Couldn't create the backup.")}break;
    case"restoreok":try{await restoreBackup(S.pendingRestore);toast("Restored. Reloading…");setTimeout(()=>location.reload(),600)}catch{toast("Restore failed. Nothing was changed.")}break;
    case"restorecancel":S.pendingRestore=null;$("#restoreBox").innerHTML="";break;
    case"savecounters":''')
R('''  if(t.id==="logoFile"&&t.files[0]){uploadLogo(t.files[0]);return}''', '''  if(t.id==="logoFile"&&t.files[0]){uploadLogo(t.files[0]);return}
  if(t.id==="aiProvider"){const p=AI_PRESETS[t.value]||{};$("#aiFields").hidden=t.value==="none";$("#aiModel").placeholder=p.model||"model name";$("#aiBase").placeholder=p.base||"https://…/v1";$("#aiKeyHint").textContent=p.keys?"Get a key at "+p.keys:"";S.sDirty=true;return}
  if(t.id==="restoreFile"&&t.files[0]){const box=$("#restoreBox");try{const j=await readBackup(t.files[0]);S.pendingRestore=j;const n=k=>Object.keys(j.records).filter(x=>x.startsWith(k+"/")).length;
      box.innerHTML=`<div class="banner" style="margin:0">Backup from ${esc(fdate(String(j.exportedAt).slice(0,10)))}: ${n("docs")} documents, ${n("products")} products, ${n("customers")} customers.<div class="row" style="margin-top:8px"><button class="btn danger armed" data-act="restoreok">Replace all data on this phone</button><button class="btn ghost" data-act="restorecancel">Cancel</button></div></div>`}
    catch(e){box.innerHTML=`<div class="banner" style="margin:0">${esc(e.message||"Couldn't read that file.")}</div>`}t.value="";return}''')

# --- boot: local database instead of claude.ai capabilities ---
RX(r'/\* ---------- boot ---------- \*/.*?\n\}\)\(\);\n', '''/* ---------- boot ---------- */
let backArm=0;
function handleBack(){
  if(S.view==="editor"){if(S.ed?.dirty&&Date.now()-backArm>3000){backArm=Date.now();toast("Unsaved changes. Press back again to discard.");return true}go("docs");return true}
  if(S.view!=="docs"){go("docs");return true}
  return false;
}
(async()=>{
  render();
  try{await LocalStore.load();await seedIfEmpty()}catch(e){$("#banner").hidden=false;$("#banner").textContent="This phone's storage couldn't be opened. Restart the app.";return}
  registerBlobs();DB=LocalStore;
  DB.doc("settings/main").onSnapshot(s=>{S.settings={...DEFAULTS,...(s.data()||{})};S.ready.settings=true;afterData("settings")});
  for(const col of["products","customers"])DB.collection(col).onSnapshot(q=>{S[col]=q.docs.map(d=>({id:d.id,...d.data()})).sort((a,b)=>String(a.name).localeCompare(String(b.name)));S.ready[col]=true;afterData(col)});
  DB.collection("docs").orderBy("createdAt","desc").onSnapshot(q=>{S.docs=q.docs.map(d=>({id:d.id,...d.data()}));S.ready.docs=true;afterData("docs")});
  setupNative(handleBack);
})();
''')
R('<small>Billing desk · Multan</small>', '<small>Billing · Multan</small>')
R('<button data-nav="products">Catalogue</button>', '<button data-nav="products">Products</button>')

# --- document shell ---
head = '''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<meta name="theme-color" content="#2b3a2f">
<title>Radiant Billing</title>
<link rel="stylesheet" href="fonts/fonts.css">
<link rel="icon" href="data:,">
<style>
@media (max-width:760px){
  .top nav{position:fixed;left:0;right:0;bottom:0;z-index:8;margin:0;background:var(--deep);display:grid;grid-template-columns:repeat(5,1fr);gap:0;
    padding:6px max(6px,env(safe-area-inset-right,0px)) calc(6px + env(safe-area-inset-bottom,0px)) max(6px,env(safe-area-inset-left,0px));border-top:1px solid rgba(255,255,255,.08);overflow:visible}
  .top nav button{padding:9px 2px;font-size:12.5px;text-align:center;border-radius:8px}
  .wrap{padding-bottom:calc(84px + env(safe-area-inset-bottom,0px))!important}
  .pgrid{grid-template-columns:repeat(2,minmax(0,1fr))!important;gap:10px!important}
  .pcard .bd{padding:10px!important}
  .pcard .pr{flex-direction:column;align-items:flex-start!important;gap:6px}
  .toast{bottom:calc(80px + env(safe-area-inset-bottom,0px))!important}
}
</style>
<style>:root{color-scheme:light;padding-top:env(safe-area-inset-top,0px);padding-bottom:env(safe-area-inset-bottom,0px)}body{margin:0;font-size:14px;-webkit-tap-highlight-color:transparent}img{max-width:100%}[hidden]{display:none!important}</style>
</head>
<body>
'''
R('<script>\n"use strict";', '<script src="platform.js"></script>\n<script src="localitems.js"></script>\n<script>\n"use strict";')
out = head + s + "\n</body>\n</html>\n"
assert "claude.use" not in out and "window.claude" not in out, "claude runtime reference left"
assert "googleapis" not in out and "jsdelivr" not in out and "cdnjs" not in out, "external URL left"

# --- write www ---
if os.path.exists(WWW): shutil.rmtree(WWW)
os.makedirs(os.path.join(WWW, "vendor")); os.makedirs(os.path.join(WWW, "fonts")); os.makedirs(os.path.join(WWW, "img"))
open(os.path.join(WWW, "index.html"), "w", encoding="utf-8").write(out)
for f in ["platform.js", "localitems.js"]:
    shutil.copy(os.path.join(ROOT, "src", f), os.path.join(WWW, f))
shutil.copy(os.path.join(NM, "pdf-lib/dist/pdf-lib.min.js"), os.path.join(WWW, "vendor"))
shutil.copy(os.path.join(NM, "@pdf-lib/fontkit/dist/fontkit.umd.min.js"), os.path.join(WWW, "vendor"))
css = []
for w in ("400", "500", "600", "700"):
    shutil.copy(os.path.join(NM, f"@fontsource/figtree/files/figtree-latin-{w}-normal.woff2"), os.path.join(WWW, "fonts"))
    css.append(f'@font-face{{font-family:"Figtree";font-style:normal;font-weight:{w};font-display:swap;src:url(figtree-latin-{w}-normal.woff2) format("woff2")}}')
for w, st in (("400", "normal"), ("700", "normal"), ("400", "italic"), ("700", "italic")):
    fn = f"arimo-latin-{w}-{st}.woff2"
    shutil.copy(os.path.join(NM, f"@fontsource/arimo/files/{fn}"), os.path.join(WWW, "fonts"))
    css.append(f'@font-face{{font-family:"Arimo";font-style:{st};font-weight:{w};font-display:swap;src:url({fn}) format("woff2")}}')
open(os.path.join(WWW, "fonts", "fonts.css"), "w").write("\n".join(css) + "\n")
for f in glob.glob(os.path.join(ROOT, "src", "img", "*")):
    shutil.copy(f, os.path.join(WWW, "img"))
shutil.copy(os.path.join(ROOT, "src", "seed.json"), os.path.join(WWW, "seed.json"))
print("www built:", sum(os.path.getsize(os.path.join(dp, f)) for dp, _, fs in os.walk(WWW) for f in fs) // 1024, "KB")
