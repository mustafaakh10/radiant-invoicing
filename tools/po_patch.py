#!/usr/bin/env python3
"""One-off patch: suppliers + purchase orders (PO) made from an invoice at cost prices, with a negotiation stage."""
import os
P = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src", "app.src.html")
s = open(P, encoding="utf-8").read()
def R(a, b, cnt=1):
    global s
    n = s.count(a); assert n == cnt, f"expected {cnt}, found {n}: {a[:120]!r}"; s = s.replace(a, b)

# ---------- basics ----------
R('const TYPE_NAME={QT:"Quotation",INV:"Invoice",DN:"Delivery note"};',
  'const TYPE_NAME={QT:"Quotation",INV:"Invoice",DN:"Delivery note",PO:"Purchase order"};\nconst PO_STATUS=[["draft","Draft"],["negotiating","Negotiating"],["ordered","Ordered"],["received","Received"]];\nconst poStatusName=k=>(PO_STATUS.find(x=>x[0]===k)||PO_STATUS[0])[1];')
R('''  notesDefault:"Prices are exclusive of GST.",''',
  '''  notesDefault:"Prices are exclusive of GST.",
  termsPO:"Please confirm prices and delivery date on receipt of this order.\\nGoods must match the description and specification above.\\nDeliver with a delivery challan quoting this PO number.\\nPayment as agreed.",''')
R('''const S={settings:{...DEFAULTS},products:[],customers:[],docs:[],''', '''const S={settings:{...DEFAULTS},products:[],customers:[],suppliers:[],sform:null,cmode:"customers",docs:[],''')
R('ready:{settings:false,products:false,customers:false,docs:false}', 'ready:{settings:false,products:false,customers:false,suppliers:false,docs:false}')
R('for(const col of["products","customers"])DB.collection(col)', 'for(const col of["products","customers","suppliers"])DB.collection(col)')
R('''  else if(S.view==="customers"&&col==="customers")renderCList();''', '''  else if(S.view==="customers"&&(col==="customers"||col==="suppliers"))renderCList();''')
R('const slashOn=d=>!!d.slash&&d.type!=="DN";', 'const slashOn=d=>!!d.slash&&d.type!=="DN"&&d.type!=="PO";')

# ---------- printed document (HTML preview) ----------
R('''  const title={QT:"QUOTATION",INV:"INVOICE",DN:"DELIVERY NOTE"}[d.type];
  const sub={QT:"CUSTOMER COPY",INV:"ORIGINAL  ·  CUSTOMER COPY",DN:"CUSTOMER COPY"}[d.type];''',
  '''  const title={QT:"QUOTATION",INV:"INVOICE",DN:"DELIVERY NOTE",PO:"PURCHASE ORDER"}[d.type];
  const sub={QT:"CUSTOMER COPY",INV:"ORIGINAL  ·  CUSTOMER COPY",DN:"CUSTOMER COPY",PO:"SUPPLIER COPY"}[d.type];''')
R('''  const cdet=[c.attn?("Attn: "+c.attn+(c.phone?"  ·  "+c.phone:"")):c.phone,c.address,c.ntn&&("Customer NTN: "+c.ntn)].filter(Boolean).join("\\n");
  const no=d.number||`RL-${d.type}-${(d.date||todayISO()).slice(0,4)}-····`;''',
  '''  const cdet=partyLines(d);
  const no=d.number||`RL-${d.type}-${(d.date||todayISO()).slice(0,4)}-····`;''')
R('''  if(dn){meta=[["DN No.",no],["Delivery Date",fdate(d.date)]];if(d.refINV)meta.push(["Invoice Ref.",d.refINV])}
  const cols=''', '''  if(dn){meta=[["DN No.",no],["Delivery Date",fdate(d.date)]];if(d.refINV)meta.push(["Invoice Ref.",d.refINV])}
  if(d.type==="PO"){meta=[["PO No.",no],["PO Date",fdate(d.date)]];if(d.dueDate)meta.push(["Required By",fdate(d.dueDate)])}
  const cols=''')
R('''    <div class="r">${bank?`<div class="p-lbl">BANK DETAILS</div><div class="p-tx">${esc(bank)}</div>`:""}</div></div>''',
  '''    <div class="r">${d.type==="PO"?`<div class="p-lbl">DELIVER TO</div><div class="p-tx">${esc(poDeliverTo())}</div>`:bank?`<div class="p-lbl">BANK DETAILS</div><div class="p-tx">${esc(bank)}</div>`:""}</div></div>''')
R('''  const word={QT:"quotation",INV:"invoice",DN:"delivery note"}[d.type];
  const foot=`This is a computer-generated ${word}.  For queries: ${[s.phone,s.email].filter(Boolean).join("  ·  ")}${dn?"":"  ·  Thank you for your business."}`;
  return `<div class="paper">''',
  '''  const word={QT:"quotation",INV:"invoice",DN:"delivery note",PO:"purchase order"}[d.type];
  const foot=`This is a computer-generated ${word}.  For queries: ${[s.phone,s.email].filter(Boolean).join("  ·  ")}${dn?"":d.type==="PO"?"  ·  Thank you.":"  ·  Thank you for your business."}`;
  return `<div class="paper">''')
R('''<div class="p-lbl">${dn?"DELIVER TO":"BILL TO"}</div>''', '''<div class="p-lbl">${partyLabel(d)}</div>''')
R('''function docHTML(d){''', '''/* the party box: customer (bill to / deliver to) or, on a purchase order, the supplier */
const partyLabel=d=>d.type==="PO"?"SUPPLIER":d.type==="DN"?"DELIVER TO":"BILL TO";
function partyLines(d){const c=d.customer||{};
  return[c.attn?("Attn: "+c.attn+(c.phone?"  ·  "+c.phone:"")):c.phone,d.type==="PO"?c.email:"",c.address,c.ntn&&((d.type==="PO"?"NTN: ":"Customer NTN: ")+c.ntn)].filter(Boolean).join("\\n")}
const poDeliverTo=()=>{const s=S.settings;return[s.company,s.address,[s.phone&&("Tel: "+s.phone),s.email].filter(Boolean).join("  ·  ")].filter(Boolean).join("\\n")};
function docHTML(d){''')

# ---------- PDF ----------
R('''  const word={QT:"quotation",INV:"invoice",DN:"delivery note"}[d.type];
  const title={QT:"QUOTATION",INV:"INVOICE",DN:"DELIVERY NOTE"}[d.type];''',
  '''  const word={QT:"quotation",INV:"invoice",DN:"delivery note",PO:"purchase order"}[d.type];
  const title={QT:"QUOTATION",INV:"INVOICE",DN:"DELIVERY NOTE",PO:"PURCHASE ORDER"}[d.type];''')
R('''  const foot=`This is a computer-generated ${word}.  For queries: ${[s.phone,s.email].filter(Boolean).join("  ·  ")}${dn?"":"  ·  Thank you for your business."}`;
  const LIMIT=1050;''', '''  const foot=`This is a computer-generated ${word}.  For queries: ${[s.phone,s.email].filter(Boolean).join("  ·  ")}${dn?"":d.type==="PO"?"  ·  Thank you.":"  ·  Thank you for your business."}`;
  const LIMIT=1050;''')
R('''  tx({QT:"CUSTOMER COPY",INV:"ORIGINAL  ·  CUSTOMER COPY",DN:"CUSTOMER COPY"}[d.type],746,70,''', '''  tx({QT:"CUSTOMER COPY",INV:"ORIGINAL  ·  CUSTOMER COPY",DN:"CUSTOMER COPY",PO:"SUPPLIER COPY"}[d.type],746,70,''')
R('''  if(dn){meta=[["DN No.",no],["Delivery Date",fdate(d.date)]];if(d.refINV)meta.push(["Invoice Ref.",d.refINV])}
  const cdet=[c.attn?("Attn: "+c.attn+(c.phone?"  ·  "+c.phone:"")):c.phone,c.address,c.ntn&&("Customer NTN: "+c.ntn)].filter(Boolean).join("\\n");''',
  '''  if(dn){meta=[["DN No.",no],["Delivery Date",fdate(d.date)]];if(d.refINV)meta.push(["Invoice Ref.",d.refINV])}
  if(d.type==="PO"){meta=[["PO No.",no],["PO Date",fdate(d.date)]];if(d.dueDate)meta.push(["Required By",fdate(d.dueDate)])}
  const cdet=partyLines(d);''')
R('''  tx(dn?"DELIVER TO":"BILL TO",60,150,{size:8,style:"bold",color:G});''', '''  tx(partyLabel(d),60,150,{size:8,style:"bold",color:G});''')
R('''    let b=0;if(bank){tx("BANK DETAILS",440,ty,o({size:8,style:"bold",color:G}));b=tx(bank,440,ty+16,o({size:9,color:G2,lh:1.6,w:306}))}''',
  '''    let b=0;if(d.type==="PO"){tx("DELIVER TO",440,ty,o({size:8,style:"bold",color:G}));b=tx(poDeliverTo(),440,ty+16,o({size:9,color:G2,lh:1.6,w:306}))}
    else if(bank){tx("BANK DETAILS",440,ty,o({size:8,style:"bold",color:G}));b=tx(bank,440,ty+16,o({size:9,color:G2,lh:1.6,w:306}))}''')

# ---------- orders: purchase step ----------
R('''    const qt=docs.filter(d=>d.type==="QT").sort(by).at(-1),inv=docs.filter(d=>d.type==="INV").sort(by).at(-1),dns=docs.filter(d=>d.type==="DN").sort(by);''',
  '''    const qt=docs.filter(d=>d.type==="QT").sort(by).at(-1),inv=docs.filter(d=>d.type==="INV").sort(by).at(-1),dns=docs.filter(d=>d.type==="DN").sort(by),pos=docs.filter(d=>d.type==="PO").sort(by);
    if(!qt&&!inv&&!dns.length)return null;''')
R('''    return{key,docs,qt,inv,dns,base,status,updated,customer:base.customer||{},''', '''    return{key,docs,qt,inv,dns,pos,base,status,updated,customer:base.customer||{},''')
R('''  }).sort((a,b)=>b.updated-a.updated);
}''', '''  }).filter(Boolean).sort((a,b)=>b.updated-a.updated);
}''')
R('''  return `<div class="steps">${step("1 · Quotation",j.qt,j.inv||j.dns.length?"skip":"todo")}<span class="sbar ${j.inv?"on":""}"></span>${step("2 · Invoice",j.inv,j.dns.length?"skip":"todo")}<span class="sbar ${j.dns.length?"on":""}"></span>${step("3 · Delivery",dnLast,"todo",j.dns.length>1?` +${j.dns.length-1}`:"")}</div>`;''',
  '''  const po=j.pos?.[0],poX=po?` · ${poStatusName(po.status)}${j.pos.length>1?` +${j.pos.length-1}`:""}`:"";
  return `<div class="steps">${step("1 · Quotation",j.qt,j.inv||j.dns.length?"skip":"todo")}<span class="sbar ${j.inv?"on":""}"></span>${step("2 · Invoice",j.inv,j.dns.length?"skip":"todo")}<span class="sbar ${po?"on":""}"></span>${step("3 · Purchase",po,j.dns.length?"skip":"todo",poX)}<span class="sbar ${j.dns.length?"on":""}"></span>${step("4 · Delivery",dnLast,"todo",j.dns.length>1?` +${j.dns.length-1}`:"")}</div>`;''')
R('''  if(j.status==="invoiced")return`<button class="btn pri sm" data-act="convert" data-id="${j.inv.id}" data-to="DN">Make delivery note</button>`;''',
  '''  if(j.status==="invoiced")return`${j.pos.length?"":`<button class="btn sm" data-act="convert" data-id="${j.inv.id}" data-to="PO">Make purchase order</button>`}<button class="btn pri sm" data-act="convert" data-id="${j.inv.id}" data-to="DN">Make delivery note</button>`;''')
R('''      <div class="job-ft"><span class="muted">${fdate(j.base.date)}</span>${nextAction(j)}</div></div>`}).join("");''',
  '''      <div class="job-ft"><span class="muted">${fdate(j.base.date)}</span><div class="row" style="gap:6px">${nextAction(j)}</div></div></div>`}).join("");''')
R('''      :[["all","All"],["QT","Quotations"],["INV","Invoices"],["DN","Delivery notes"]]''', '''      :[["all","All"],["QT","Quotations"],["INV","Invoices"],["DN","Delivery notes"],["PO","Purchase orders"]]''')
R('''    <div class="d-type"><span class="tag ${d.type}">${d.type}</span></div>''', '''    <div class="d-type"><span class="tag ${d.type}">${d.type}</span>${d.type==="PO"?` <span class="muted" style="font-size:11px">${esc(poStatusName(d.status))}</span>`:""}</div>''')
R('''  <div class="pgrid">${["QT","INV","DN"].map(t=>''', '''  <div class="pgrid">${["QT","INV","DN","PO"].map(t=>''')

# ---------- new docs / convert ----------
R('''    slash:false,notes:type==="DN"?"":(s.notesDefault||""),terms:type==="QT"?s.termsQT:type==="INV"?s.termsINV:"",showImages:true,''',
  '''    slash:false,notes:type==="DN"||type==="PO"?"":(s.notesDefault||""),terms:type==="QT"?s.termsQT:type==="INV"?s.termsINV:type==="PO"?(s.termsPO||DEFAULTS.termsPO):"",showImages:true,status:type==="PO"?"draft":undefined,''')
R('''async function convert(src,to){
  const j=jobFor(src);''', '''async function convert(src,to){
  if(to==="PO")return makePOs(src);
  const j=jobFor(src);''')
R('''function openDocById(id){''', '''/* ---------- purchase orders: invoice lines grouped by supplier, priced at our cost; negotiated before ordering ---------- */
const supOf=p=>p&&(p.supplierId&&S.suppliers.find(x=>x.id===p.supplierId)||S.suppliers.find(x=>p.supplier&&x.name.toLowerCase()===String(p.supplier).toLowerCase()||(x.aliases||[]).some(a=>p.supplier&&a.toLowerCase()===String(p.supplier).toLowerCase())))||null;
const supParty=x=>x?{id:x.id,name:x.name||"",attn:x.attn||"",phone:x.phone||"",email:x.email||"",address:x.address||"",ntn:x.ntn||""}:{id:"",name:"Supplier (to choose)",attn:"",phone:"",email:"",address:"",ntn:""};
async function makePOs(src){
  const j=jobFor(src),from=j?.inv||src;
  let jobId=from.jobId;
  if(!jobId){jobId=uid("j");for(const x of(j?.docs||[from]))if(x.id){x.jobId=jobId;try{await put("docs",x.id,strip(clone(x)))}catch{}}}
  /* what is already on purchase orders for this job is not ordered twice */
  const onPO=new Map();for(const po of j?.pos||[])for(const it of po.items||[]){const k=itemKey(it);onPO.set(k,(onPO.get(k)||0)+num(it.qty))}
  const groups=new Map();
  for(const it of from.items||[]){const k=itemKey(it),have=onPO.get(k)||0,q=num(it.qty)-have;onPO.set(k,Math.max(0,have-num(it.qty)));if(q<=0)continue;
    const p=it.pid&&S.products.find(x=>x.id===it.pid),sup=supOf(p),gk=sup?.id||"";
    if(!groups.has(gk))groups.set(gk,{sup,items:[]});const c=lineCost(it);
    groups.get(gk).items.push({pid:it.pid||"",vid:it.vid||"",opts:clone(it.opts||{}),name:it.name,spec:it.spec||"",warranty:it.warranty||"",img:it.img||"",unit:it.unit||"Pcs",qty:q,qtyDel:q,rate:c,list:c,cost:c})}
  if(!groups.size){const first=j?.pos?.[0];if(first){openDocById(first.id);toast("Everything on this invoice is already on a purchase order")}else toast("No items to order");return}
  const drafts=[...groups.values()].map(g=>{const d=blankDoc("PO");d.jobId=jobId;d.refINV=from.type==="INV"?from.number:"";d.customer=supParty(g.sup);d.items=g.items;d.showImages=from.showImages;d.taxMode="excl";return d});
  if(drafts.length===1){openEditor(drafts[0],true);toast(`Purchase order drafted at cost prices${drafts[0].customer.id?" for "+drafts[0].customer.name:""}`);return}
  /* one PO per supplier: all saved as drafts, first one opened */
  let firstId=null;
  for(const d of drafts){d.number=await nextNumber("PO",d.date);d.totals=calc(d);d.createdAt=d.updatedAt=Date.now();const id=uid("d");firstId=firstId||id;await put("docs",id,strip(clone(d)))}
  toast(`${drafts.length} purchase orders drafted, one per supplier`);setTimeout(()=>openDocById(firstId),300);
}
/* what negotiation saved, and what this PO leaves as profit against the invoice */
function poNumbers(d){
  const t=calc(d),net=t.sub-t.disc,quoted=d.items.reduce((a,it)=>a+num(num(it.list)>0?it.list:it.rate)*num(it.qty),0),saved=Math.max(0,Math.round(quoted-net));
  const inv=d.refINV&&S.docs.find(x=>x.type==="INV"&&x.number===d.refINV);let sale=null;
  if(inv){const pool=new Map();for(const it of inv.items||[]){const k=itemKey(it);if(!pool.has(k))pool.set(k,num(it.rate))}
    const it0=calc(inv),f=it0.sub?(it0.sub-it0.disc)/it0.sub:1;
    sale=Math.round(d.items.reduce((a,it)=>a+(pool.has(itemKey(it))?pool.get(itemKey(it)):0)*num(it.qty),0)*f)}
  return{net,quoted:Math.round(quoted),saved,sale,profit:sale==null?null:sale-net,pct:sale?Math.round((sale-net)/sale*1000)/10:0,inv}}
function poPanel(d){if(!d.items.length)return"";const m=poNumbers(d);
  return `<div class="mhead"><b>Negotiation</b><span class="muted">Private · never on the PDF</span></div>
  <div class="mgrid"><span>Supplier's first price</span><b>PKR ${fmt(m.quoted)}</b><span>Agreed (after discount)</span><b>PKR ${fmt(m.net)}</b>
  <span class="pos">Saved by negotiating</span><b class="pos">PKR ${fmt(m.saved)}${m.quoted?` · ${Math.round(m.saved/m.quoted*1000)/10}%`:""}</b>
  ${m.sale!=null?`<span>Sold on ${esc(m.inv.number)}</span><b>PKR ${fmt(m.sale)}</b><span class="${m.profit<0?"neg":"pos"}">${m.profit<0?"Loss":"Profit"} on these items</span><b class="${m.profit<0?"neg":"pos"}">PKR ${fmt(Math.abs(m.profit))} · ${pctTxt(m.pct)}</b>`:""}</div>
  <div class="muted" style="font-size:12px">Change a line's agreed rate, or type “linea 15 rate 1900”, “5% discount”, “discount 2000”. The first price stays for comparison.</div>`}
function poLine(d,i){const it=d.items[i],l=num(it.list),r=num(it.rate);if(!l||l===r)return`<span class="muted">First price ${fmt(l||r)}</span>`;
  return`<span class="${r>l?"neg":""}">First price ${fmt(l)} · ${r<l?"saved":"up"} ${fmt(Math.abs(l-r)*num(it.qty))}</span>`}
function openDocById(id){''')

# ---------- editor ----------
R('''function vEditor(){
  const d=S.ed.doc,dn=d.type==="DN";''', '''function vEditor(){
  const d=S.ed.doc,dn=d.type==="DN",po=d.type==="PO";''')
R('''    const row=itemFromProduct(p,q??1,rate??null,v?.id,opts);d.items.push(row);''', '''    const row=itemFromProduct(p,q??1,rate??null,v?.id,opts);if(d.type==="PO"&&rate==null){row.rate=num(row.cost)||row.rate;row.list=row.rate}d.items.push(row);''')
R('''        if(d.type==="INV")return j.status==="delivered"?"":`<button class="btn" data-act="edconvert" data-to="DN">${j.dns.length?"Deliver remaining":"Make delivery note"}</button>`;''',
  '''        if(d.type==="INV")return(j.pos.length?`<button class="btn" data-act="open" data-id="${j.pos[0].id}">Open ${esc(j.pos[0].number)}</button>`:`<button class="btn" data-act="edconvert" data-to="PO">Make purchase order</button>`)+(j.status==="delivered"?"":`<button class="btn" data-act="edconvert" data-to="DN">${j.dns.length?"Deliver remaining":"Make delivery note"}</button>`);
        if(d.type==="PO"){const inv=j.inv;return(inv?`<button class="btn" data-act="open" data-id="${inv.id}">Open ${esc(inv.number)}</button>`:"")+`<button class="btn ${S.armed==="pocosts"?"armed":""}" data-act="pocosts">${S.armed==="pocosts"?"Confirm: update catalogue":"Save agreed costs to catalogue"}</button>`}''')
R('''        ${dn?`<label class="f">Invoice ref.<input data-f="refINV" value="${esc(d.refINV)}" placeholder="RL-INV-…"></label>`:""}
      </div></div>''', '''        ${dn||po?`<label class="f">Invoice ref.${po?` <span class="muted" style="font-weight:400">(not printed)</span>`:""}<input data-f="refINV" value="${esc(d.refINV)}" placeholder="RL-INV-…"></label>`:""}
        ${po?`<label class="f">Required by (optional)<input type="date" data-f="dueDate" value="${esc(d.dueDate)}"></label>
        <label class="f">Stage<select data-f="status">${PO_STATUS.map(([k,l])=>`<option value="${k}" ${(d.status||"draft")===k?"selected":""}>${l}</option>`).join("")}</select></label>`:""}
      </div></div>''')
R('''      <div class="sect"><div class="spread"><h2 style="margin:0">${dn?"Deliver to":"Bill to"}</h2><button class="btn sm ghost" data-act="savecust">Save to customers</button></div>
        <select id="custPick">${custOptions(d.customer.id)}</select>
        <label class="f">Company / name<input data-f="customer.name" value="${esc(d.customer.name)}" placeholder="Mall of Central Square"></label>
        <div class="g2"><label class="f">Attn<input data-f="customer.attn" value="${esc(d.customer.attn)}" placeholder="Mr. Mashood"></label>
        <label class="f">Phone<input data-f="customer.phone" value="${esc(d.customer.phone)}"></label></div>
        <div class="g2"><label class="f">Address<input data-f="customer.address" value="${esc(d.customer.address)}"></label>
        <label class="f">Customer NTN<input data-f="customer.ntn" value="${esc(d.customer.ntn)}"></label></div></div>''',
  '''      <div class="sect"><div class="spread"><h2 style="margin:0">${po?"Supplier":dn?"Deliver to":"Bill to"}</h2><button class="btn sm ghost" data-act="savecust">${po?"Save to suppliers":"Save to customers"}</button></div>
        <select id="custPick">${po?supOptions(d.customer.id):custOptions(d.customer.id)}</select>
        <label class="f">Company / name<input data-f="customer.name" value="${esc(d.customer.name)}" placeholder="${po?"Luméra Studio":"Mall of Central Square"}"></label>
        <div class="g2"><label class="f">Attn<input data-f="customer.attn" value="${esc(d.customer.attn)}" placeholder="${po?"Ahmed":"Mr. Mashood"}"></label>
        <label class="f">Phone<input data-f="customer.phone" value="${esc(d.customer.phone)}"></label></div>
        ${po?`<label class="f">Email<input data-f="customer.email" value="${esc(d.customer.email||"")}"></label>`:""}
        <div class="g2"><label class="f">Address<input data-f="customer.address" value="${esc(d.customer.address)}"></label>
        <label class="f">${po?"Supplier NTN":"Customer NTN"}<input data-f="customer.ntn" value="${esc(d.customer.ntn)}"></label></div></div>''')
R('''        <label class="slashtog"><input type="checkbox" data-f="slash" ${d.slash?"checked":""}><span><b>Show slashed prices</b><br><span class="muted">For offers you want to highlight: the list price is struck through above the offer price. Off for normal quotes.</span></span></label>''',
  '''        ${po?"":`<label class="slashtog"><input type="checkbox" data-f="slash" ${d.slash?"checked":""}><span><b>Show slashed prices</b><br><span class="muted">For offers you want to highlight: the list price is struck through above the offer price. Off for normal quotes.</span></span></label>`}''')
R('''        ${costsOn()?`<div class="mpanel" id="marginPanel"></div>`:""}''', '''        ${po?`<div class="mpanel" id="poPanel"></div>`:costsOn()?`<div class="mpanel" id="marginPanel"></div>`:""}''')
R('''function custOptions(sel){''', '''function supOptions(sel){return `<option value="">— Pick saved supplier —</option>`+S.suppliers.map(c=>`<option value="${c.id}" ${c.id===sel?"selected":""}>${esc(c.name)}${c.attn?" · "+esc(c.attn):""}</option>`).join("")}
function custOptions(sel){''')
# item rows on a PO: agreed rate + first price
R('''<label class="f">${slashOn(d)?"Offer rate":"Rate (PKR)"}<input data-f="items.${i}.rate" inputmode="decimal" value="${esc(it.rate)}"></label></div>''',
  '''<label class="f">${d.type==="PO"?"Agreed rate":slashOn(d)?"Offer rate":"Rate (PKR)"}<input data-f="items.${i}.rate" inputmode="decimal" value="${esc(it.rate)}"></label></div>
    ${d.type==="PO"?`<label class="f">Supplier's first price <span class="muted" style="font-weight:400">(for comparison, not printed)</span><input data-f="items.${i}.list" inputmode="decimal" value="${esc(it.list??"")}"></label>`:""}''')
R('''    <div class="amtline">${costsOn()?`<span class="mline" data-mg="${i}">${marginLine(d,i)}</span>`:""}Amount''',
  '''    <div class="amtline">${d.type==="PO"?`<span class="mline" data-mg="${i}">${poLine(d,i)}</span>`:costsOn()?`<span class="mline" data-mg="${i}">${marginLine(d,i)}</span>`:""}Amount''')
R('''  if(costsOn()&&d.type!=="DN"){const mp=$("#marginPanel");''', '''  if(d.type==="PO"){const pp=$("#poPanel");if(pp)pp.innerHTML=poPanel(d);d.items.forEach((_,i)=>{const el=document.querySelector(`[data-mg="${i}"]`);if(el)el.innerHTML=poLine(d,i)})}
  else if(costsOn()&&d.type!=="DN"){const mp=$("#marginPanel");''')
R('''<span class="saveline">Customer saves</span>''', '''<span class="saveline">${d.type==="PO"?"You save":"Customer saves"}</span>''')

# ---------- actions ----------
R('''    case"savecust":{const c=S.ed.doc.customer;if(!c.name.trim()){toast("Enter a customer name first");break}''',
  '''    case"savecust":if(S.ed.doc.type==="PO"){const c=S.ed.doc.customer;if(!c.name.trim()||/to choose/i.test(c.name)){toast("Enter the supplier name first");break}
      const sid=c.id||uid("s");c.id=sid;await put("suppliers",sid,{...(S.suppliers.find(x=>x.id===sid)?strip(S.suppliers.find(x=>x.id===sid)):{}),name:c.name,attn:c.attn||"",phone:c.phone||"",email:c.email||"",address:c.address||"",ntn:c.ntn||""});$("#custPick").innerHTML=supOptions(sid);toast("Supplier saved");break}
    {const c=S.ed.doc.customer;if(!c.name.trim()){toast("Enter a customer name first");break}''')
R('''    case"newcust":''', '''    case"pocosts":{if(S.armed!=="pocosts"){S.armed="pocosts";vEditorKeep();break}S.armed=null;const d=S.ed.doc;let n=0;const touched=new Map();
      for(const it of d.items){const p=it.pid&&(touched.get(it.pid)||clone(S.products.find(x=>x.id===it.pid)||null));if(!p||!num(it.rate))continue;
        const v=it.vid&&(p.variants||[]).find(x=>x.id===it.vid);if(v)v.cost=num(it.rate);else p.cost=num(it.rate);touched.set(p.id,p);n++}
      for(const p of touched.values())await put("products",p.id,strip(p));toast(n?`Updated cost on ${touched.size} product${touched.size===1?"":"s"}`:"No catalogue items on this PO");vEditorKeep();break}
    case"cmode":S.cmode=b.dataset.m;S.cform=null;S.sform=null;S.armed=null;vCustomers();break;
    case"newsup":S.sform={id:"",name:"",attn:"",phone:"",email:"",address:"",ntn:""};S.armed=null;renderCForm();break;
    case"editsup":S.sform=clone(S.suppliers.find(c=>c.id===id));renderCForm();break;
    case"cancelsup":S.sform=null;renderCForm();break;
    case"supnew":{const c=S.suppliers.find(x=>x.id===id);const d=blankDoc("PO");d.customer=supParty(c);openEditor(d,true);break}
    case"savesupf":{const c=S.sform;if(!c.name.trim()){toast("Enter a name");break}await put("suppliers",c.id||uid("s"),{...strip(c),name:c.name.trim()});S.sform=null;renderCForm();toast("Supplier saved");break}
    case"delsup":if(S.armed===S.sform?.id){await del("suppliers",S.sform.id);S.sform=null;S.armed=null;renderCForm();toast("Supplier deleted")}else{S.armed=S.sform.id;renderCForm()}break;
    case"newcust":''')
R('''  if(t.id==="custPick"&&S.ed){S.ed.dirty=true;const c=S.customers.find(x=>x.id===t.value);''',
  '''  if(t.id==="custPick"&&S.ed&&S.ed.doc.type==="PO"){S.ed.dirty=true;const c=S.suppliers.find(x=>x.id===t.value);if(c){S.ed.doc.customer=supParty(c);vEditorKeep()}return}
  if(t.id==="custPick"&&S.ed){S.ed.dirty=true;const c=S.customers.find(x=>x.id===t.value);''')
R('''  if(t.dataset.cf&&S.cform){S.cform[t.dataset.cf]=t.value;return}''', '''  if(t.dataset.cf&&S.cform){S.cform[t.dataset.cf]=t.value;return}
  if(t.dataset.sf2&&S.sform){S.sform[t.dataset.sf2]=t.value;return}''')

# ---------- customers page: Customers | Suppliers ----------
R('''function vCustomers(){
  $("#view").innerHTML=`<div class="spread" style="margin-bottom:16px"><div><div class="eyebrow">Address book</div><h1>Customers</h1></div><button class="btn pri" data-act="newcust">Add customer</button></div>''',
  '''function vCustomers(){const sup=S.cmode==="suppliers";
  $("#view").innerHTML=`<div class="spread" style="margin-bottom:16px"><div><div class="eyebrow">Address book</div><h1>${sup?"Suppliers":"Customers"}</h1></div>
    <div class="row"><div class="seg"><button data-act="cmode" data-m="customers" aria-pressed="${!sup}">Customers</button><button data-act="cmode" data-m="suppliers" aria-pressed="${sup}">Suppliers</button></div>
    <button class="btn pri" data-act="${sup?"newsup":"newcust"}">${sup?"Add supplier":"Add customer"}</button></div></div>''')
R('''function renderCList(){const el=$("#clist");if(!el)return;''', '''function renderCList(){const el=$("#clist");if(!el)return;
  if(S.cmode==="suppliers"){el.innerHTML=S.suppliers.length?`<div class="clist">${S.suppliers.map(c=>{const n=S.products.filter(p=>supOf(p)?.id===c.id).length,o=S.docs.filter(d=>d.type==="PO"&&d.customer?.id===c.id).length;
    return `<div class="crow"><div style="min-width:0"><div class="cn">${esc(c.name)}</div><div class="muted" style="font-size:13px">${esc([c.attn,c.phone,c.email].filter(Boolean).join(" · ")||"No contact details")}</div></div>
    <div class="row"><span class="muted" style="font-size:12px">${n} product${n===1?"":"s"} · ${o} PO${o===1?"":"s"}</span><button class="btn sm" data-act="supnew" data-id="${c.id}">New PO</button><button class="btn sm" data-act="editsup" data-id="${c.id}">Edit</button></div></div>`}).join("")}</div>`
   :`<div class="card empty">${S.ready.suppliers||!DB?"No suppliers yet. Add one, then pick it on your products so purchase orders go to the right place.":"Loading suppliers…"}</div>`;return}''')
R('''function renderCForm(){const el=$("#cform");if(!el)return;const c=S.cform;''', '''function renderCForm(){const el=$("#cform");if(!el)return;
  if(S.cmode==="suppliers"){const c=S.sform;
    if(!c){el.innerHTML=`<div class="card muted" style="font-size:13px">Pick a supplier on each product (Catalogue → Edit). <b>Make purchase order</b> on an invoice then splits the items by supplier at your cost prices.</div>`;return}
    el.innerHTML=`<div class="card stack"><h2>${c.id?"Edit supplier":"New supplier"}</h2>
     <label class="f">Company / name<input data-sf2="name" value="${esc(c.name)}"></label>
     <div class="g2"><label class="f">Attn<input data-sf2="attn" value="${esc(c.attn||"")}" placeholder="Ahmed"></label><label class="f">Phone<input data-sf2="phone" value="${esc(c.phone||"")}"></label></div>
     <label class="f">Email<input data-sf2="email" value="${esc(c.email||"")}"></label>
     <label class="f">Address<input data-sf2="address" value="${esc(c.address||"")}"></label>
     <label class="f">Supplier NTN<input data-sf2="ntn" value="${esc(c.ntn||"")}"></label>
     <div class="row"><button class="btn pri" data-act="savesupf">Save supplier</button><button class="btn ghost" data-act="cancelsup">Cancel</button>
     ${c.id?`<button class="btn sm danger ${S.armed===c.id?"armed":""}" data-act="delsup" style="margin-left:auto">${S.armed===c.id?"Confirm delete":"Delete"}</button>`:""}</div></div>`;return}
  const c=S.cform;''')

# ---------- product form: supplier ----------
R('''      await put("products",pid,{name:p.name.trim(),''', '''      await put("products",pid,{supplierId:p.supplierId||"",name:p.name.trim(),''')
R('''   <div class="row" style="gap:8px;font-size:12px"><span class="muted">Fill cost from sale price minus</span>''',
  '''   <label class="f">Supplier <span class="muted" style="font-weight:400">(purchase orders go here)</span><select data-pf="supplierId"><option value="">— None —</option>${S.suppliers.map(x=>`<option value="${esc(x.id)}" ${supOf(p)?.id===x.id?"selected":""}>${esc(x.name)}</option>`).join("")}</select></label>
   <div class="row" style="gap:8px;font-size:12px"><span class="muted">Fill cost from sale price minus</span>''')

# ---------- numbering settings ----------
R('''${["QT","INV","DN"].map(t=>`<label class="f">RL-${t}''', '''${["QT","INV","DN","PO"].map(t=>`<label class="f">RL-${t}''')
R('''  for(const t of["QT","INV","DN"]){const v=await counterGet''', '''  for(const t of["QT","INV","DN","PO"]){const v=await counterGet''')
R('''case"savecounters":{const y=todayISO().slice(0,4);for(const t of["QT","INV","DN"])''', '''case"savecounters":{const y=todayISO().slice(0,4);for(const t of["QT","INV","DN","PO"])''')

# ---------- styles ----------
R('.tag.DN{background:color-mix(in srgb,#4f86b8 18%,transparent);color:#3a6f9e}', '.tag.DN{background:color-mix(in srgb,#4f86b8 18%,transparent);color:#3a6f9e}\n.tag.PO{background:color-mix(in srgb,#8a63b8 18%,transparent);color:#6a4596}')

open(P, "w", encoding="utf-8").write(s)
print("patched")
