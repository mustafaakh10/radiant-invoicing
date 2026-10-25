/* ---------- built-in order-line reader (no AI): catalogue words + quantities + rates ---------- */
const GENERIC=new Set("led light lights series downlight downlights black white warm cool lamp model the and with for pcs pc set".split(" "));
function catIndex(){
  const tok=s=>String(s||"").toLowerCase().match(/[a-z][a-z0-9\-]{2,}/g)||[];
  const phrases=[],count=new Map();
  for(const p of S.products){
    const kws=String(p.keywords||"").toLowerCase().split(/[,;]+/).map(x=>x.trim()).filter(x=>x.length>1);
    if(p.model)kws.push(String(p.model).toLowerCase());
    for(const k of kws)phrases.push({p,text:k,w:3+k.length/20});
    for(const t of new Set([...tok(p.name),...tok(p.keywords)]))count.set(t,(count.get(t)||0)+1);
  }
  for(const p of S.products)for(const t of new Set(tok(p.name)))if(count.get(t)===1&&!GENERIC.has(t)&&!STOP.has(t))phrases.push({p,text:t,w:2});
  return phrases;
}
function findMentions(lc){
  const out=[];
  for(const ph of catIndex()){const re=new RegExp(`(^|[^a-z0-9])(${ph.text.replace(/[.*+?^${}()|[\]\\]/g,"\\$&")})(?=$|[^a-z0-9])`,"g");let m;
    while((m=re.exec(lc))){const start=m.index+m[1].length;out.push({p:ph.p,start,end:start+ph.text.length,w:ph.w})}}
  out.sort((a,b)=>a.start-b.start||b.w-a.w);
  const kept=[];for(const m of out){const last=kept.at(-1);
    if(last&&m.start<last.end){if(m.w>last.w&&m.p!==last.p)kept[kept.length-1]=m;continue}
    if(last&&last.p===m.p&&!/\d/.test(lc.slice(last.end,m.start))){last.end=m.end;continue}
    kept.push(m)}
  return kept;
}
const wattOf=s=>(String(s).toLowerCase().match(/\b(\d+(?:\.\d+)?)\s*w\b/)||[])[1];
/* returns {items:[{productId,description,qty,rate}], customer:{id}|{name}|null, ok:boolean} */
function localParse(text,d){
  const lc=text.toLowerCase().replace(/\s+/g," ").trim();
  let ms=findMentions(lc);
  /* wattage disambiguation: "trail 3w" vs "trail 5w" */
  ms=ms.map(m=>{const seg=lc.slice(m.start,m.end+8),w=wattOf(seg);if(!w)return m;
    const alt=S.products.filter(p=>p!==m.p&&String(p.keywords||"").toLowerCase().split(/[,;]+/).some(k=>k.trim()&&lc.slice(m.start,m.end).includes(k.trim()))&&new RegExp(`\\b${w}\\s*w\\b`,"i").test(p.name+" "+p.spec));
    return alt.length===1&&!new RegExp(`\\b${w}\\s*w\\b`,"i").test(m.p.name+" "+m.p.spec)?{...m,p:alt[0]}:m});
  const nums=[];const re=/(?<![a-z])(\d[\d,]*(?:\.\d+)?)(\s*(?:k|w|watt|watts|%|m|mtr|meter|meters|ft|pcs|pc|nos|x)\b)?/gi;let m;
  while((m=re.exec(lc))){const unit=(m[2]||"").trim();if(/^(w|watt|watts|%)$/.test(unit))continue;
    let v=parseFloat(m[1].replace(/,/g,""));if(unit==="k")v*=1000;nums.push({v,at:m.index,end:m.index+m[0].length,unit,qtyish:/^(pcs|pc|nos|x)$/.test(unit)})}
  const items=[];let ok=true;
  if(ms.length){
    ms.forEach((mt,i)=>{
      const lo=i?ms[i-1].end:0,hi=i<ms.length-1?ms[i+1].start:lc.length;
      const before=nums.filter(n=>n.end<=mt.start&&n.at>=lo&&!n.used),after=nums.filter(n=>n.at>=mt.end&&n.end<=hi&&!n.used);
      let qty=null,rate=null;
      const qb=before.at(-1);if(qb){qty=qb.v;qb.used=true}
      for(const n of after){if(n.used)continue;
        if(n.qtyish&&qty==null){qty=n.v;n.used=true;continue}
        if(rate==null&&(n.v>=100||qty!=null)&&!(i<ms.length-1&&n===after.at(-1)&&n.v<100&&qty!=null)){rate=n.v;n.used=true;continue}
        if(qty==null&&n.v<100){qty=n.v;n.used=true}}
      items.push({productId:mt.p.id,description:mt.p.name,qty,rate});
    });
  }else{
    /* not in the catalogue: "<qty> <description> <rate>" */
    const words=lc.replace(/(?<![a-z])\d[\d,]*(?:\.\d+)?\s*(?:k|pcs|pc|nos|x)?\b/g," ").replace(/[^a-z0-9\s\-\/×.]/g," ").split(/\s+/).filter(w=>w&&!STOP.has(w));
    if(nums.length&&words.length){const q=nums.find(n=>n.v<100||n.qtyish)||null,r=nums.find(n=>n!==q&&n.v>=100)||null;
      items.push({productId:null,description:words.join(" ").replace(/\b\w/g,c=>c.toUpperCase()),qty:q?.v??null,rate:r?.v??null});ok=false}
  }
  /* customer from the words before the first product / number */
  let customer=null;
  const firstAt=Math.min(ms[0]?.start??Infinity,nums[0]?.at??Infinity);
  const lead=firstAt===Infinity?"":lc.slice(0,firstAt).replace(/[^a-z\s.&']/g," ").split(/\s+/).filter(w=>w&&!STOP.has(w)&&!/^(mr|mrs|ms|sir|for|to)\.?$/.test(w));
  if(lead.length&&ms.length){
    const scored=S.customers.map(c=>{const hay=`${c.name} ${c.attn||""}`.toLowerCase();return{c,s:lead.filter(w=>w.length>2&&hay.includes(w)).length}}).filter(x=>x.s>0).sort((a,b)=>b.s-a.s);
    if(scored.length&&(scored.length===1||scored[0].s>scored[1].s))customer={id:scored[0].c.id};
    else customer={name:lead.join(" ").replace(/\b\w/g,c=>c.toUpperCase())};
  }
  if(ms.length&&items.some(it=>it.qty==null))ok=ok&&true;
  return{items,customer,ok:ok&&items.length>0};
}
/* apply parsed lines (from the built-in reader or the AI) to the document */
function applyParsed(res,d,done,asks){
  if(res.customer){
    const c=res.customer.id&&S.customers.find(x=>x.id===res.customer.id);
    if(c){if(d.customer.id!==c.id){d.customer={id:c.id,name:c.name||"",attn:c.attn||"",phone:c.phone||"",address:c.address||"",ntn:c.ntn||""};done.push(`Customer: ${c.name}`)}}
    else if(res.customer.name&&!d.customer.name){d.customer={...d.customer,id:"",name:String(res.customer.name),attn:String(res.customer.attn||"")};done.push(`Customer: ${d.customer.name}${d.customer.attn?" · "+d.customer.attn:""}`)}
  }
  for(const it of res.items||[]){
    const q0=it.qty==null?null:num(it.qty),q=q0>0?q0:null,rate=it.rate==null?null:num(it.rate);
    const p=it.productId&&S.products.find(x=>x.id===it.productId);
    const ex=p?d.items.findIndex(x=>x.pid===p.id):-1;
    if(ex>=0){const row=d.items[ex];if(q!=null){row.qty=q;row.qtyDel=q}if(rate!=null)row.rate=rate;S.ed.lastItem=ex;done.push(`Updated ${row.name}: ${fmt(row.qty)} × ${fmt(row.rate)}`);continue}
    if(p){d.items.push(itemFromProduct(p,q??1,rate??num(p.price)));done.push(`Added ${fmt(q??1)} × ${p.name} @ ${fmt(rate??num(p.price))}${q==null?" (qty not given, set to 1)":""}`)}
    else{d.items.push({pid:"",name:String(it.description||"Item"),spec:"",warranty:"",img:"",unit:"Pcs",qty:q??1,qtyDel:q??1,rate:rate??0});asks.push(`Added “${it.description||"Item"}”, not in your catalogue. Check the name and rate.`)}
    S.ed.lastItem=d.items.length-1;
  }
}
