#!/usr/bin/env python3
"""One-off patch: private cost prices, per-line and per-document margin, below-cost warnings."""
import os
P = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src", "app.src.html")
s = open(P, encoding="utf-8").read()
def R(a, b, cnt=1):
    global s
    n = s.count(a); assert n == cnt, f"expected {cnt}, found {n}: {a[:110]!r}"; s = s.replace(a, b)

# helpers + snapshot cost on new lines
R('function itemFromProduct(p,qty,rate,vid,opts){', '''/* cost price (private): per size if set, else the product's; lines keep the cost from the day they were added */
const varCost=(p,v)=>num(v?.cost)||num(p?.cost);
function lineCost(it){if(it.cost!=null&&it.cost!=="")return num(it.cost);const p=it.pid&&S.products.find(x=>x.id===it.pid);return p?varCost(p,varOf(p,it.vid)):0}
const costsOn=()=>S.settings?.showCosts!==false;
function margins(d){
  const t=calc(d),net=t.sub-t.disc;let cost=0,known=true;const lines=d.items.map(it=>{const c=lineCost(it),q=num(it.qty),r=num(it.rate);if(!c)known=false;cost+=c*q;
    return{c,profit:(r-c)*q,pct:r?Math.round((r-c)/r*1000)/10:0,below:c>0&&r<c}});
  const profit=net-cost;return{lines,cost,net,profit,pct:net?Math.round(profit/net*1000)/10:0,known,anyBelow:lines.some(l=>l.below)};
}
const pctTxt=x=>`${x>0?"+":""}${x}%`;
function itemFromProduct(p,qty,rate,vid,opts){''')
R('''  return{pid:p.id,vid:v?.id||"",opts:o,name:p.name,spec:composeSpec(p,v,o),warranty:p.warranty||"",img:p.img||"",unit:p.unit||"Pcs",qty:qty??1,qtyDel:qty??1,rate:rate??varPrice(p,v)};''',
  '''  return{pid:p.id,vid:v?.id||"",opts:o,name:p.name,spec:composeSpec(p,v,o),warranty:p.warranty||"",img:p.img||"",unit:p.unit||"Pcs",qty:qty??1,qtyDel:qty??1,rate:rate??varPrice(p,v),cost:varCost(p,v)};''')
R('''  it.vid=v?.id||"";it.opts=o;it.spec=composeSpec(p,v,o);if(!keepRate&&v)it.rate=varPrice(p,v);''',
  '''  it.vid=v?.id||"";it.opts=o;it.spec=composeSpec(p,v,o);if(!keepRate&&v)it.rate=varPrice(p,v);if(v)it.cost=varCost(p,v);''')
R('''  if(t.dataset.act==="pick"&&S.ed){S.ed.dirty=true;''', '''  if(t.dataset.act==="pick"&&S.ed){S.ed.dirty=true;S.ed.doc.items[+t.dataset.i].cost=null;''')

# editor: margin under each line + private panel in totals
R('''    <div class="amtline">Amount <b data-amt="${i}">PKR ${fmt(lineAmt(it))}</b></div>`}</div>`).join("");''',
  '''    <div class="amtline">${costsOn()?`<span class="mline" data-mg="${i}">${marginLine(d,i)}</span>`:""}Amount <b data-amt="${i}">PKR ${fmt(lineAmt(it))}</b></div>`}</div>`).join("");''')
R('function itemsHTML(d){', '''function marginLine(d,i){const it=d.items[i],c=lineCost(it);if(!c)return`<span class="muted">No cost set</span>`;
  const r=num(it.rate),pr=(r-c)*num(it.qty),pct=r?Math.round((r-c)/r*1000)/10:0;
  return`<span class="${r<c?"neg":""}">Cost ${fmt(c)} · ${r<c?"Loss":"Profit"} ${fmt(Math.abs(pr))} (${pctTxt(pct)})</span>`}
function itemsHTML(d){''')
R('''  const tt=$("#totals");if(tt&&d.type!=="DN"){const t=calc(d);tt.innerHTML=`''',
  '''  if(costsOn()&&d.type!=="DN"){const mp=$("#marginPanel");if(mp)mp.innerHTML=marginPanel(d);d.items.forEach((_,i)=>{const el=document.querySelector(`[data-mg="${i}"]`);if(el)el.innerHTML=marginLine(d,i)})}
  const tt=$("#totals");if(tt&&d.type!=="DN"){const t=calc(d);tt.innerHTML=`''')
R('function updatePreview(){', '''function marginPanel(d){const m=margins(d);if(!d.items.length)return"";
  return `<div class="mhead"><b>Your margin</b><span class="muted">Private · never on the PDF</span></div>
  <div class="mgrid"><span>Sale value (after discount)</span><b>PKR ${fmt(m.net)}</b><span>Cost</span><b>PKR ${fmt(m.cost)}</b>
  <span class="${m.profit<0?"neg":"pos"}">${m.profit<0?"Loss":"Profit"}</span><b class="${m.profit<0?"neg":"pos"}">PKR ${fmt(Math.abs(m.profit))} · ${pctTxt(m.pct)}</b></div>
  ${m.anyBelow?`<div class="mwarn">Below cost: ${m.lines.map((l,i)=>l.below?`item ${i+1}`:null).filter(Boolean).join(", ")}</div>`:""}
  ${m.known?"":`<div class="muted" style="font-size:12px">Some items have no cost price; add it in Products for an exact figure.</div>`}`}
function updatePreview(){''')
R('''        <div class="totals" id="totals"></div>''', '''        <div class="totals" id="totals"></div>
        ${costsOn()?`<div class="mpanel" id="marginPanel"></div>`:""}''')

# product form: cost next to price, cost per size, live margin; card shows margin
R('''   <div class="g2 keep"><label class="f">Price (PKR)<input data-pf="price" inputmode="decimal" value="${esc(p.price)}"></label><label class="f">Unit<input data-pf="unit" value="${esc(p.unit||"Pcs")}"></label></div>''',
  '''   <div class="g3"><label class="f">Sale price (PKR)<input data-pf="price" inputmode="decimal" value="${esc(p.price)}"></label><label class="f">Cost price<input data-pf="cost" inputmode="decimal" value="${esc(p.cost??"")}" placeholder="Private"></label><label class="f">Unit<input data-pf="unit" value="${esc(p.unit||"Pcs")}"></label></div>
   <div class="row" style="gap:8px;font-size:12px"><span class="muted">Fill cost from sale price minus</span><input id="costPct" inputmode="decimal" value="${esc(p.supplierDisc??30)}" style="width:60px;padding:4px 8px" aria-label="Supplier discount percent"><span class="muted">%</span><button class="btn sm" data-act="costfill">Fill costs</button><span class="muted" id="pmargin">${formMargin(p)}</span></div>''')
R('function renderPForm(){', '''function formMargin(p){const rows=hasVar(p)?(p.variants||[]).map(v=>[num(v.price)||num(p.price),num(v.cost)||num(p.cost)]):[[num(p.price),num(p.cost)]];
  const ok=rows.filter(([pr,c])=>pr&&c);if(!ok.length)return"";const pc=ok.map(([pr,c])=>(pr-c)/pr*100);const lo=Math.round(Math.min(...pc)*10)/10,hi=Math.round(Math.max(...pc)*10)/10;
  return `Margin ${lo===hi?pctTxt(lo):pctTxt(lo)+" to "+pctTxt(hi)}`}
function renderPForm(){''')
R('''<input data-vf="${i}.price" inputmode="decimal" value="${esc(v.price)}" placeholder="Price" aria-label="Price">''',
  '''<input data-vf="${i}.price" inputmode="decimal" value="${esc(v.price)}" placeholder="Price" aria-label="Price"><input data-vf="${i}.cost" inputmode="decimal" value="${esc(v.cost??"")}" placeholder="Cost" aria-label="Cost price">''')
R('''      const variants=(p.variants||[]).filter(v=>String(v.label||"").trim()).map(v=>({id:v.id||uid("v"),label:String(v.label).trim(),price:num(v.price),model:String(v.model||"").trim(),spec:String(v.spec||"").trim()}));''',
  '''      const variants=(p.variants||[]).filter(v=>String(v.label||"").trim()).map(v=>({id:v.id||uid("v"),label:String(v.label).trim(),price:num(v.price),cost:num(v.cost),model:String(v.model||"").trim(),spec:String(v.spec||"").trim()}));''')
R('''price:num(p.price),unit:p.unit||"Pcs",model:p.model||"",keywords:p.keywords||"",img:p.img||"",variants,options});S.pform=null;''',
  '''price:num(p.price),cost:num(p.cost),supplier:p.supplier||"",supplierDisc:p.supplierDisc??"",unit:p.unit||"Pcs",model:p.model||"",keywords:p.keywords||"",img:p.img||"",variants,options});S.pform=null;''')
R('''    case"cancelprod":''', '''    case"costfill":{const p=S.pform;if(!p)break;const k=num($("#costPct").value);if(!(k>=0&&k<100)){toast("Enter a discount between 0 and 99%");break}
      p.supplierDisc=k;if(num(p.price))p.cost=Math.round(num(p.price)*(1-k/100));(p.variants||[]).forEach(v=>{const pr=num(v.price)||num(p.price);if(pr)v.cost=Math.round(pr*(1-k/100))});
      renderPForm();toast(`Costs filled at ${k}% below sale price`);break}
    case"cancelprod":''')
R('''  if(t.dataset.vf&&S.pform){const[i,k]=t.dataset.vf.split(".");S.pform.variants[+i][k]=t.value;return}''',
  '''  if(t.dataset.vf&&S.pform){const[i,k]=t.dataset.vf.split(".");S.pform.variants[+i][k]=t.value;const pm=$("#pmargin");if(pm)pm.textContent=formMargin(S.pform);return}''')
R('''  if(t.dataset.pf&&S.pform){S.pform[t.dataset.pf]=t.value;return}''',
  '''  if(t.dataset.pf&&S.pform){S.pform[t.dataset.pf]=t.value;const pm=$("#pmargin");if(pm)pm.textContent=formMargin(S.pform);return}''')
R('''<span class="q low">Prices not set</span>`})():`PKR ${fmt(p.price)}`} / ${esc(p.unit||"Pcs")}</span>''',
  '''<span class="q low">Prices not set</span>`})():`PKR ${fmt(p.price)}`} / ${esc(p.unit||"Pcs")}${costsOn()&&formMargin(p)?`<br><span class="cmargin">${esc(formMargin(p))}${!hasVar(p)&&num(p.cost)?` · cost ${fmt(p.cost)}`:""}</span>`:""}</span>''')

# settings switch
R('''    <div class="card stack"><h2>Import products</h2>''', '''    <div class="card stack"><h2>Cost prices</h2>
      <label class="slashtog"><input type="checkbox" id="showCosts" ${s.showCosts!==false?"checked":""}><span><b>Show costs and margin</b><br><span class="muted">Turn off on a phone a salesperson uses. Costs never print on documents either way.</span></span></label></div>
    <div class="card stack"><h2>Import products</h2>''')
R('''  if(t.id==="logoFile"&&t.files[0]){uploadLogo(t.files[0]);return}''', '''  if(t.id==="logoFile"&&t.files[0]){uploadLogo(t.files[0]);return}
  if(t.id==="showCosts"){const o={...S.settings,showCosts:t.checked};delete o.id;await saveSettings(o);S.settings={...DEFAULTS,...o};toast(t.checked?"Costs shown":"Costs hidden");return}''')
# keep the cost when a line is saved/converted is automatic (it lives on the line)

# styles
R('/* orders */', '''.mline{margin-right:auto;font-size:12px;color:var(--muted)}.mline .neg,.mpanel .neg{color:var(--danger);font-weight:700}
.item .amtline{display:flex;gap:10px;align-items:baseline;flex-wrap:wrap;justify-content:flex-end}
.mpanel{border:1px dashed var(--line);border-radius:8px;padding:10px 12px;display:flex;flex-direction:column;gap:6px;background:var(--sunk);font-size:13px}
.mpanel:empty{display:none}.mhead{display:flex;justify-content:space-between;gap:8px;flex-wrap:wrap}.mhead .muted{font-size:12px}
.mgrid{display:grid;grid-template-columns:1fr auto;gap:2px 12px;font-variant-numeric:tabular-nums}.mgrid .pos{color:var(--accent-ink)}
.mwarn{color:var(--danger);font-weight:600;font-size:12px}
.cmargin{font-size:11.5px;font-weight:600;color:var(--accent-ink)}
.vrow{grid-template-columns:minmax(0,.9fr) minmax(0,1fr) minmax(0,1fr) minmax(0,1.2fr) auto!important}
@media (max-width:520px){.vrow{grid-template-columns:minmax(0,1fr) minmax(0,1fr) minmax(0,1fr) auto!important}.vrow input[data-vf$=".model"]{grid-column:1/3;grid-row:2}.vrow .vspec{grid-column:3/-1!important;grid-row:2}}
/* orders */''')

open(P, "w", encoding="utf-8").write(s)
print("patched")
