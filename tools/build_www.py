#!/usr/bin/env python3
"""Builds www/ (the app shipped inside the APK) from the web-app source + device layer."""
import json, os, re, shutil, glob, sys

# --web builds the same app for the Django server (web/billing/static/app) instead of the Android www/
WEB = "--web" in sys.argv

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "src", "app.src.html")
WWW = os.path.join(ROOT, "web", "billing", "static", "app") if WEB else os.path.join(ROOT, "www")
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
R('esc(p.img)', 'esc(imgSrc(p.img))', 3)
R('esc(s.logo||LOGO)', 'esc(imgSrc(s.logo)||LOGO)', 2)
R('await image(s.logo||LOGO,', 'await image(imgSrc(s.logo)||LOGO,')
R('  async function image(src,x,y,w,h){\n    if(!src)return false;', '  async function image(src,x,y,w,h){\n    src=imgSrc(src);if(!src)return false;')
RX(r'async function storeImage\(blob\)\{.*?\n\}\n', 'async function storeImage(blob){return storeImageLocal(blob)}\n')
R('const LIBS={pdf:"https://cdn.jsdelivr.net/npm/pdf-lib@1.17.1/dist/pdf-lib.min.js",fk:"https://cdn.jsdelivr.net/npm/@pdf-lib/fontkit@1.1.1/dist/fontkit.umd.min.js"};',
  'const LIBS={pdf:"vendor/pdf-lib.min.js",fk:"vendor/fontkit.umd.min.js"};')

# defaults: AI settings
R('  logo:""\n};', '  logo:"",aiProvider:"none",aiBase:"",aiModel:"",aiKey:""\n};')

# --- PDF: share sheet (phone) / download or share sheet (web) instead of claude.ai download ---
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
if not WEB:
  R('${S.ed.id?"Download PDF":"Save & download PDF"}', '${S.ed.id?"Share PDF":"Save & share PDF"}')
  R('<button class="btn sm" data-act="pdf" data-id="${d.id}">PDF</button>', '<button class="btn sm" data-act="pdf" data-id="${d.id}">Share PDF</button>')
R('if(/\\b(download|export)\\b.*\\bpdf\\b|^pdf$/.test(lc)){S.ed.after="pdf";return"Will save & download PDF"}',
  'if(/\\b(download|export|share|send|whatsapp)\\b.*\\bpdf\\b|^(pdf|share|whatsapp|share pdf|send)$/.test(lc)){S.ed.after="pdf";return"Will save & share PDF"}')
R('“save” · “pdf” · “convert to invoice”', '“save” · “share” · “convert to invoice”')
if not WEB: R("Couldn't save. Check your connection and try again.", "Couldn't save on this phone. Try again.")

# --- quick entry wording ---
R("New items are matched to your catalogue on your device, sizes and options included; AI is only used for lines it can't place. Totals are always computed here.",
  "New items are matched to your catalogue first, sizes and options included; AI is only used for lines it can't place, and only if you add a key in Settings. Totals are always computed here." if WEB else "Everything runs on this phone. New items are matched to your catalogue, sizes and options included; AI is only used for lines it can't place, and only if you add a key in Settings. Totals are always computed here.")

# --- AI: provider from Settings (local-first logic lives in the shared source) ---
R('const AIX={ready:()=>!!SAMPLE,json:p=>SAMPLE.json(p,{modelTier:"default"})};', 'const AIX={ready:aiReady,json:aiJson};')

# --- Settings: AI, backup (and account on the web) come from the platform file as extra sections ---
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
  try{await LocalStore.load();await seedIfEmpty();if(typeof aiLoad==="function")await aiLoad()}catch(e){$("#banner").hidden=false;$("#banner").textContent=BOOT_FAIL;return}
  registerBlobs();DB=LocalStore;
  DB.doc("settings/main").onSnapshot(s=>{S.settings={...DEFAULTS,...(s.data()||{})};S.ready.settings=true;afterData("settings")});
  for(const col of["products","customers","suppliers"])DB.collection(col).onSnapshot(q=>{S[col]=q.docs.map(d=>({id:d.id,...d.data()})).sort((a,b)=>String(a.name).localeCompare(String(b.name)));S.ready[col]=true;afterData(col)});
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
BASE_TAG
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
R('<script>\n"use strict";', '<script src="platform.js"></script>\n<script>\n"use strict";')
head = head.replace("BASE_TAG\n", '<base href="/static/app/">\n' if WEB else "")
s = s.replace("BOOT_FAIL", json.dumps("Couldn't load your data. Check your connection and reload the page." if WEB else "This phone's storage couldn't be opened. Restart the app."))
out = head + s + "\n</body>\n</html>\n"
assert "claude.use" not in out and "window.claude" not in out, "claude runtime reference left"
assert "googleapis" not in out and "jsdelivr" not in out and "cdnjs" not in out, "external URL left"

# --- write www ---
if os.path.exists(WWW): shutil.rmtree(WWW)
os.makedirs(os.path.join(WWW, "vendor")); os.makedirs(os.path.join(WWW, "fonts")); os.makedirs(os.path.join(WWW, "img"))
open(os.path.join(WWW, "index.html"), "w", encoding="utf-8").write(out)
shutil.copy(os.path.join(ROOT, "src", "platform_web.js" if WEB else "platform.js"), os.path.join(WWW, "platform.js"))
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
if not WEB:
    shutil.copy(os.path.join(ROOT, "src", "seed.json"), os.path.join(WWW, "seed.json"))
print(("web app built (web/billing/static/app):" if WEB else "www built:"), sum(os.path.getsize(os.path.join(dp, f)) for dp, _, fs in os.walk(WWW) for f in fs) // 1024, "KB")
