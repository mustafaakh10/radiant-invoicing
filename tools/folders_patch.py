#!/usr/bin/env python3
"""One-off patch: catalogue folders (Category → Series → products), search, shared-keyword size disambiguation."""
import os
P = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src", "app.src.html")
s = open(P, encoding="utf-8").read()
def R(a, b, cnt=1):
    global s
    n = s.count(a); assert n == cnt, f"expected {cnt}, found {n}: {a[:110]!r}"; s = s.replace(a, b)

# 1) catalogue list → folders
start = s.index('function renderPList(){const el=$("#plist");if(!el)return;')
end = s.index('function renderPForm(){')
old = s[start:end]
card_start = old.index('S.products.map(p=>`') + len('S.products.map(p=>')
card_end = old.index('`).join("")}</div>`', card_start) + 1
card = old[card_start:card_end]
s = s[:start] + r'''const catOf=p=>String(p.category||"").trim()||"Uncategorised";
const serOf=p=>String(p.series||"").trim();
const pCard=p=>''' + card + r''';
const pGrid=list=>`<div class="pgrid">${list.map(pCard).join("")}</div>`;
const byName=(a,b)=>String(a).localeCompare(String(b),undefined,{numeric:true});
function folderTile(act,key,title,list,sub){const pics=list.filter(p=>p.img).slice(0,3);
  return `<button class="ftile" data-act="${act}" data-c="${esc(key)}"><span class="fpics">${pics.length?pics.map(p=>`<img src="${esc(p.img)}" alt="">`).join(""):`<span class="fnone">${esc(title.slice(0,1))}</span>`}</span>
    <span class="fname">${esc(title)}</span><span class="fsub">${sub}</span></button>`}
function renderPList(){const el=$("#plist");if(!el)return;
  if(!S.products.length){el.innerHTML=`<div class="card empty">${S.ready.products||!DB?"No products yet. Add your first one with a photo, price and the shorthand you use for it.":"Loading catalogue…"}</div>`;return}
  if(!$("#pbody"))el.innerHTML=`<div class="pnav"><input id="pq" type="search" placeholder="Search all products, sizes, codes" value="${esc(S.pq||"")}" aria-label="Search products"><div class="crumbs" id="crumbs"></div></div><div id="pbody"></div>`;
  renderPBody();
}
function renderPBody(){const body=$("#pbody"),cr=$("#crumbs");if(!body)return;
  const q=String(S.pq||"").trim().toLowerCase(),cat=S.pcat||"",ser=S.pser||"";
  const c=[`<button class="crumb" data-act="pcat" data-c="">All products</button>`];
  if(!q&&cat)c.push(`<button class="crumb" data-act="pcat" data-c="${esc(cat)}">${esc(cat)}</button>`);
  if(!q&&cat&&ser)c.push(`<span class="crumb on">${esc(ser)}</span>`);
  cr.innerHTML=q?`<span class="crumb on">Search results</span>`:c.join(`<span class="sep">›</span>`);
  if(q){const hits=S.products.filter(p=>`${p.name} ${p.spec||""} ${p.keywords||""} ${p.category||""} ${p.series||""} ${p.model||""} ${(p.variants||[]).map(v=>`${v.label} ${v.model||""}`).join(" ")}`.toLowerCase().includes(q)).sort((a,b)=>byName(a.name,b.name));
    body.innerHTML=hits.length?pGrid(hits):`<div class="card empty">No products match “${esc(S.pq)}”.</div>`;return}
  if(!cat){const g=new Map();for(const p of S.products){const k=catOf(p);if(!g.has(k))g.set(k,[]);g.get(k).push(p)}
    const keys=[...g.keys()].sort((a,b)=>(a==="Uncategorised")-(b==="Uncategorised")||byName(a,b));
    body.innerHTML=`<div class="ftiles">${keys.map(k=>{const l=g.get(k),ns=new Set(l.map(serOf).filter(Boolean)).size;return folderTile("pcat",k,k,l,`${l.length} product${l.length===1?"":"s"}${ns?` · ${ns} series`:""}`)}).join("")}</div>`;return}
  const inCat=S.products.filter(p=>catOf(p)===cat);
  if(!ser){const g=new Map(),loose=[];for(const p of inCat){const k=serOf(p);if(!k){loose.push(p);continue}if(!g.has(k))g.set(k,[]);g.get(k).push(p)}
    const keys=[...g.keys()].sort(byName);
    body.innerHTML=(keys.length?`<div class="ftiles">${keys.map(k=>folderTile("pser",k,k,g.get(k),`${g.get(k).length} product${g.get(k).length===1?"":"s"}`)).join("")}</div>`:"")
      +(loose.length?`${keys.length?`<div class="eyebrow" style="margin:18px 0 10px">Not in a series</div>`:""}${pGrid(loose.sort((a,b)=>byName(a.name,b.name)))}`:"");
    if(!inCat.length)body.innerHTML=`<div class="card empty">This folder is empty.</div>`;return}
  const list=inCat.filter(p=>serOf(p)===ser).sort((a,b)=>byName(a.name,b.name));
  body.innerHTML=list.length?pGrid(list):`<div class="card empty">This series is empty.</div>`;
}
''' + s[end:]

R('''   <label class="f">Name on document<input data-pf="name" value="${esc(p.name)}" placeholder="LED Wall / Step Light – Trail Series"></label>''',
  '''   <label class="f">Name on document<input data-pf="name" value="${esc(p.name)}" placeholder="LED Wall / Step Light – Trail Series"></label>
   <div class="g2"><label class="f">Category (folder)<input data-pf="category" list="catlist" value="${esc(p.category||"")}" placeholder="e.g. SMD, COB, Strip"></label><label class="f">Series<input data-pf="series" list="serlist" value="${esc(p.series||"")}" placeholder="e.g. Rayzen, Linea"></label></div>
   <datalist id="catlist">${[...new Set(S.products.map(x=>String(x.category||"").trim()).filter(Boolean))].sort(byName).map(x=>`<option value="${esc(x)}">`).join("")}</datalist>
   <datalist id="serlist">${[...new Set(S.products.filter(x=>!p.category||String(x.category||"").trim()===String(p.category).trim()).map(x=>String(x.series||"").trim()).filter(Boolean))].sort(byName).map(x=>`<option value="${esc(x)}">`).join("")}</datalist>''')
R('''S.pform={id:"",name:"",spec:"",warranty:"",price:"",unit:"Pcs",model:"",keywords:"",img:"",variants:[],options:[]};''',
  '''S.pform={id:"",name:"",category:S.pcat&&S.pcat!=="Uncategorised"?S.pcat:"",series:S.pser||"",spec:"",warranty:"",price:"",unit:"Pcs",model:"",keywords:"",img:"",variants:[],options:[]};''')
R('''      await put("products",pid,{name:p.name.trim(),spec:p.spec||"",''', '''      await put("products",pid,{name:p.name.trim(),category:String(p.category||"").trim(),series:String(p.series||"").trim(),spec:p.spec||"",''')
R('''    case"cancelprod":''', '''    case"pcat":S.pcat=b.dataset.c||"";S.pser="";S.pq="";if($("#pq"))$("#pq").value="";renderPBody();$("#plist").scrollIntoView({block:"start",behavior:"smooth"});break;
    case"pser":S.pser=b.dataset.c||"";renderPBody();$("#plist").scrollIntoView({block:"start",behavior:"smooth"});break;
    case"cancelprod":''')
R('''  if(t.dataset.pf&&S.pform){S.pform[t.dataset.pf]=t.value;return}''', '''  if(t.id==="pq"){S.pq=t.value;renderPBody();return}
  if(t.dataset.pf&&S.pform){S.pform[t.dataset.pf]=t.value;return}''')
R('''await put("products",id,{spec:"",warranty:"",price:0,''', '''await put("products",id,{category:"",series:"",spec:"",warranty:"",price:0,''')
R('''  else if(S.view==="products"&&col==="products")renderPList();''', '''  else if(S.view==="products"&&col==="products"){if(S.pcat&&!S.products.some(p=>catOf(p)===S.pcat)){S.pcat="";S.pser=""}renderPList()}''')

# 2) two products sharing a word ("rayzen" linear / square): the size typed decides
R('''    if(last&&m.start<last.end){if(m.w>last.w&&m.p!==last.p)kept[kept.length-1]=m;continue}''',
  '''    if(last&&m.start<last.end){if(m.start===last.start&&m.end===last.end&&m.p!==last.p){(last.alts=last.alts||[]).push(m.p);continue}if(m.w>last.w&&m.p!==last.p)kept[kept.length-1]=m;continue}''')
R('''    const r=readVariant(mt.p,seg.join(""));''', '''    let r=readVariant(mt.p,seg.join(""));
    if(hasVar(mt.p)&&!r.v&&mt.alts)for(const q of mt.alts){const r2=readVariant(q,seg.join(""));if(r2.v){mt.p=q;r=r2;break}}''')

# 3) styles
R('/* orders */', '''.pnav{display:flex;flex-direction:column;gap:10px;margin-bottom:14px}
.pnav input{max-width:420px}
.crumbs{display:flex;flex-wrap:wrap;align-items:center;gap:4px;font-size:13px}
.crumb{background:none;border:0;padding:4px 6px;border-radius:6px;cursor:pointer;color:var(--accent-ink);font-weight:600}
.crumb:hover{background:var(--sunk)}.crumb.on{color:var(--ink);cursor:default}.crumbs .sep{color:var(--muted)}
.ftiles{display:grid;grid-template-columns:repeat(auto-fill,minmax(170px,1fr));gap:12px}
.ftile{display:flex;flex-direction:column;gap:6px;text-align:left;background:var(--surface);border:1px solid var(--line);border-radius:10px;padding:10px;cursor:pointer;font:inherit;color:inherit}
.ftile:hover{border-color:var(--accent)}
.fpics{display:grid;grid-template-columns:repeat(3,1fr);gap:4px;aspect-ratio:3/1;max-width:100%;background:var(--sunk);border-radius:7px;overflow:hidden}
.fpics img{width:100%;height:100%;object-fit:contain;background:#fff}
.fnone{grid-column:1/-1;display:flex;align-items:center;justify-content:center;font-size:22px;font-weight:700;color:var(--muted)}
.fname{font-weight:700}.fsub{font-size:12px;color:var(--muted)}
@media (max-width:760px){.ftiles{grid-template-columns:repeat(2,minmax(0,1fr))}}
/* orders */''')

open(P, "w", encoding="utf-8").write(s)
print("patched")
