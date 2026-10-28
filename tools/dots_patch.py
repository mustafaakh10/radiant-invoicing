#!/usr/bin/env python3
"""One-off patch: list-style demands ("laser blade" header, "02 dott=14nos", "20 watt"), same product twice in one entry adds up."""
import os
P = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src", "app.src.html")
s = open(P, encoding="utf-8").read()
def R(a, b, cnt=1):
    global s
    n = s.count(a); assert n == cnt, f"expected {cnt}, found {n}: {a[:110]!r}"; s = s.replace(a, b)

# 02 -> 2 (two-digit only, so phone numbers stay), 20 watt -> 20w, dott/dots -> dot, head(s) -> head
R('''const normOrder=t=>String(t||"").toLowerCase().replace(/[’']/g,"").replace(/(\\d)\\s+(w|k|watt|watts)\\b/g,"$1$2")''',
  '''const normOrder=t=>String(t||"").toLowerCase().replace(/[’']/g,"").replace(/(^|[^\\d.])0(\\d)(?![\\d.])/g,"$1$2").replace(/(\\d)\\s+(w|k|watt|watts)\\b/g,"$1$2").replace(/(\\d)watts?\\b/g,"$1w").replace(/\\b(dott?s?|heads)\\b/g,m=>m.startsWith("d")?"dot":"head")''')

# heading lines ("laser blade") give context to the lines under them
R('''  const itemClauses=rest.filter(c=>looksLikeItems(c,d));
  rest.filter(c=>!itemClauses.includes(c)).forEach(c=>asks.push(`Didn't understand “${c}”. Tap “What can I type?” for examples.`));''',
  '''  const itemClauses=[];let ctx="";S.ed.runRows=new Set();
  for(const c of rest){
    if(isHeading(c)){ctx=c;continue}
    const c2=ctx&&!findMentions(normOrder(c)).length?`${ctx} ${c}`:c;
    if(looksLikeItems(c2,d))itemClauses.push(c2);else asks.push(`Didn't understand “${c}”. Tap “What can I type?” for examples.`)}''')
R('''/* does a leftover clause look like a new order line for the AI? */''',
  '''/* a line like "laser blade" or "COB" on its own: a heading for the lines below it */
const plainW=t=>normOrder(t).replace(/[^a-z0-9 ]/g," ").split(" ").filter(Boolean).map(w=>w.replace(/s$/,"")).join(" ");
function isHeading(c){if(/\\d/.test(c))return false;const w=plainW(c);if(!w)return false;
  return S.products.some(p=>[p.category,p.series].some(x=>x&&plainW(x)===w))||findMentions(normOrder(c)).length>0}
/* does a leftover clause look like a new order line for the AI? */''')

# same product twice in one entry: add the quantities instead of overwriting
R('''    if(ex>=0){const row=d.items[ex];if(q!=null){row.qty=q;row.qtyDel=q}''',
  '''    if(ex>=0&&S.ed.runRows?.has(d.items[ex])&&q!=null){const row=d.items[ex],was=num(row.qty);row.qty=was+q;row.qtyDel=row.qty;if(rate!=null)row.rate=rate;S.ed.lastItem=ex;done.push(`${label} appears twice: ${fmt(was)} + ${fmt(q)} = ${fmt(row.qty)}`);continue}
    if(ex>=0){const row=d.items[ex];if(q!=null){row.qty=q;row.qtyDel=q}''')
R('''    const row=itemFromProduct(p,q??1,rate??null,v?.id,opts);d.items.push(row);S.ed.lastItem=d.items.length-1;''',
  '''    const row=itemFromProduct(p,q??1,rate??null,v?.id,opts);d.items.push(row);S.ed.lastItem=d.items.length-1;S.ed.runRows?.add(row);''')

open(P, "w", encoding="utf-8").write(s)
print("patched")
