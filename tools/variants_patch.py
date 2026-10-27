#!/usr/bin/env python3
"""One-off patch: adds product variants (sizes + per-order options) and catalogue matching to app.src.html."""
import os, re, sys
P = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src", "app.src.html")
s = open(P, encoding="utf-8").read()
def R(a, b, cnt=1):
    global s
    n = s.count(a); assert n == cnt, f"expected {cnt}, found {n}: {a[:100]!r}"; s = s.replace(a, b)
def RX(pat, repl, cnt=1):
    global s
    s, n = re.subn(pat, lambda m: repl, s, flags=re.S); assert n == cnt, f"regex {n}: {pat[:80]!r}"

VARIANTS = r'''/* ---------- product variants: sizes (own price / code / spec) + options chosen per order ---------- */
const hasVar=p=>Array.isArray(p?.variants)&&p.variants.length>0;
const varOf=(p,vid)=>hasVar(p)&&vid?p.variants.find(v=>v.id===vid)||null:null;
const optsFor=(p,v)=>(p?.options||[]).filter(o=>o&&o.name&&Array.isArray(o.values)&&o.values.length&&(!o.only?.length||(v&&o.only.some(x=>String(x).toLowerCase()===String(v.label).toLowerCase()))));
function composeSpec(p,v,opts){
  if(!hasVar(p))return p?.spec||"";
  const parts=[];if(v)parts.push(v.spec||v.label);
  for(const o of optsFor(p,v))if(opts?.[o.name])parts.push(opts[o.name]);
  if(p.spec)parts.push(p.spec);
  return parts.filter(Boolean).join("  ·  ");
}
const varPrice=(p,v)=>num(v?.price)||num(p?.price);
const sameOpts=(a,b)=>JSON.stringify(Object.entries(a||{}).filter(([,x])=>x).sort())===JSON.stringify(Object.entries(b||{}).filter(([,x])=>x).sort());
function itemFromProduct(p,qty,rate,vid,opts){
  const v=varOf(p,vid),o={};for(const op of optsFor(p,v))if(opts?.[op.name]&&op.values.includes(opts[op.name]))o[op.name]=opts[op.name];
  return{pid:p.id,vid:v?.id||"",opts:o,name:p.name,spec:composeSpec(p,v,o),warranty:p.warranty||"",img:p.img||"",unit:p.unit||"Pcs",qty:qty??1,qtyDel:qty??1,rate:rate??varPrice(p,v)};
}
/* change size / options on an existing line; the rate follows the size price unless it was edited by hand */
function setLineVariant(it,p,vid,opts){
  const oldV=varOf(p,it.vid),v=varOf(p,vid)??oldV;
  const keepRate=num(it.rate)&&num(it.rate)!==varPrice(p,oldV);
  const o={};for(const op of optsFor(p,v)){const val=opts&&op.name in opts?opts[op.name]:it.opts?.[op.name];if(val&&op.values.includes(val))o[op.name]=val}
  it.vid=v?.id||"";it.opts=o;it.spec=composeSpec(p,v,o);if(!keepRate&&v)it.rate=varPrice(p,v);
}
const lineLabel=it=>{const p=S.products.find(x=>x.id===it.pid),v=varOf(p,it.vid);return[it.name||"Item",v?.label,...Object.values(it.opts||{})].filter(Boolean).join(" · ")};
const escRe=x=>String(x).replace(/[.*+?^${}()|[\]\\]/g,"\\$&");
const normOrder=t=>String(t||"").toLowerCase().replace(/[’']/g,"").replace(/(\d)\s+(w|k|watt|watts)\b/g,"$1$2").replace(/(\d)\s*(?:deg|degree|degrees)\b/g,"$1°").replace(/\s+/g," ").trim();
const wordAt=(hay,al)=>{const m=new RegExp(`(^|[^a-z0-9°])${escRe(al)}(?=$|[^a-z0-9°])`).exec(hay);return m?{at:m.index+m[1].length,len:al.length}:null};
function variantAliases(v){const a=new Set(),L=String(v.label||"").toLowerCase().trim();
  if(L){a.add(L);a.add(L.replace(/\s+/g,""))}if(v.model)a.add(String(v.model).toLowerCase());
  const w=(String(`${v.label} ${v.spec||""}`).match(/(\d+(?:\.\d+)?)\s*w\b/i)||[])[1];if(w){a.add(w+"w");a.add(w+"watt")}
  return[...a].filter(x=>x.length>=2)}
function optionAliases(val){const v=String(val).toLowerCase().trim(),a=new Set([v,v.replace(/\s+/g,"")]);let m;
  if((m=v.match(/^(\d{4})\s*k$/))){const t=+m[1];a.add(m[1]+"k");
    if(t<=3500)["warm","warm white","ww","yellow"].forEach(x=>a.add(x));else if(t<=4500)["natural","neutral","natural white","nw","cool day"].forEach(x=>a.add(x));else["cool","cool white","daylight","day light","cw","white light"].forEach(x=>a.add(x))}
  if((m=v.match(/^(\d+)\s*°$/)))a.add(m[1]+"°");
  if(v==="white")a.add("wht");if(v==="black")a.add("blk");
  return[...a]}
/* which size / options a piece of text names for product p; spans are the matched character ranges */
function readVariant(p,seg){
  const out={v:null,opts:{},spans:[]};if(!p)return out;
  if(hasVar(p)){let best=null;for(const v of p.variants)for(const al of variantAliases(v)){const h=wordAt(seg,al);if(h&&(!best||h.len>best.len))best={v,...h}}
    if(best){out.v=best.v;out.spans.push([best.at,best.at+best.len])}}
  for(const o of optsFor(p,out.v||null).concat(out.v?[]:(p.options||[]).filter(o=>o.only?.length))){
    let best=null;for(const val of o.values)for(const al of optionAliases(val)){const h=wordAt(seg,al);if(h&&(!best||h.len>best.len))best={val,...h}}
    if(best){out.opts[o.name]=best.val;out.spans.push([best.at,best.at+best.len])}}
  /* colour words like "white light" can mean CCT or finish: if both hit the same words, keep the explicit one */
  return out;
}
'''

MATCHER = r'''/* ---------- built-in order reader (no AI): catalogue words + sizes + options + quantities + rates ---------- */
const GENERIC=new Set("led light lights series downlight downlights black white warm cool lamp model the and with for pcs pc set spot".split(" "));
function catIndex(){
  const tok=s=>String(s||"").toLowerCase().match(/[a-z][a-z0-9\-]{2,}/g)||[];
  const phrases=[],count=new Map();
  for(const p of S.products){
    const kws=String(p.keywords||"").toLowerCase().split(/[,;]+/).map(x=>x.trim()).filter(x=>x.length>1);
    if(p.model)kws.push(String(p.model).toLowerCase());
    for(const k of kws)phrases.push({p,text:k,w:3+k.length/20});
    for(const v of p.variants||[])if(v.model)phrases.push({p,text:String(v.model).toLowerCase(),w:4,vid:v.id});
    for(const t of new Set([...tok(p.name),...tok(p.keywords)]))count.set(t,(count.get(t)||0)+1);
  }
  for(const p of S.products)for(const t of new Set(tok(p.name)))if(count.get(t)===1&&!GENERIC.has(t)&&!STOP.has(t))phrases.push({p,text:t,w:2});
  return phrases;
}
function findMentions(lc){
  const out=[];
  for(const ph of catIndex()){const re=new RegExp(`(^|[^a-z0-9])(${escRe(ph.text)})(?=$|[^a-z0-9])`,"g");let m;
    while((m=re.exec(lc))){const start=m.index+m[1].length;out.push({p:ph.p,start,end:start+ph.text.length,w:ph.w,vid:ph.vid})}}
  out.sort((a,b)=>a.start-b.start||b.w-a.w);
  const kept=[];for(const m of out){const last=kept.at(-1);
    if(last&&m.start<last.end){if(m.w>last.w&&m.p!==last.p)kept[kept.length-1]=m;continue}
    if(last&&last.p===m.p&&!/\d/.test(lc.slice(last.end,m.start))){last.end=m.end;if(m.vid)last.vid=m.vid;continue}
    kept.push(m)}
  return kept;
}
/* returns {items:[{productId,variantId,options,description,qty,rate}], customer, ok} */
function localParse(text,d){
  const lc=normOrder(text);
  const ms=findMentions(lc);
  let blank=lc.split("");
  const wipe=(a,b)=>{for(let i=a;i<b&&i<blank.length;i++)blank[i]=" "};
  const info=ms.map((mt,i)=>{
    const lo=i?ms[i-1].end:0,hi=i<ms.length-1?ms[i+1].start:lc.length;
    /* the size/options for this product sit between the previous and next product mention */
    const seg=lc.slice(lo,hi).split("");for(let k=mt.start-lo;k<mt.end-lo;k++)seg[k]=" ";
    const r=readVariant(mt.p,seg.join(""));
    if(!r.v&&mt.vid)r.v=varOf(mt.p,mt.vid);
    for(const[a,b]of r.spans)wipe(lo+a,lo+b);
    wipe(mt.start,mt.end);
    return{mt,lo,hi,r};
  });
  const B=blank.join("");
  const nums=[];const re=/(?<![a-z0-9])(\d[\d,]*(?:\.\d+)?)(\s*(?:k|w|watt|watts|%|m|mtr|meter|meters|ft|pcs|pc|nos|x|°)\b|°)?/gi;let m;
  while((m=re.exec(B))){const unit=(m[2]||"").trim();if(/^(w|watt|watts|%|°)$/.test(unit))continue;
    let v=parseFloat(m[1].replace(/,/g,""));if(unit==="k")v*=1000;nums.push({v,at:m.index,end:m.index+m[0].length,unit,qtyish:/^(pcs|pc|nos|x)$/.test(unit)})}
  const items=[];let ok=true;
  if(ms.length){
    info.forEach(({mt,lo,hi,r},i)=>{
      const before=nums.filter(n=>n.end<=mt.start&&n.at>=lo&&!n.used),after=nums.filter(n=>n.at>=mt.end&&n.end<=hi&&!n.used);
      let qty=null,rate=null;
      const qb=before.at(-1);if(qb){qty=qb.v;qb.used=true}
      for(const n of after){if(n.used)continue;
        if(n.qtyish&&qty==null){qty=n.v;n.used=true;continue}
        if(rate==null&&(n.v>=100||qty!=null)){rate=n.v;n.used=true;continue}
        if(qty==null&&n.v<100){qty=n.v;n.used=true}}
      items.push({productId:mt.p.id,variantId:r.v?.id||null,options:r.opts,description:mt.p.name,qty,rate});
    });
  }else{
    const words=B.replace(/(?<![a-z])\d[\d,]*(?:\.\d+)?\s*(?:k|pcs|pc|nos|x)?\b/g," ").replace(/[^a-z0-9\s\-\/×.]/g," ").split(/\s+/).filter(w=>w&&!STOP.has(w));
    if(nums.length&&words.length){const q=nums.find(n=>n.v<100||n.qtyish)||null,r=nums.find(n=>n!==q&&n.v>=100)||null;
      items.push({productId:null,description:words.join(" ").replace(/\b\w/g,c=>c.toUpperCase()),qty:q?.v??null,rate:r?.v??null});ok=false}
  }
  let customer=null;
  const firstAt=Math.min(ms[0]?.start??Infinity,nums[0]?.at??Infinity);
  const lead=firstAt===Infinity?[]:lc.slice(0,firstAt).replace(/[^a-z\s.&']/g," ").split(/\s+/).filter(w=>w&&!STOP.has(w)&&!/^(mr|mrs|ms|sir|for|to)\.?$/.test(w));
  if(lead.length&&ms.length){
    const scored=S.customers.map(c=>{const hay=`${c.name} ${c.attn||""}`.toLowerCase();return{c,s:lead.filter(w=>w.length>2&&hay.includes(w)).length}}).filter(x=>x.s>0).sort((a,b)=>b.s-a.s);
    if(scored.length&&(scored.length===1||scored[0].s>scored[1].s))customer={id:scored[0].c.id};
    else customer={name:lead.join(" ").replace(/\b\w/g,c=>c.toUpperCase())};
  }
  return{items,customer,ok:ok&&items.length>0};
}
const shortKey=p=>String(p.keywords||"").split(/[,;]/)[0].trim()||String(p.name).split(/[\s–-]+/).filter(w=>w.length>2&&!GENERIC.has(w.toLowerCase())).slice(-2)[0]||p.name;
/* apply parsed lines (built-in reader or AI) to the document */
function applyParsed(res,d,done,asks){
  if(res.customer){
    const c=res.customer.id&&S.customers.find(x=>x.id===res.customer.id);
    if(c){if(d.customer.id!==c.id){d.customer={id:c.id,name:c.name||"",attn:c.attn||"",phone:c.phone||"",address:c.address||"",ntn:c.ntn||""};done.push(`Customer: ${c.name}`)}}
    else if(res.customer.name&&!d.customer.name){d.customer={...d.customer,id:"",name:String(res.customer.name),attn:String(res.customer.attn||"")};done.push(`Customer: ${d.customer.name}${d.customer.attn?" · "+d.customer.attn:""}`)}
  }
  for(const it of res.items||[]){
    const q0=it.qty==null?null:num(it.qty),q=q0>0?q0:null,rate=it.rate==null?null:num(it.rate);
    const p=it.productId&&S.products.find(x=>x.id===it.productId);
    if(!p){d.items.push({pid:"",vid:"",opts:{},name:String(it.description||"Item"),spec:"",warranty:"",img:"",unit:"Pcs",qty:q??1,qtyDel:q??1,rate:rate??0});
      asks.push(`Added “${it.description||"Item"}”, not in your catalogue. Check the name and rate.`);S.ed.lastItem=d.items.length-1;continue}
    const v=varOf(p,it.variantId);
    if(hasVar(p)&&!v){asks.push(`${p.name}: which size? ${p.variants.map(x=>x.label).join(" · ")}. Type e.g. “${q??10} ${shortKey(p)} ${p.variants[Math.min(1,p.variants.length-1)].label}${rate?" "+rate:""}”.`);continue}
    const opts={};for(const o of optsFor(p,v)){const val=it.options?.[o.name];if(val&&o.values.includes(val))opts[o.name]=val}
    const label=[p.name,v?.label,...Object.values(opts)].filter(Boolean).join(" · ");
    const ex=d.items.findIndex(x=>x.pid===p.id&&(x.vid||"")===(v?.id||"")&&sameOpts(x.opts,opts));
    if(ex>=0){const row=d.items[ex];if(q!=null){row.qty=q;row.qtyDel=q}if(rate!=null)row.rate=rate;S.ed.lastItem=ex;done.push(`Updated ${label}: ${fmt(row.qty)} × ${fmt(row.rate)}`);continue}
    const row=itemFromProduct(p,q??1,rate??null,v?.id,opts);d.items.push(row);S.ed.lastItem=d.items.length-1;
    done.push(`Added ${fmt(row.qty)} × ${label} @ ${fmt(row.rate)}${q==null?" (qty not given, set to 1)":""}`);
    const miss=optsFor(p,v).filter(o=>!opts[o.name]).map(o=>o.name);
    if(miss.length)asks.push(`${label}: ${miss.join(" and ")} not chosen. Pick below, or type e.g. “${shortKey(p)} ${v?.label||""} ${optsFor(p,v).filter(o=>!opts[o.name]).map(o=>o.values[0]).join(" ")}”.`.replace(/\s+”/,"”"));
    if(!num(row.rate)&&d.type!=="DN")asks.push(`${label}: no price set. Type “${shortKey(p)} ${v?.label||""} rate 1450” or add the price in Products.`.replace(/\s+rate/," rate"));
  }
}
'''

# 1) variants helpers replace old itemFromProduct
RX(r'function itemFromProduct\(p,qty,rate\)\{return\{pid:p\.id,name:p\.name,spec:p\.spec\|\|"",warranty:p\.warranty\|\|"",img:p\.img\|\|"",unit:p\.unit\|\|"Pcs",qty:qty\?\?1,qtyDel:qty\?\?1,rate:rate\?\?num\(p\.price\)\}\}\n', VARIANTS)

# 2) matcher after setTotal / CMD_HELP area: put before cmdLogHTML
R('function cmdLogHTML(){', MATCHER + 'function cmdLogHTML(){')

# 3) order key for deliveries counts sizes/options separately
R('const itemKey=it=>it.pid||String(it.name||"").trim().toLowerCase();',
  'const itemKey=it=>it.pid?`${it.pid}|${it.vid||""}|${JSON.stringify(Object.entries(it.opts||{}).filter(([,x])=>x).sort())}`:String(it.name||"").trim().toLowerCase();')

# 4) editor line: size + option pickers
R('''    <input data-f="items.${i}.name" value="${esc(it.name)}" placeholder="Description" aria-label="Description">''',
  '''    ${variantPickers(it,i)}
    <input data-f="items.${i}.name" value="${esc(it.name)}" placeholder="Description" aria-label="Description">''')
R('function itemsHTML(d){', '''function variantPickers(it,i){const p=S.products.find(x=>x.id===it.pid);if(!hasVar(p))return"";const v=varOf(p,it.vid);
  return `<div class="vpick"><label class="f">Size<select data-act="vsel" data-i="${i}" class="${v?"":"need"}"><option value="">Choose size…</option>${p.variants.map(x=>`<option value="${esc(x.id)}" ${x.id===it.vid?"selected":""}>${esc(x.label)}${num(x.price)?" · "+fmt(x.price):""}</option>`).join("")}</select></label>
   ${optsFor(p,v).map(o=>`<label class="f">${esc(o.name)}<select data-act="osel" data-i="${i}" data-o="${esc(o.name)}" class="${it.opts?.[o.name]?"":"need"}"><option value="">Choose…</option>${o.values.map(val=>`<option ${it.opts?.[o.name]===val?"selected":""}>${esc(val)}</option>`).join("")}</select></label>`).join("")}</div>`}
function itemsHTML(d){''')
R('''function prodOptions(sel){return `<option value="">Custom item</option>`+S.products.map(p=>`<option value="${p.id}" ${p.id===sel?"selected":""}>${esc(p.name)}${p.spec?" — "+esc(p.spec.split("·")[0].trim()):""}</option>`).join("")}''',
  '''function prodOptions(sel){return `<option value="">Custom item</option>`+S.products.map(p=>`<option value="${p.id}" ${p.id===sel?"selected":""}>${esc(p.name)}${hasVar(p)?` — ${p.variants.length} sizes`:p.spec?" — "+esc(p.spec.split("·")[0].trim()):""}</option>`).join("")}''')
# change handlers for pickers
R('''  if(t.dataset.act==="pick"&&S.ed){S.ed.dirty=true;''', '''  if((t.dataset.act==="vsel"||t.dataset.act==="osel")&&S.ed){S.ed.dirty=true;const i=+t.dataset.i,it=S.ed.doc.items[i],p=S.products.find(x=>x.id===it.pid);if(!p)return;
    if(t.dataset.act==="vsel")setLineVariant(it,p,t.value,null);else setLineVariant(it,p,it.vid,{[t.dataset.o]:t.value});
    S.ed.lastItem=i;$("#items").innerHTML=itemsHTML(S.ed.doc);updatePreview();return}
  if(t.dataset.act==="pick"&&S.ed){S.ed.dirty=true;''')

# 5) catalogue card + form
R('''   <div class="spread pr"><span>PKR ${fmt(p.price)} / ${esc(p.unit||"Pcs")}</span><button class="btn sm" data-act="editprod" data-id="${p.id}">Edit</button></div></div></div>`).join("")}</div>`''',
  '''   ${hasVar(p)?`<div class="vchips">${p.variants.map(v=>`<span>${esc(v.label)}</span>`).join("")}</div>${(p.options||[]).filter(o=>o.values?.length).map(o=>`<div class="sp">${esc(o.name)}: ${esc(o.values.join(", "))}${o.only?.length?` <i>(${esc(o.only.join(", "))} only)</i>`:""}</div>`).join("")}`:""}
   <div class="spread pr"><span>${hasVar(p)?(()=>{const ps=p.variants.map(v=>varPrice(p,v)).filter(Boolean);return ps.length?`From PKR ${fmt(Math.min(...ps))}`:`<span class="q low">Prices not set</span>`})():`PKR ${fmt(p.price)}`} / ${esc(p.unit||"Pcs")}</span><button class="btn sm" data-act="editprod" data-id="${p.id}">Edit</button></div></div></div>`).join("")}</div>`''')
R('''   <div class="g2"><label class="f">Model / code<input data-pf="model" value="${esc(p.model)}"></label><label class="f">Shorthand words<input data-pf="keywords" value="${esc(p.keywords)}" placeholder="trail, step"></label></div>''',
  '''   <div class="g2"><label class="f">Model / code<input data-pf="model" value="${esc(p.model)}"></label><label class="f">Shorthand words<input data-pf="keywords" value="${esc(p.keywords)}" placeholder="trail, step"></label></div>
   <div class="vsect"><div class="spread"><h3>Sizes</h3><button class="btn sm" data-act="addvar">Add size</button></div>
     <div class="muted hint">For a range like 5W / 7W / 12W. Each size has its own price, code and spec line. Leave empty for a single-size product.${(p.variants||[]).length?" The price above is used only for sizes with no price.":""}</div>
     ${(p.variants||[]).map((v,i)=>`<div class="vrow"><input data-vf="${i}.label" value="${esc(v.label)}" placeholder="Size · 12W" aria-label="Size name"><input data-vf="${i}.price" inputmode="decimal" value="${esc(v.price)}" placeholder="Price" aria-label="Price"><input data-vf="${i}.model" value="${esc(v.model)}" placeholder="Code" aria-label="Code"><button class="btn sm ghost danger" data-act="rmvar" data-i="${i}" aria-label="Remove size">✕</button><input class="vspec" data-vf="${i}.spec" value="${esc(v.spec)}" placeholder="Spec line · 12W · 1080 lm · Cut-out Φ90-100" aria-label="Spec line"></div>`).join("")}</div>
   <div class="vsect"><div class="spread"><h3>Options chosen per order</h3><button class="btn sm" data-act="addopt">Add option</button></div>
     <div class="muted hint">e.g. CCT: 3000K, 4000K, 6000K · Finish: White, Black. Leave “only for sizes” empty if every size has it.</div>
     ${(p.options||[]).map((o,i)=>`<div class="orow"><input data-of="${i}.name" value="${esc(o.name)}" placeholder="Option · CCT" aria-label="Option name"><input data-of="${i}.values" value="${esc(o.values)}" placeholder="Choices · 3000K, 4000K, 6000K" aria-label="Choices"><input data-of="${i}.only" value="${esc(o.only)}" placeholder="Only for sizes (optional) · 5W, 7W" aria-label="Only for sizes"><button class="btn sm ghost danger" data-act="rmopt" data-i="${i}" aria-label="Remove option">✕</button></div>`).join("")}</div>''')
# form state: options are edited as text
R('''    case"editprod":S.pform=clone(S.products.find(p=>p.id===id));''',
  '''    case"editprod":S.pform=clone(S.products.find(p=>p.id===id));S.pform.variants=S.pform.variants||[];S.pform.options=(S.pform.options||[]).map(o=>({name:o.name||"",values:(o.values||[]).join(", "),only:(o.only||[]).join(", ")}));''')
R('''S.pform={id:"",name:"",spec:"",warranty:"",price:"",unit:"Pcs",model:"",keywords:"",img:""};''',
  '''S.pform={id:"",name:"",spec:"",warranty:"",price:"",unit:"Pcs",model:"",keywords:"",img:"",variants:[],options:[]};''')
R('''    case"cancelprod":''', '''    case"addvar":S.pform.variants.push({id:uid("v"),label:"",price:"",model:"",spec:""});renderPForm();document.querySelector(`[data-vf="${S.pform.variants.length-1}.label"]`)?.focus();break;
    case"rmvar":S.pform.variants.splice(+b.dataset.i,1);renderPForm();break;
    case"addopt":S.pform.options.push({name:"",values:"",only:""});renderPForm();document.querySelector(`[data-of="${S.pform.options.length-1}.name"]`)?.focus();break;
    case"rmopt":S.pform.options.splice(+b.dataset.i,1);renderPForm();break;
    case"cancelprod":''')
R('''      await put("products",pid,{name:p.name.trim(),spec:p.spec||"",warranty:(p.warranty||"").trim(),price:num(p.price),unit:p.unit||"Pcs",model:p.model||"",keywords:p.keywords||"",img:p.img||""});''',
  '''      const list=x=>String(x||"").split(",").map(y=>y.trim()).filter(Boolean);
      const variants=(p.variants||[]).filter(v=>String(v.label||"").trim()).map(v=>({id:v.id||uid("v"),label:String(v.label).trim(),price:num(v.price),model:String(v.model||"").trim(),spec:String(v.spec||"").trim()}));
      const options=(p.options||[]).filter(o=>String(o.name||"").trim()&&list(o.values).length).map(o=>({name:String(o.name).trim(),values:list(o.values),only:list(o.only)}));
      await put("products",pid,{name:p.name.trim(),spec:p.spec||"",warranty:(p.warranty||"").trim(),price:num(p.price),unit:p.unit||"Pcs",model:p.model||"",keywords:p.keywords||"",img:p.img||"",variants,options});''')
R('''  if(t.dataset.pf&&S.pform){S.pform[t.dataset.pf]=t.value;return}''',
  '''  if(t.dataset.pf&&S.pform){S.pform[t.dataset.pf]=t.value;return}
  if(t.dataset.vf&&S.pform){const[i,k]=t.dataset.vf.split(".");S.pform.variants[+i][k]=t.value;return}
  if(t.dataset.of&&S.pform){const[i,k]=t.dataset.of.split(".");S.pform.options[+i][k]=t.value;return}''')

# 6) commands: variant-aware targeting + change size/option
RX(r'/\* which line items a clause refers to: \[\] = none named; null = ambiguous \*/\nfunction itemsIn\(c,d\)\{.*?\n\}\nconst targetItems=\(c,d\)=>\{.*?return null\};\n', r'''/* which line items a clause refers to: [] = none named; null = ambiguous.
   A line whose size or options contradict the clause ("tulip 9w" vs a 12W line) doesn't count, unless loose is set. */
function lineConflicts(it,lc){const p=S.products.find(x=>x.id===it.pid);if(!hasVar(p)&&!(p?.options||[]).length)return false;
  const r=readVariant(p,lc);if(r.v&&it.vid&&r.v.id!==it.vid)return true;
  for(const[k,v]of Object.entries(r.opts))if(it.opts?.[k]&&it.opts[k]!==v)return true;return false}
function itemsIn(c,d,loose){
  const n=d.items.length,lc=normOrder(c);let m;
  if(!n)return[];
  if(/\b(all|every|everything|each item|all items)\b/.test(lc))return d.items.map((_,i)=>i);
  if((m=lc.match(/\b(?:item|line|no\.?)\s*#?(\d+)\b|#(\d+)\b/))){const i=+(m[1]||m[2])-1;return i>=0&&i<n?[i]:null}
  for(const[w,i]of Object.entries(ORD))if(new RegExp(`\\b${w}\\b`).test(lc))return i<n?[i]:null;
  if(/\blast\b/.test(lc))return[n-1];
  const toks=lc.match(/\b\d+(?:\.\d+)?(?:w|k)\b|[a-z][a-z0-9\-]{2,}/g)?.filter(t=>!STOP.has(t))||[];
  const scores=d.items.map(it=>{const p=S.products.find(x=>x.id===it.pid),v=varOf(p,it.vid);
    const hay=normOrder(`${it.name} ${it.spec||""} ${p?.keywords||""} ${p?.model||""} ${v?.label||""} ${v?.model||""} ${Object.values(it.opts||{}).join(" ")}`);
    if(!loose&&lineConflicts(it,lc))return -100;
    return toks.reduce((a,t)=>a+(new RegExp(`(^|[^a-z0-9])${escRe(t)}(?=$|[^a-z0-9])`).test(hay)?1:0),0)});
  const best=Math.max(...scores);
  if(best>0){const hits=scores.map((s,i)=>s===best?i:-1).filter(i=>i>=0);return hits.length===1?hits:null}
  return[];
}
/* null = ambiguous, [] = names a product that isn't on this document, else the line indexes */
const targetItems=(c,d,loose)=>{const r=itemsIn(c,d,loose);if(r===null)return null;if(r.length)return r;
  if(findMentions(normOrder(c)).length)return[];
  if(d.items.length===1)return[0];if(S.ed.lastItem!=null&&S.ed.lastItem<d.items.length&&/\b(this|it|that|same)\b/i.test(c))return[S.ed.lastItem];return null};
const NOTON="That item isn't on this document yet. Add it first, e.g. “10 tulip 12w 1450”.";
const pickOr=ti=>!ti?{ask:ASK}:!ti.length?{ask:NOTON}:null;
''')
R('let CURD=null;const nm=i=>CURD.items[i].name||`Item ${i+1}`;', 'let CURD=null;const nm=i=>lineLabel(CURD.items[i])||`Item ${i+1}`;')
# guard callers that used "if(!ti)return{ask:ASK}"
R('''    if(perUnit&&d.items.length){const ti=targetItems(lc,d);if(!ti)return{ask:ASK};''', '''    if(perUnit&&d.items.length){const ti=targetItems(lc,d);if(pickOr(ti))return pickOr(ti);''')
R('''  if(/\\bwarrant(y|ee)\\b|\\bguarantee\\b/.test(lc)){const ti=targetItems(lc.replace(/\\b\\d+\\s*(year|yr|month|mo)s?\\b/g,""),d);if(!ti)return{ask:ASK};''',
  '''  if(/\\bwarrant(y|ee)\\b|\\bguarantee\\b/.test(lc)){const ti=targetItems(lc.replace(/\\b\\d+\\s*(year|yr|month|mo)s?\\b/g,""),d);if(pickOr(ti))return pickOr(ti);''')
R('''const ti=targetItems(m[1]||"this",d);if(!ti)return{ask:ASK};ti.forEach(i=>d.items[i].spec=m[2].trim())''', '''const ti=targetItems(m[1]||"this",d);if(pickOr(ti))return pickOr(ti);ti.forEach(i=>d.items[i].spec=m[2].trim())''')
R('''const ti=targetItems(m[1],d);if(!ti)return{ask:ASK};const was=nm(ti[0])''', '''const ti=targetItems(m[1],d);if(pickOr(ti))return pickOr(ti);const was=nm(ti[0])''')
R('''const ti=targetItems(lc.replace(/\\bunit\\b.*$/,""),d)||targetItems(lc,d);if(!ti)return{ask:ASK};''', '''const ti=targetItems(lc.replace(/\\bunit\\b.*$/,""),d)||targetItems(lc,d);if(pickOr(ti))return pickOr(ti);''')
R('''const ti=targetItems(lc,d);if(!ti)return{ask:ASK};
    if(/\\b(all|full|everything)\\b/.test(lc))''', '''const ti=targetItems(lc,d);if(pickOr(ti))return pickOr(ti);
    if(/\\b(all|full|everything)\\b/.test(lc))''')
R('''    const ti=targetItems(lc.replace(/\\b\\d+\\s+more\\b/,"more"),d);if(!ti)return d.items.length?{ask:ASK}:null;''',
  '''    const ti=targetItems(lc.replace(/\\b\\d+\\s+more\\b/,"more"),d);if(ti&&!ti.length)return null;if(!ti)return d.items.length?{ask:ASK}:null;''')
R('''  if(!dn&&(isPrice||(isDelta&&/\\bby\\b/.test(lc)))&&d.items.length){
    const ti=targetItems(lc,d);if(!ti)return{ask:ASK};''', '''  if(!dn&&(isPrice||(isDelta&&/\\bby\\b/.test(lc)))&&d.items.length){
    const ti=targetItems(lc,d);if(pickOr(ti))return pickOr(ti);''')
# change size / option command, before the generic item edits
R('''  /* item edits */''', r'''  /* change size / option on a line: "change tulip 12w to 9w", "make tulip black", "tulip 12w cct 3000k" */
  {const lcn=normOrder(c),hasTo=/\s(?:to|into)\s/.test(lcn),verb=/\b(change|make|set|switch|turn|swap)\b|\b(cct|colou?r|finish|beam|size|watt|wattage)\b/.test(lcn);
   const varLines=d.items.map((it,i)=>[it,i]).filter(([it])=>{const p=S.products.find(x=>x.id===it.pid);return hasVar(p)||(p?.options||[]).length});
   if(varLines.length&&(verb||hasTo)&&!/\b(price|rate|qty|quantity|pcs|discount|warranty)\b/.test(lcn)&&!/\d{3,}(?!\s*(?:k|w)\b)/.test(lcn.replace(/\b\d{4}k\b/g,""))){
     const cut=hasTo?lcn.lastIndexOf(" to ")>=0?lcn.lastIndexOf(" to "):lcn.lastIndexOf(" into "):-1;
     const before=cut>=0?lcn.slice(0,cut):lcn,afterTxt=cut>=0?lcn.slice(cut).replace(/^\s*(to|into)\s/,""):lcn;
     const ti=targetItems(before,d,cut<0);
     if(ti&&ti.length){
       const msgs=[];
       for(const i of ti){const it=d.items[i],p=S.products.find(x=>x.id===it.pid);if(!p)continue;
         const r=readVariant(p,afterTxt);if(!r.v&&!Object.keys(r.opts).length)continue;
         const was=lineLabel(it);setLineVariant(it,p,r.v?.id??it.vid,r.opts);msgs.push(`${was} → ${lineLabel(it)}`);S.ed.lastItem=i}
       if(msgs.length)return msgs.join(", ");
     }else if(ti===null&&verb)return{ask:ASK};
   }}
  /* item edits */''')

# 7) AI prompt knows sizes/options; local-first runAI for every build
RX(r'async function aiItems\(txt,d\)\{.*?\n\}\nasync function runAI\(\)\{.*?\n\}\n', r'''const AIX={ready:()=>!!SAMPLE,json:p=>SAMPLE.json(p,{modelTier:"default"})};
async function aiItems(clauses,d){
  const done=[],asks=[];
  const cat=S.products.map(p=>({id:p.id,name:p.name,specs:p.spec||"",model:p.model||"",keywords:p.keywords||"",price:num(p.price),unit:p.unit||"Pcs",
    ...(hasVar(p)?{sizes:p.variants.map(v=>({id:v.id,label:v.label,model:v.model||"",spec:v.spec||""}))}:{}),
    ...((p.options||[]).length?{options:p.options.map(o=>({name:o.name,values:o.values,onlyForSizes:o.only||[]}))}:{})}));
  const cus=S.customers.map(c=>({id:c.id,name:c.name,attn:c.attn||""}));
  const prompt=`You turn shorthand order notes from a lighting company in Multan, Pakistan into structured data. Do not do any arithmetic or totals.
CATALOGUE (JSON): ${JSON.stringify(cat)}
SAVED CUSTOMERS (JSON): ${JSON.stringify(cus)}
ORDER TEXT: """${clauses.join(", ")}"""
Rules:
- Match each product mention to a catalogue id by series name, keyword, wattage, model or description. Use null productId only if nothing in the catalogue fits; then give a clean description.
- If the product has "sizes", return the matching size id as sizeId (by wattage, label or model code), or null if no size is written. Never guess a size.
- If the product has "options", return the chosen values in "options" using the exact option names and values listed (e.g. "warm" = 3000K, "cool white"/"daylight" = 6000K). Leave out options that aren't written.
- A small number right before a product is the quantity. A larger number (usually 3+ digits) after a product is the unit rate in PKR. Wattage (e.g. 12w) and colour temperature (e.g. 4000k) are not quantities or rates. If no rate is written, rate is null. If no quantity is written, qty is null.
- If the text names a person and/or business, match a saved customer (fuzzy) and return its customerId; otherwise newCustomer with a Title Case company name and attn like "Mr. Mashood". If no customer is mentioned, both are null.
Reply with JSON only, exactly this shape:
{"customerId": string|null, "newCustomer": {"name": string, "attn": string}|null, "items": [{"productId": string|null, "sizeId": string|null, "options": {"<option name>": "<value>"}, "description": string, "qty": number|null, "rate": number|null}]}`;
  try{
    const r=await AIX.json(prompt);
    if(!r||typeof r!=="object")throw new Error("The AI reply couldn't be read.");
    applyParsed({customer:r.customerId?{id:r.customerId}:r.newCustomer?.name?{name:r.newCustomer.name,attn:r.newCustomer.attn}:null,
      items:(Array.isArray(r.items)?r.items:[]).map(x=>({...x,variantId:x.sizeId||null,options:x.options||{}}))},d,done,asks);
    if(!done.length&&!asks.length)asks.push("No items found in that text.");
  }catch(e){
    asks.push((e?.code==="rate_limited"?"AI is busy.":e?.message||"AI request failed.")+" Used built-in matching instead.");
    for(const cl of clauses)applyParsed(localParse(cl,d),d,done,asks);
  }
  return{done,asks};
}
async function runAI(){
  const box=$("#aiText"),txt=box.value.trim();S.ed.aiText=txt;if(!txt)return;
  const d=S.ed.doc,snap=clone(d);S.ed.after=null;
  const done=[],asks=[],rest=[];let help=false;
  for(const cl of splitClauses(txt)){let r;try{r=runCommand(cl,d)}catch(e){console.error(e);r=null}
    if(r===null)rest.push(cl);else if(r?.help)help=true;else if(r?.ask)asks.push(`“${cl}”: ${r.ask}`);else if(r)done.push(r)}
  const itemClauses=rest.filter(c=>looksLikeItems(c,d));
  rest.filter(c=>!itemClauses.includes(c)).forEach(c=>asks.push(`Didn't understand “${c}”. Tap “What can I type?” for examples.`));
  const forAI=[];
  for(const cl of itemClauses){const r=localParse(cl,d);
    if(!r.items.length){asks.push(`Didn't understand “${cl}”. Try “45 trail 4850”.`);continue}
    if(r.ok||!AIX.ready())applyParsed(r,d,done,asks);else forAI.push(cl)}
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
R('''const looksLikeItems=(c,d)=>/\\d/.test(c)&&(S.products.some(p=>`${p.name} ${p.keywords||""} ${p.model||""}`''',
  '''const looksLikeItems=(c,d)=>/\\d/.test(c)&&(S.products.some(p=>`${p.name} ${p.keywords||""} ${p.model||""} ${(p.variants||[]).map(v=>v.model||"").join(" ")}`''')

# 8) wording + help
R('Edits are done instantly on your device; only new items use AI. Totals are always computed here.',
  'New items are matched to your catalogue on your device, sizes and options included; AI is only used for lines it can\'t place. Totals are always computed here.')
R('<b>New items</b> (uses AI): “45 trail 4850, 20 convex”<br>',
  '<b>New items</b>: “45 trail 4850, 20 convex” · sizes &amp; options: “20 tulip 12w 4000k black 1450”<br><b>Sizes &amp; options</b>: “change tulip 12w to 9w” · “make tulip black” · “tulip 12w cct warm”<br>')

# 9) import products (Settings)
R('''    <div class="card stack"><h2>Numbering ${y}</h2>''', '''    <div class="card stack"><h2>Import products</h2>
      <div class="muted" style="font-size:13px">Load a product file (.json) prepared for you. Products with the same ID are updated; everything else is kept.</div>
      <div class="row"><label class="btn">Choose product file<input type="file" accept="application/json,.json" id="importProducts" hidden></label><span id="importMsg" class="muted" style="font-size:13px"></span></div></div>
    <div class="card stack"><h2>Numbering ${y}</h2>''')
R('''  if(t.id==="logoFile"&&t.files[0]){uploadLogo(t.files[0]);return}''', '''  if(t.id==="logoFile"&&t.files[0]){uploadLogo(t.files[0]);return}
  if(t.id==="importProducts"&&t.files[0]){const msg=$("#importMsg");msg.textContent="Importing…";
    try{const j=JSON.parse(await t.files[0].text());const list=Array.isArray(j)?j:Array.isArray(j.products)?j.products:[];if(!list.length)throw new Error("No products found in that file.");
      let n=0;for(const p of list){if(!p||!p.name)continue;const rec={...p};const id=String(rec.id||uid("p"));delete rec.id;
        if(typeof rec.img==="string"&&rec.img.startsWith("data:")){try{rec.img=await storeImage(await (await fetch(rec.img)).blob())}catch{rec.img=""}}
        const old=S.products.find(x=>x.id===id);if(old?.img&&!rec.img)rec.img=old.img;
        await put("products",id,{spec:"",warranty:"",price:0,unit:"Pcs",model:"",keywords:"",img:"",variants:[],options:[],...rec});n++}
      msg.textContent=`Imported ${n} product${n===1?"":"s"}.`;toast(`Imported ${n} product${n===1?"":"s"}`)}
    catch(e){msg.textContent=e.message&&!/JSON/.test(e.message)?e.message:"That file isn't a product file."}t.value="";return}''')

# 10) styles
R('/* orders */', '''.vpick{display:grid;grid-template-columns:repeat(auto-fit,minmax(104px,1fr));gap:8px}
select.need{border-color:#d9a13b;background:color-mix(in srgb,#d9a13b 8%,var(--surface))}
.vsect{display:flex;flex-direction:column;gap:8px;border-top:1px solid var(--line);padding-top:12px}
.vsect h3{font-size:14px;margin:0}.vsect .hint{font-size:12px}
.vrow{display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1fr) minmax(0,1.2fr) auto;gap:6px;align-items:center}
.vrow .vspec{grid-column:1/-1;margin-bottom:4px}
.orow{display:grid;grid-template-columns:minmax(0,.8fr) minmax(0,1.6fr) minmax(0,1.1fr) auto;gap:6px;align-items:center}
@media (max-width:520px){.orow{grid-template-columns:minmax(0,1fr) auto}.orow input:nth-child(2),.orow input:nth-child(3){grid-column:1/-1}.orow button{grid-row:1;grid-column:2}}
.vchips{display:flex;flex-wrap:wrap;gap:4px;margin-top:4px}.vchips span{font-size:11px;font-weight:700;border:1px solid var(--line);border-radius:99px;padding:1px 7px;color:var(--muted)}
.pcard .sp i{font-style:normal;opacity:.75}
/* orders */''')

open(P, "w", encoding="utf-8").write(s)
print("patched", P)
