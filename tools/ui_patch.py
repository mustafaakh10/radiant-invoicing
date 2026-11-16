#!/usr/bin/env python3
"""One-off patch: cleaner Settings (side menu, one section at a time, save bar) and a
slide-over product editor with labelled groups. Adds hooks so the phone and web builds
can add their own Settings sections and actions (SETTINGS_EXTRA, PLATFORM_ACTS, PLATFORM_CHANGE)."""
import os, re
P = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src", "app.src.html")
s = open(P, encoding="utf-8").read()
def R(a, b, cnt=1):
    global s
    n = s.count(a); assert n == cnt, f"expected {cnt}, found {n}: {a[:120]!r}"; s = s.replace(a, b)

# ======================= Settings =======================
a = s.index("async function vSettings(){")
b = s.index("\nasync function uploadLogo(file){")
s = s[:a] + r'''/* Settings: one section at a time. Platform builds add sections through SETTINGS_EXTRA. */
const setSections=()=>[
  {id:"company",label:"Company",sub:"Name, contact and bank details printed on every document."},
  {id:"brand",label:"Logo & signature",sub:"How your documents are branded and signed."},
  {id:"docs",label:"Documents",sub:"Tax, validity, notes and terms used on new documents."},
  {id:"numbers",label:"Numbering",sub:"The last number used this year for each document type."},
  {id:"catalogue",label:"Products & costs",sub:"Cost prices and loading a product file."},
  ...(typeof SETTINGS_EXTRA!=="undefined"?SETTINGS_EXTRA:[])];
const sfIn=(k,l,o={})=>`<label class="f${o.full?" full":""}">${l}${o.hint?` <span class="muted fh">${o.hint}</span>`:""}<input data-sf="${k}" value="${esc(S.settings[k]??"")}"${o.ph?` placeholder="${esc(o.ph)}"`:""}${o.num?` inputmode="decimal"`:""}></label>`;
const sfTa=(k,l,rows,hint)=>`<label class="f">${l}${hint?` <span class="muted fh">${hint}</span>`:""}<textarea data-sf="${k}" rows="${rows}">${esc(S.settings[k]??"")}</textarea></label>`;
const sCard=(title,body,sub)=>`<div class="card stack scard"><div><h3>${title}</h3>${sub?`<p class="muted ssub">${sub}</p>`:""}</div>${body}</div>`;
function settingsBody(id){
  const s=S.settings,y=todayISO().slice(0,4);
  if(id==="company")return sCard("Business",`<div class="g2">${sfIn("company","Company name")}${sfIn("tagline","Tagline")}${sfIn("address","Address",{full:true})}${sfIn("phone","Phone")}${sfIn("email","Email")}${sfIn("website","Website")}</div>`)
    +sCard("Tax registration",`<div class="g2">${sfIn("ntn","NTN",{ph:"Leave blank to hide"})}${sfIn("strn","STRN",{ph:"Leave blank to hide"})}</div>`,"Printed under your company name only when filled in.")
    +sCard("Bank details",`<div class="g2">${sfIn("bankTitle","Account title")}${sfIn("bankName","Bank & branch")}${sfIn("bankAcc","Account no.")}${sfIn("iban","IBAN")}</div>`,"Shown on quotations and invoices so customers can pay.");
  if(id==="brand")return sCard("Logo",`<label class="logo-drop" id="logoDrop" for="logoFile"><span class="logo-paper"><img id="logoImg" src="${esc(s.logo||LOGO)}" alt="Current logo"></span>
        <span class="logo-cta"><b>Drop your logo here</b> or tap to choose a PNG or JPG</span><input type="file" accept="image/png,image/jpeg" id="logoFile" hidden></label>
      <div id="logoInfo" class="logo-info">Checking resolution…</div>
      <div class="row">${s.logo?`<button class="btn sm ghost" data-act="resetlogo">Use original logo</button>`:""}<span class="muted fh">A wide PNG on white or transparent, about 500 px wide or more, prints sharpest.</span></div>`)
    +sCard("Signature",`<label class="logo-drop" for="signFile"><span class="logo-paper" style="min-height:70px">${s.signImg?`<img src="${esc(s.signImg)}" alt="Your signature" style="max-height:70px">`:`<span class="muted" style="font-size:13px">No signature yet</span>`}</span>
        <span class="logo-cta"><b>${s.signImg?"Replace signature":"Add your signature"}</b>: a photo or PNG of it on white paper. The background is removed automatically.</span><input type="file" accept="image/png,image/jpeg" id="signFile" hidden></label>
      <label class="slashtog"><input type="checkbox" id="signOn" ${s.signOn!==false?"checked":""}><span><b>Sign quotations, invoices and purchase orders</b><br><span class="muted">Delivery notes stay unsigned for the driver and customer.</span></span></label>
      <div class="g2">${sfIn("signName","Name under the signature")}${sfIn("signTitle","Title under the signature")}</div>
      ${s.signImg?`<div><button class="btn sm ghost danger ${S.armed==="delsign"?"armed":""}" data-act="resetsign">${S.armed==="delsign"?"Confirm: remove signature":"Remove signature"}</button></div>`:""}`);
  if(id==="docs")return sCard("Defaults",`<div class="g2">${sfIn("gstRate","GST rate %",{num:true})}${sfIn("quoteValidDays","Quotation valid for (days)",{num:true})}
      <label class="f full">GST on new documents<select data-sf="defaultTax"><option value="excl" ${s.defaultTax==="excl"?"selected":""}>Excluded (shows “Excl.”)</option><option value="add" ${s.defaultTax==="add"?"selected":""}>Add GST</option></select></label></div>`)
    +sCard("Notes & terms",`${sfTa("notesDefault","Default notes",2)}${sfTa("termsQT","Quotation terms",4,"one per line")}${sfTa("termsINV","Invoice terms",4,"one per line")}${sfTa("termsPO","Purchase order terms",4,"one per line")}${sfTa("dnInstructions","Delivery note instructions",4,"one per line")}`);
  if(id==="numbers")return sCard(`Numbering ${y}`,`<div class="g2">${[["QT","Quotations"],["INV","Invoices"],["DN","Delivery notes"],["PO","Purchase orders"]].map(([t,l])=>`<label class="f">${l} <span class="muted fh">RL-${t}-${y}-</span><input id="cnt-${t}" inputmode="numeric" value="…"></label>`).join("")}</div>
      <div><button class="btn" data-act="savecounters">Update numbering</button></div>`,"The next document gets this number + 1. Only change it if you're continuing from another system.");
  if(id==="catalogue")return sCard("Cost prices",`<label class="slashtog"><input type="checkbox" id="showCosts" ${s.showCosts!==false?"checked":""}><span><b>Show costs and margin</b><br><span class="muted">Turn off on a device a salesperson uses. Costs never print on documents either way.</span></span></label>`)
    +sCard("Import products",`<div class="row"><label class="btn">Choose product file<input type="file" accept="application/json,.json" id="importProducts" hidden></label><span id="importMsg" class="muted" style="font-size:13px"></span></div>`,"Load a product file (.json) prepared for you. Products with the same ID are updated; everything else is kept.");
  const x=setSections().find(z=>z.id===id);return x&&x.html?x.html():"";
}
async function vSettings(){
  const secs=setSections(),cur=secs.find(x=>x.id===S.sset)||secs[0],y=todayISO().slice(0,4);S.sset=cur.id;S.sDirty=false;
  $("#view").innerHTML=`<div class="spread" style="margin-bottom:16px"><div><div class="eyebrow">Settings</div><h1>${esc(cur.label)}</h1></div></div>
  <div class="setlayout"><nav class="setnav" aria-label="Settings sections">${secs.map(x=>`<button data-act="sset" data-s="${x.id}" ${x.id===cur.id?`aria-current="page"`:""}>${esc(x.label)}</button>`).join("")}</nav>
    <div class="setmain"><p class="muted setsub">${esc(cur.sub||"")}</p>${settingsBody(cur.id)}</div></div>
  <div class="savebar" id="savebar" hidden><span>You have unsaved changes</span><div class="row"><button class="btn ghost" data-act="sdiscard">Discard</button><button class="btn pri" data-act="savesettings">Save changes</button></div></div>`;
  if(cur.id==="brand")logoQuality();
  if(cur.id==="numbers")for(const t of["QT","INV","DN","PO"]){const v=await counterGet(`${t}-${y}`);const el=$("#cnt-"+t);if(el)el.value=v}
  if(cur.after)cur.after();
}
async function saveSettingsForm(){
  const o={...S.settings};document.querySelectorAll("[data-sf]").forEach(i=>o[i.dataset.sf]=i.type==="checkbox"?i.checked:i.value);
  o.gstRate=num(o.gstRate);o.quoteValidDays=num(o.quoteValidDays)||7;delete o.id;
  await saveSettings(o);S.settings={...DEFAULTS,...o};S.sDirty=false;const sb=$("#savebar");if(sb)sb.hidden=true;
}''' + s[b:]

R('''case"savesettings":{const o={...S.settings};document.querySelectorAll("[data-sf]").forEach(i=>o[i.dataset.sf]=i.value);o.gstRate=num(o.gstRate);o.quoteValidDays=num(o.quoteValidDays)||7;delete o.id;
      try{await saveSettings(o);S.settings={...DEFAULTS,...o};S.sDirty=false;toast("Settings saved")}catch{toast("Couldn't save settings")}break}''',
  '''case"savesettings":try{await saveSettingsForm();toast("Settings saved")}catch{toast("Couldn't save settings")}break;
    case"sset":if(S.sDirty){try{await saveSettingsForm();toast("Saved")}catch{toast("Couldn't save settings");break}}S.sset=b.dataset.s;vSettings();window.scrollTo(0,0);break;
    case"sdiscard":S.sDirty=false;vSettings();break;''')
R('''  if(t.dataset.sf){S.sDirty=true;return}''', '''  if(t.dataset.sf){S.sDirty=true;const sb=$("#savebar");if(sb)sb.hidden=false;return}''')
# nav away from Settings with unsaved changes: save them
R('''  const nb=e.target.closest("[data-nav]");if(nb){const v=nb.dataset.nav;S.pform=null;S.cform=null;go(v);return}''',
  '''  const nb=e.target.closest("[data-nav]");if(nb){const v=nb.dataset.nav;if(S.view==="settings"&&S.sDirty){try{await saveSettingsForm();toast("Settings saved")}catch{}}S.pform=null;S.cform=null;document.body.classList.remove("sheet-open");go(v);return}''')
# platform hooks
R('''  if(b.tagName==="SELECT")return;
  const findDoc=''', '''  if(b.tagName==="SELECT")return;
  if(typeof PLATFORM_ACTS!=="undefined"&&PLATFORM_ACTS[a]){try{await PLATFORM_ACTS[a](b)}catch(err){toast(err?.message||"Something went wrong")}return}
  const findDoc=''')
R('''document.addEventListener("change",async e=>{
  const t=e.target;''', '''document.addEventListener("change",async e=>{
  const t=e.target;
  if(typeof PLATFORM_CHANGE!=="undefined"&&await PLATFORM_CHANGE(t))return;''')

# ======================= Product editor: slide-over sheet =======================
R('''  <div class="two"><div id="plist"></div><div class="formside" id="pform"></div></div>`;renderPList();renderPForm();''',
  '''  <div id="plist"></div><div class="sheet" id="pform" hidden></div>`;renderPList();renderPForm();''')
a = s.index("function renderPForm(){const el=$(\"#pform\");if(!el)return;const p=S.pform;")
b = s.index("\n/* ---------- Customers ---------- */")
s = s[:a] + r'''function renderPForm(){const el=$("#pform");if(!el)return;const p=S.pform;
  if(!p){el.hidden=true;el.innerHTML="";document.body.classList.remove("sheet-open");return}
  const keep=el.querySelector(".sheet-body")?.scrollTop||0,first=el.hidden;
  const cats=[...new Set(S.products.map(x=>String(x.category||"").trim()).filter(Boolean))].sort(byName);
  const sers=[...new Set(S.products.filter(x=>!p.category||String(x.category||"").trim()===String(p.category).trim()).map(x=>String(x.series||"").trim()).filter(Boolean))].sort(byName);
  const vs=p.variants||[],os=p.options||[];
  el.hidden=false;document.body.classList.add("sheet-open");
  el.innerHTML=`<div class="sheet-bg" data-act="cancelprod"></div>
  <aside class="sheet-panel" role="dialog" aria-modal="true" aria-label="${p.id?"Edit product":"New product"}">
   <header class="sheet-head"><div><div class="eyebrow">${p.id?"Edit product":"New product"}</div><h2>${esc(p.name||"Untitled product")}</h2></div><button class="iconbtn" data-act="cancelprod" aria-label="Close">✕</button></header>
   <div class="sheet-body">
    <section class="psec"><h3>Photo &amp; name</h3>
     <div class="pp-top"><label class="pp-photo" for="pPhoto">${p.img?`<img src="${esc(p.img)}" alt="">`:`<span>Add photo</span>`}<input type="file" accept="image/*" id="pPhoto" hidden></label>
      <div class="stack" style="gap:12px;flex:1;min-width:0">
       <label class="f">Name on documents<input data-pf="name" value="${esc(p.name)}" placeholder="LED Wall / Step Light – Trail Series"></label>
       <div class="g2"><label class="f">Category <span class="muted fh">folder</span><input data-pf="category" list="catlist" value="${esc(p.category||"")}" placeholder="e.g. COB"></label><label class="f">Series<input data-pf="series" list="serlist" value="${esc(p.series||"")}" placeholder="e.g. Linea"></label></div>
      </div></div>
     <div class="row" style="gap:8px">${p.img?`<button class="btn sm ghost" data-act="rmphoto">Remove photo</button>`:""}<span id="pPhotoMsg" class="muted fh"></span></div>
     <datalist id="catlist">${cats.map(x=>`<option value="${esc(x)}">`).join("")}</datalist><datalist id="serlist">${sers.map(x=>`<option value="${esc(x)}">`).join("")}</datalist>
    </section>
    <section class="psec"><h3>Details</h3>
     <label class="f">Spec line <span class="muted fh">printed under the name</span><input data-pf="spec" value="${esc(p.spec)}" placeholder="3W · 140 lm · CRI >80 · IP65"></label>
     <div class="g2"><label class="f">Warranty<input data-pf="warranty" value="${esc(p.warranty||"")}" placeholder="2 years replacement warranty"></label><label class="f">Unit<input data-pf="unit" value="${esc(p.unit||"Pcs")}" placeholder="Pcs"></label></div>
     <p class="muted fh">Warranty prints only when it's 1 year or more.</p>
    </section>
    <section class="psec"><h3>Price</h3>
     <div class="g2"><label class="f">Sale price <span class="muted fh">PKR</span><input data-pf="price" inputmode="decimal" value="${esc(p.price)}"></label><label class="f">Cost price <span class="muted fh">private</span><input data-pf="cost" inputmode="decimal" value="${esc(p.cost??"")}"></label></div>
     <label class="f">Supplier <span class="muted fh">purchase orders go here</span><select data-pf="supplierId"><option value="">None</option>${S.suppliers.map(x=>`<option value="${esc(x.id)}" ${supOf(p)?.id===x.id?"selected":""}>${esc(x.name)}</option>`).join("")}</select></label>
     <div class="helper"><span>Cost = sale price −</span><input id="costPct" inputmode="decimal" value="${esc(p.supplierDisc??30)}" aria-label="Supplier discount percent"><span>%</span><button class="btn sm" data-act="costfill">Apply</button><b id="pmargin">${formMargin(p)}</b></div>
    </section>
    <section class="psec"><div class="spread"><h3>Sizes</h3><button class="btn sm" data-act="addvar">+ Add size</button></div>
     ${vs.length?`<div class="vtable"><div class="vth"><span>Size</span><span>Sale price</span><span>Cost</span><span>Model code</span><span></span></div>
      ${vs.map((v,i)=>`<div class="vtr"><input data-vf="${i}.label" value="${esc(v.label)}" placeholder="Size, e.g. 12W" aria-label="Size"><input data-vf="${i}.price" inputmode="decimal" value="${esc(v.price)}" placeholder="Sale price" aria-label="Sale price"><input data-vf="${i}.cost" inputmode="decimal" value="${esc(v.cost??"")}" placeholder="Cost" aria-label="Cost"><input data-vf="${i}.model" value="${esc(v.model)}" placeholder="Model code" aria-label="Model code"><button class="iconbtn danger" data-act="rmvar" data-i="${i}" aria-label="Remove size">✕</button>
        <input class="vspec" data-vf="${i}.spec" value="${esc(v.spec)}" placeholder="Spec line for this size, e.g. 12W · 1080 lm · Cut-out Ø90" aria-label="Spec line"></div>`).join("")}</div>
      <p class="muted fh">A size with no sale price uses the price above.</p>`:`<p class="muted fh">Only for products sold in several sizes (5W / 7W / 12W). Each size gets its own price, cost and code.</p>`}
    </section>
    <section class="psec"><div class="spread"><h3>Options</h3><button class="btn sm" data-act="addopt">+ Add option</button></div>
     ${os.length?`<div class="otable"><div class="oth"><span>Option</span><span>Choices <span class="muted">comma separated</span></span><span>Only for sizes</span><span></span></div>
      ${os.map((o,i)=>`<div class="otr"><input data-of="${i}.name" value="${esc(o.name)}" placeholder="Option, e.g. CCT" aria-label="Option name"><input data-of="${i}.values" value="${esc(o.values)}" placeholder="3000K, 4000K, 6000K" aria-label="Choices"><input data-of="${i}.only" value="${esc(o.only)}" placeholder="Only for sizes (blank = all)" aria-label="Only for sizes"><button class="iconbtn danger" data-act="rmopt" data-i="${i}" aria-label="Remove option">✕</button></div>`).join("")}</div>`
      :`<p class="muted fh">Choices picked per order, like colour temperature or finish.</p>`}
    </section>
    <section class="psec"><h3>Quick entry</h3>
     <div class="g2"><label class="f">Model / code<input data-pf="model" value="${esc(p.model)}"></label><label class="f">Shorthand words <span class="muted fh">what you type</span><input data-pf="keywords" value="${esc(p.keywords)}" placeholder="trail, step light"></label></div>
    </section>
   </div>
   <footer class="sheet-foot">${p.id?`<button class="btn ghost danger ${S.armed===p.id?"armed":""}" data-act="delprod">${S.armed===p.id?"Confirm delete":"Delete"}</button>`:"<span></span>"}
    <div class="row"><button class="btn ghost" data-act="cancelprod">Cancel</button><button class="btn pri" data-act="saveprod">Save product</button></div></footer>
  </aside>`;
  const body=el.querySelector(".sheet-body");if(body&&!first)body.scrollTop=keep;
  if(first)setTimeout(()=>el.querySelector('[data-pf="name"]')?.focus({preventScroll:true}),60);
}
document.addEventListener("keydown",e=>{if(e.key==="Escape"&&S.pform&&S.view==="products"){S.pform=null;renderPForm()}});
''' + s[b:]
R('''renderPForm();$("#pform").scrollIntoView({block:"nearest"});break;''', '''renderPForm();break;''', 2)

# ======================= styles =======================
R('/* orders */', '''/* settings */
.setlayout{display:grid;grid-template-columns:220px minmax(0,1fr);gap:24px;align-items:start}
.setnav{position:sticky;top:76px;display:flex;flex-direction:column;gap:2px}
.setnav button{all:unset;cursor:pointer;padding:9px 12px;border-radius:8px;font-weight:600;font-size:14px;color:var(--muted)}
.setnav button:hover{background:var(--sunk);color:var(--ink)}
.setnav button[aria-current]{background:var(--surface);color:var(--ink);box-shadow:inset 3px 0 0 var(--accent);border:1px solid var(--line)}
.setnav button:focus-visible{outline:2px solid var(--focus)}
.setmain{display:flex;flex-direction:column;gap:16px;max-width:760px;padding-bottom:90px}
.setsub{margin:-8px 0 0;font-size:14px}
.scard h3{margin:0;font-size:15px}.ssub{margin:4px 0 0;font-size:13px}
.g2 .full{grid-column:1/-1}
.fh{font-weight:400;font-size:12px}
.savebar{position:fixed;left:50%;transform:translateX(-50%);bottom:20px;z-index:20;display:flex;align-items:center;gap:16px;background:var(--deep);color:var(--on-deep);padding:10px 12px 10px 18px;border-radius:12px;box-shadow:0 12px 30px rgba(0,0,0,.22);font-weight:600;font-size:14px;width:max-content;max-width:calc(100% - 32px)}
.savebar .btn.ghost{color:var(--on-deep)}
@media (max-width:760px){
  .setlayout{grid-template-columns:minmax(0,1fr);gap:12px}
  .setnav{position:sticky;top:0;z-index:5;flex-direction:row;overflow-x:auto;gap:6px;padding:8px 0;margin:0 -16px;padding-left:16px;padding-right:16px;background:var(--bg);scrollbar-width:none}
  .setnav button{white-space:nowrap;border:1px solid var(--line);background:var(--surface);padding:7px 12px;font-size:13px}
  .setnav button[aria-current]{box-shadow:none;background:var(--deep);color:var(--on-deep);border-color:var(--deep)}
  .savebar{bottom:calc(84px + env(safe-area-inset-bottom,0px));left:16px;right:16px;transform:none;width:auto;justify-content:space-between}
}
/* product editor sheet */
body.sheet-open{overflow:hidden}
.sheet{position:fixed;inset:0;z-index:40}
.sheet-bg{position:absolute;inset:0;background:rgba(15,22,16,.45)}
.sheet-panel{position:absolute;top:0;right:0;bottom:0;width:min(720px,100%);background:var(--bg);display:flex;flex-direction:column;box-shadow:-20px 0 40px rgba(0,0,0,.18);animation:sheetin .18s ease-out}
@keyframes sheetin{from{transform:translateX(24px);opacity:.6}to{transform:none;opacity:1}}
.sheet-head{display:flex;justify-content:space-between;align-items:flex-start;gap:12px;padding:18px 24px 14px;border-bottom:1px solid var(--line);background:var(--surface)}
.sheet-head h2{margin:2px 0 0;font-size:19px;overflow-wrap:anywhere}
.sheet-body{flex:1;overflow-y:auto;padding:16px 24px 24px;display:flex;flex-direction:column;gap:14px}
.sheet-foot{display:flex;justify-content:space-between;align-items:center;gap:10px;padding:12px 24px calc(12px + env(safe-area-inset-bottom,0px));border-top:1px solid var(--line);background:var(--surface)}
.iconbtn{all:unset;cursor:pointer;width:34px;height:34px;border-radius:8px;display:grid;place-items:center;color:var(--muted);font-size:15px}
.iconbtn:hover{background:var(--sunk);color:var(--ink)}.iconbtn.danger:hover{background:var(--danger-bg);color:var(--danger)}
.iconbtn:focus-visible{outline:2px solid var(--focus)}
.psec{background:var(--surface);border:1px solid var(--line);border-radius:12px;padding:16px;display:flex;flex-direction:column;gap:12px}
.psec h3{margin:0;font-size:14px;letter-spacing:.02em}
.psec .fh{margin:0}
.pp-top{display:flex;gap:16px;align-items:flex-start}
.pp-photo{flex:0 0 116px;width:116px;height:116px;border-radius:10px;border:1px dashed var(--line);background:#fff;display:grid;place-items:center;cursor:pointer;overflow:hidden;color:var(--muted);font-size:13px;font-weight:600}
.pp-photo img{width:100%;height:100%;object-fit:contain}
.pp-photo:hover{border-color:var(--accent)}
.helper{display:flex;align-items:center;flex-wrap:wrap;gap:8px;font-size:13px;color:var(--muted);background:var(--sunk);border-radius:8px;padding:8px 10px}
.helper input{width:56px;padding:5px 8px}.helper b{margin-left:auto;color:var(--accent-ink);font-weight:700}
.vtable,.otable{display:flex;flex-direction:column;border:1px solid var(--line);border-radius:10px;overflow:hidden}
.vth,.vtr{display:grid;grid-template-columns:1fr 1fr 1fr 1.3fr 34px;gap:8px;align-items:center;padding:8px 10px}
.oth,.otr{display:grid;grid-template-columns:1fr 2fr 1.2fr 34px;gap:8px;align-items:center;padding:8px 10px}
.vth,.oth{background:var(--sunk);font-size:11.5px;font-weight:700;text-transform:uppercase;letter-spacing:.04em;color:var(--muted)}
.vtr,.otr{border-top:1px solid var(--line)}
.vtr .vspec{grid-column:1/5;font-size:13px}
.vtr input,.otr input{min-width:0}
@media (max-width:760px){
  .sheet-panel{width:100%}
  .sheet-head,.sheet-body,.sheet-foot{padding-left:16px;padding-right:16px}
  .sheet-foot{padding-bottom:calc(12px + env(safe-area-inset-bottom,0px))}
  .pp-top{flex-direction:column}.pp-photo{width:100%;flex-basis:auto;height:160px}
  .vth{display:none}.vtr{grid-template-columns:1fr 1fr 34px}
  .vtr>:nth-child(1){grid-area:1/1}.vtr>:nth-child(2){grid-area:1/2}.vtr>:nth-child(5){grid-area:1/3}
  .vtr>:nth-child(3){grid-area:2/1}.vtr>:nth-child(4){grid-area:2/2}.vtr>:nth-child(6){grid-area:3/1/4/4}
  .oth{display:none}.otr{grid-template-columns:1fr 34px}
  .otr>:nth-child(1){grid-area:1/1}.otr>:nth-child(4){grid-area:1/2}.otr>:nth-child(2){grid-area:2/1/3/3}.otr>:nth-child(3){grid-area:3/1/4/3}
}
/* orders */''')

open(P, "w", encoding="utf-8").write(s)
print("patched")
