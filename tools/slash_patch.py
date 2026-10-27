#!/usr/bin/env python3
"""One-off patch: optional slashed (offer vs list) prices per document."""
import os
P = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src", "app.src.html")
s = open(P, encoding="utf-8").read()
def R(a, b, cnt=1):
    global s
    n = s.count(a); assert n == cnt, f"expected {cnt}, found {n}: {a[:110]!r}"; s = s.replace(a, b)

# totals: savings vs list prices (only when the document shows slashed prices)
R('''  return{sub,disc,tax,grand:sub-disc+tax,qty:d.items.reduce((a,it)=>a+num(d.type==="DN"?it.qtyDel:it.qty),0)};''',
  '''  const slashSave=slashOn(d)?d.items.reduce((a,it)=>a+(isSlashed(d,it)?(num(it.list)-num(it.rate))*num(it.qty):0),0):0;
  return{sub,disc,tax,grand:sub-disc+tax,qty:d.items.reduce((a,it)=>a+num(d.type==="DN"?it.qtyDel:it.qty),0),save:slashOn(d)?Math.round(slashSave+disc):0};''')
R('function calc(d){', '''const slashOn=d=>!!d.slash&&d.type!=="DN";
const isSlashed=(d,it)=>slashOn(d)&&num(it.list)>num(it.rate);
function calc(d){''')

# HTML preview: struck list price above the offer rate, and "You save" under the grand total
R('''<div class="p-v p-rt">${fmt(it.rate)}</div><div class="p-v b p-am">${fmt(lineAmt(it))}</div></div>`;''',
  '''<div class="p-v p-rt">${isSlashed(d,it)?`<span class="p-was">${fmt(it.list)}</span><span class="p-now">${fmt(it.rate)}</span>`:fmt(it.rate)}</div><div class="p-v b p-am">${fmt(lineAmt(it))}</div></div>`;''')
R('''      <div class="p-gt"><div class="k">GRAND TOTAL</div><div class="v">PKR ${fmt(t.grand)}</div></div></div></div>''',
  '''      <div class="p-gt"><div class="k">GRAND TOTAL</div><div class="v">PKR ${fmt(t.grand)}</div></div>${t.save>0?`<div class="p-save">You save PKR ${fmt(t.save)}</div>`:""}</div></div>''')
R('.p-gt .v{font-size:12px;font-weight:700}', '''.p-gt .v{font-size:12px;font-weight:700}
.p-was{display:block;font-size:8px;line-height:1.3;color:#9aa1a9;text-decoration:line-through}
.p-now{display:block;font-weight:700;line-height:1.3}
.p-save{text-align:right;font-size:9px;font-weight:700;color:#6d9f53;margin-top:6px;padding-right:10px}''')

# PDF
R('''      tx(fmt(it.rate),C[di+3][0]+C[di+3][1]-6,cy,{...v,align:"right"});''',
  '''      if(isSlashed(d,it)){const rx=C[di+3][0]+C[di+3][1]-6,was=fmt(it.list),ww=width(clean(was),8,"normal");
        tx(was,rx,cy-6,{size:8,color:"#9aa1a9",align:"right"});rect(rx-ww,cy-6+5.2,ww,0.7,"#9aa1a9");
        tx(fmt(it.rate),rx,cy+5,{size:10,lh:1.4,style:"bold",align:"right"});}
      else tx(fmt(it.rate),C[di+3][0]+C[di+3][1]-6,cy,{...v,align:"right"});''')
R('''    const hr=Math.max(ly,gy+30)+20;if(draw)rect(48,hr,698,1,LN);''',
  '''    if(t.save>0)tx(`You save PKR ${fmt(t.save)}`,736,gy+36,o({size:9,style:"bold",color:G,align:"right"}));
    const hr=Math.max(ly,gy+30+(t.save>0?18:0))+20;if(draw)rect(48,hr,698,1,LN);''')

# editor: toggle, list price per line, savings in the totals panel
R('''      :`<div class="sect"><h2>Totals</h2><div class="g3">''',
  '''      :`<div class="sect"><h2>Totals</h2>
        <label class="slashtog"><input type="checkbox" data-f="slash" ${d.slash?"checked":""}><span><b>Show slashed prices</b><br><span class="muted">For offers you want to highlight: the list price is struck through above the offer price. Off for normal quotes.</span></span></label>
        <div class="g3">''')
R('''<label class="f">Rate (PKR)<input data-f="items.${i}.rate" inputmode="decimal" value="${esc(it.rate)}"></label></div>''',
  '''<label class="f">${slashOn(d)?"Offer rate":"Rate (PKR)"}<input data-f="items.${i}.rate" inputmode="decimal" value="${esc(it.rate)}"></label></div>
    ${slashOn(d)?`<label class="f">List price, shown slashed <span class="muted" style="font-weight:400">(leave empty for no slash on this line)</span><input data-f="items.${i}.list" inputmode="decimal" value="${esc(it.list??"")}" placeholder="e.g. ${esc(fmt(Math.round(num(it.rate)*1.15/50)*50||0))}"></label>`:""}''')
R('''<span class="gt">Grand total</span><span class="gt">PKR ${fmt(t.grand)}</span>''',
  '''<span class="gt">Grand total</span><span class="gt">PKR ${fmt(t.grand)}</span>${t.save>0?`<span class="saveline">Customer saves</span><span class="saveline">PKR ${fmt(t.save)}</span>`:""}''')
R('''  if(t.type==="checkbox"&&t.dataset.f){setPath(S.ed.doc,t.dataset.f,t.checked);updatePreview();return}''',
  '''  if(t.type==="checkbox"&&t.dataset.f){S.ed.dirty=true;setPath(S.ed.doc,t.dataset.f,t.checked);if(t.dataset.f==="slash")$("#items").innerHTML=itemsHTML(S.ed.doc);updatePreview();return}''')
R('''.vpick{''', '''.slashtog{display:flex;gap:10px;align-items:flex-start;font-size:13px;padding:10px 12px;border:1px solid var(--line);border-radius:8px;cursor:pointer}
.slashtog input{width:auto;margin-top:3px}.slashtog:has(input:checked){border-color:var(--accent);background:color-mix(in srgb,var(--accent) 8%,var(--surface))}
.totals .saveline{color:var(--accent-ink);font-weight:600}
.vpick{''')

# new docs default off; quotation -> invoice keeps it
R('''    notes:type==="DN"?"":(s.notesDefault||""),''', '''    slash:false,notes:type==="DN"?"":(s.notesDefault||""),''')
R('''  if(to==="INV"){d.refQT=from.number;''', '''  if(to==="INV"){d.slash=!!from.slash;d.refQT=from.number;''')

# typing
R('''  /* totals: round off / target total / discounts */''', r'''  /* slashed offer prices: "trail offer 4500", "10% off tulip 12w", "trail was 5200", "remove offer trail", "hide slash prices" */
  if(!dn){
    if(/^(?:show|turn on|enable|add)?\s*(?:the\s+)?(?:slash(?:ed)?|strike(?:through)?|offer|sale)\s*(?:prices?|pricing)?(?:\s+on)?$/.test(lc)){d.slash=true;return"Slashed prices on for this document"}
    if(/^(?:hide|turn off|disable|no)\s+(?:the\s+)?(?:slash(?:ed)?|strike(?:through)?|offer|sale)\s*(?:prices?|pricing)?$|^(?:slash(?:ed)?|offer|sale)\s*(?:prices?\s*)?off$/.test(lc)){d.slash=false;return"Slashed prices hidden (offer rates stay as they are)"}
    if((m=lc.match(/^(?:remove|cancel|clear|no)\s+(?:the\s+)?(?:offer|sale|slash(?:ed)?)(?:\s+price)?\s*(?:on|for|from)?\s*(.*)$/))){const ti=targetItems(m[1]||"this",d);if(pickOr(ti))return pickOr(ti);
      const msgs=ti.map(i=>{const it=d.items[i];if(num(it.list)>num(it.rate))it.rate=num(it.list);it.list="";return`${nm(i)} back to ${fmt(it.rate)}`});return msgs.join(", ")}
    const offerKw=/\b(offer|sale|slash(?:ed)?|special)\b/.test(lc),wasKw=/\b(was|list price|mrp|original price|retail price)\b/.test(lc);
    const pctOff=/\d+(?:\.\d+)?\s*%\s*off\b|\boff\s+\d+(?:\.\d+)?\s*%/.test(lc)&&!/\b(discount|each|per|total)\b/.test(lc);
    if((offerKw||wasKw||pctOff)&&d.items.length){
      const ti=targetItems(lc.replace(/\b(offer|sale|slash(?:ed)?|special|was|list price|mrp|original price|retail price|price|off)\b/g," "),d);if(pickOr(ti))return pickOr(ti);
      const p=pctIn(lc),a=amountIn(lc.replace(/\d+(?:\.\d+)?\s*%/g," "));
      if(p==null&&a==null)return{ask:"What price? e.g. “trail offer 4500”, “10% off trail” or “trail was 5200”."};
      const msgs=[];
      for(const i of ti){const it=d.items[i],base=num(it.list)>num(it.rate)?num(it.list):num(it.rate);
        if(wasKw&&!offerKw){if(a==null)return{ask:"What was the list price?"};if(a<=num(it.rate))return{ask:`The list price must be higher than the current rate (${fmt(it.rate)}) to show a slash.`};it.list=a}
        else if(p!=null){if(!base)return{ask:`${nm(i)} has no price yet.`};it.list=base;it.rate=Math.round(base*(1-p/100))}
        else{if(a>=base)return{ask:`The offer must be lower than ${fmt(base)}. To set a normal price, say “${nm(i).split(" · ")[0].split(/\s[–-]\s/).at(-1).toLowerCase()} rate ${fmt(a)}”.`};it.list=base;it.rate=a}
        msgs.push(`${nm(i)}: was ${fmt(it.list)}, now ${fmt(it.rate)}`);S.ed.lastItem=i}
      const wasOn=d.slash;d.slash=true;return msgs.join(", ")+(wasOn?"":" · slashed prices on for this document");
    }
  }
  /* totals: round off / target total / discounts */''')
R('''<br><b>Totals</b>:''', '''<br><b>Offers</b> (slashed price): “trail offer 4500” · “10% off tulip 12w” · “trail was 5200” · “remove offer trail” · “hide slash prices”<br><b>Totals</b>:''')

open(P, "w", encoding="utf-8").write(s)
print("patched")
