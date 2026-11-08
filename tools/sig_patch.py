#!/usr/bin/env python3
"""One-off patch: signature image above the signatory line on quotations, invoices and purchase orders."""
import os
P = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src", "app.src.html")
s = open(P, encoding="utf-8").read()
def R(a, b, cnt=1):
    global s
    n = s.count(a); assert n == cnt, f"expected {cnt}, found {n}: {a[:120]!r}"; s = s.replace(a, b)

R('''  signName:"",signTitle:"Authorised Signatory",''', '''  signName:"",signTitle:"Authorised Signatory",signImg:"",signOn:true,''')
R('''async function storeImage(blob){''', '''/* signature: keep only the ink. Light pixels (paper, or a checkerboard baked into a "transparent" export) become transparent */
const sigOn=d=>!!S.settings.signImg&&S.settings.signOn!==false&&d.type!=="DN";
async function cleanSignature(file){
  const url=URL.createObjectURL(file);
  try{const img=await loadImg(url);const sc=Math.min(1,900/img.naturalWidth);const c=document.createElement("canvas");
    c.width=Math.max(1,Math.round(img.naturalWidth*sc));c.height=Math.max(1,Math.round(img.naturalHeight*sc));
    const x=c.getContext("2d");x.imageSmoothingQuality="high";x.drawImage(img,0,0,c.width,c.height);
    const px=x.getImageData(0,0,c.width,c.height),a=px.data;let x0=c.width,y0=c.height,x1=-1,y1=-1;
    for(let i=0;i<a.length;i+=4){const L=0.299*a[i]+0.587*a[i+1]+0.114*a[i+2],ink=L>=100?0:L<=50?1:(100-L)/50,al=Math.round(ink*a[i+3]);
      a[i]=20;a[i+1]=20;a[i+2]=24;a[i+3]=al;if(al>24){const p=i/4,px_=p%c.width,py=(p/c.width)|0;if(px_<x0)x0=px_;if(px_>x1)x1=px_;if(py<y0)y0=py;if(py>y1)y1=py}}
    if(x1<0)throw new Error("No ink found");
    x.putImageData(px,0,0);const pad=6,w=Math.min(c.width,x1-x0+1+2*pad),h=Math.min(c.height,y1-y0+1+2*pad);
    const o=document.createElement("canvas");o.width=w;o.height=h;o.getContext("2d").drawImage(c,Math.max(0,x0-pad),Math.max(0,y0-pad),w,h,0,0,w,h);
    return await new Promise(r=>o.toBlob(r,"image/png"));
  }finally{URL.revokeObjectURL(url)}
}
async function uploadSignature(file){
  try{toast("Cleaning signature…");const b=await cleanSignature(file);const url=await storeImage(b);const o={...S.settings,signImg:url};delete o.id;await saveSettings(o);S.settings={...DEFAULTS,...o};vSettings();toast("Signature added")}
  catch(e){toast("Couldn't read that signature image")}
}
async function storeImage(blob){''')

# HTML preview
R('''    <div class="p-sig"><div class="ln"></div>''', '''    <div class="p-sig">${sigOn(d)?`<img class="p-sigimg" src="${esc(s.signImg)}" alt="">`:""}<div class="ln"></div>''')
R('.p-sig{align-self:flex-end;width:160px;margin-top:72px;text-align:center}', '.p-sig{align-self:flex-end;width:160px;margin-top:72px;text-align:center;position:relative}\n.p-sigimg{position:absolute;left:10px;right:10px;bottom:100%;margin-bottom:2px;height:46px;width:140px;object-fit:contain}')

# PDF: remember where the line went, draw the image just above it
R('''    const sy=ty+16+Math.max(a,b)+76;
    if(draw)rect(586,sy,160,1,DK);''', '''    const sy=ty+16+Math.max(a,b)+76;sigAt=sy;
    if(draw)rect(586,sy,160,1,DK);''')
R('''  function closing(y0,draw){''', '''  let sigAt=null;
  function closing(y0,draw){''')
R('''  closing(y0,true);

  const pages=doc.getPages();''', '''  closing(y0,true);
  if(sigOn(d)&&sigAt!=null)await image(s.signImg,596,sigAt-50,140,46);

  const pages=doc.getPages();''')

# settings card
R('''    <div class="card stack"><h2>Cost prices</h2>''', '''    <div class="card stack"><div class="spread"><h2 style="margin:0">Signature</h2>${s.signImg?`<button class="btn sm ghost danger ${S.armed==="delsign"?"armed":""}" data-act="resetsign">${S.armed==="delsign"?"Confirm remove":"Remove"}</button>`:""}</div>
      <label class="logo-drop" for="signFile"><span class="logo-paper" style="min-height:70px">${s.signImg?`<img src="${esc(s.signImg)}" alt="Your signature" style="max-height:70px">`:`<span class="muted" style="font-size:13px">No signature yet</span>`}</span>
        <span class="logo-cta"><b>${s.signImg?"Replace signature":"Add your signature"}</b>: a photo or PNG of it on white paper</span><input type="file" accept="image/png,image/jpeg" id="signFile" hidden></label>
      <label class="slashtog"><input type="checkbox" id="signOn" ${s.signOn!==false?"checked":""}><span><b>Sign quotations, invoices and purchase orders</b><br><span class="muted">Printed above the signatory line. Delivery notes stay unsigned for the driver and customer.</span></span></label>
      <div class="muted" style="font-size:12px">The background is removed automatically, even a grey checkerboard from a background-remover.</div></div>
    <div class="card stack"><h2>Cost prices</h2>''')
R('''  if(t.id==="showCosts"){''', '''  if(t.id==="signFile"&&t.files[0]){uploadSignature(t.files[0]);return}
  if(t.id==="signOn"){const o={...S.settings,signOn:t.checked};delete o.id;await saveSettings(o);S.settings={...DEFAULTS,...o};toast(t.checked?"Documents will be signed":"Signature off");return}
  if(t.id==="showCosts"){''')
R('''    case"resetlogo":''', '''    case"resetsign":{if(S.armed!=="delsign"){S.armed="delsign";vSettings();break}S.armed=null;const o={...S.settings,signImg:""};delete o.id;await saveSettings(o);S.settings={...DEFAULTS,...o};vSettings();toast("Signature removed");break}
    case"resetlogo":''')

open(P, "w", encoding="utf-8").write(s)
print("patched")
