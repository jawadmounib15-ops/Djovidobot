from flask import Flask, jsonify
import yfinance as yf
import pandas as pd
from datetime import datetime
import pytz, time
from curl_cffi import requests as cffi_requests

app = Flask(__name__)
session = cffi_requests.Session(impersonate="chrome")
ROMA = pytz.timezone("Europe/Rome")

PAIRS = ["EURUSD=X","GBPUSD=X","USDJPY=X","AUDUSD=X","USDCAD=X","USDCHF=X","NZDUSD=X",
         "EURJPY=X","EURGBP=X","EURCHF=X","EURCAD=X","EURAUD=X","EURNZD=X",
         "GBPJPY=X","GBPCHF=X","GBPAUD=X","GBPCAD=X","GBPNZD=X",
         "AUDJPY=X","AUDCAD=X","AUDCHF=X","AUDNZD=X",
         "CADJPY=X","CHFJPY=X","NZDJPY=X","CADCHF=X","NZDCAD=X","NZDCHF=X"]

STORICO, cooldown, pending = [], {}, []

def fix_df(df):
    if isinstance(df.columns, pd.MultiIndex): df.columns=df.columns.get_level_values(0)
    return df
def rsi(s,p=14):
    d=s.diff(); g=d.where(d>0,0).rolling(p).mean(); l=-d.where(d<0,0).rolling(p).mean()
    return 100-(100/(1+g/l))
def atr(df,p=14):
    hl=df['High']-df['Low']; hc=abs(df['High']-df['Close'].shift()); lc=abs(df['Low']-df['Close'].shift())
    tr=pd.concat([hl,hc,lc],axis=1).max(axis=1)
    return tr.rolling(p).mean()
def stochastic(df):
    lo=df['Low'].rolling(14).min(); hi=df['High'].rolling(14).max()
    return 100*((df['Close']-lo)/(hi-lo))
def get_df(s):
    try:
        df=yf.Ticker(s, session=session).history(period="5d", interval="15m")
        df=fix_df(df)
        return df if len(df)>=210 else None
    except: return None

def scan():
    global STORICO
    now=datetime.now(ROMA)
    nuovi=[]
    c=0
    for sym in PAIRS:
        if c>=5: break
        clean=sym.replace("=X","")
        if clean in cooldown and time.time()-cooldown[clean]<3600: continue
        try:
            df=get_df(sym)
            if df is None: continue
            df['e20']=df['Close'].ewm(span=20).mean()
            df['e200']=df['Close'].ewm(span=200).mean()
            df['rsi']=rsi(df['Close'])
            df['atr']=atr(df,14)
            df['atr_ma50']=df['atr'].rolling(50).mean()
            df['stoch']=stochastic(df)
            last=df.iloc[-1]
            price=float(last['Close']); rsi_v=float(last['rsi']); stoch_k=float(last['stoch'])
            if last['atr']<last['atr_ma50']*0.60 or last['atr']>last['atr_ma50']*2.0: continue
            if abs(price-float(last['e20']))/price>=0.0028: continue
            if abs(price-float(last['e200']))/price<0.001: continue
            sig=None
            if price>float(last['e200']) and 18<=rsi_v<=33 and stoch_k<20: sig="BUY"
            if price<float(last['e200']) and 62<=rsi_v<=75 and stoch_k>80: sig="SELL"
            if sig and not any(p['symbol']==clean for p in pending):
                s={"coppia":clean,"dir":sig,"rsi":int(rsi_v),"stoch":int(stoch_k),"entry":round(price,5),"ora":now.strftime("%H:%M:%S"),"data":now.strftime("%d/%m %H:%M:%S"),"id":f"{clean}{now.strftime('%H%M%S')}"}
                STORICO.append(s)
                if len(STORICO)>100: STORICO=STORICO[-100:]
                pending.append({"symbol":clean,"time":time.time()})
                cooldown[clean]=time.time()
                nuovi.append(s)
                c+=1
        except: continue
    return nuovi

@app.route('/api/signals')
def api():
    now=datetime.now(ROMA)
    nuovi=scan()
    return jsonify({"ora":now.strftime("%H:%M:%S"),"storico":STORICO[-30:][::-1],"nuovi":nuovi})

HTML="""<!DOCTYPE html><html><head><meta charset=utf-8><meta name=viewport content='width=device-width,initial-scale=1'>
<title>V61.3 FINAL</title>
<style>
body{background:#000;color:#fff;font-family:Arial;margin:0}.header{background:#111;padding:14px;border-bottom:3px solid #0f0}
h2{margin:0;color:#0f0;font-size:17px}.sub{color:#ff0;font-size:11px}
.container{padding:10px}.timer{font-size:38px;color:#ff0;text-align:center;background:#222;padding:12px;border-radius:12px;margin:10px 0}
button{width:100%;padding:18px;border:none;border-radius:14px;font-weight:bold;margin:8px 0;font-size:16px}
#unlock{background:#0f0;color:#000;font-size:18px} #unlock.on{background:#00ff00;box-shadow:0 0 15px #0f0}
.card{border:3px solid #0f0;padding:14px;margin:12px 0;border-radius:14px;background:#151515}
.card.SELL{border-color:#f33}.BUY{color:#0f0;font-size:24px;font-weight:bold}.SELL{color:#f33;font-size:24px;font-weight:bold}
.storico{background:#111;border:1px solid #444;border-radius:12px;padding:10px}
.row{display:flex;justify-content:space-between;font-size:12px;padding:6px 0;border-bottom:1px solid #222}
</style></head><body>
<div class=header><h2>🟢 V61.3 FINAL FIX - BILANCIATO 28 PAIRS - SUONO OK</h2><div class=sub>FIX browser bloccato tolto - ora suona al primo tap</div></div>
<div class=container>
<div id=timer class=timer>19:34:00</div>
<div id=status style=text-align:center;color:#aaa;font-size:12px>Tap AUDIO ON poi TEST</div>
<button id=unlock onclick="unlockAudio()">🔊 TAP PER ATTIVARE AUDIO</button>
<div id=l></div>
<div class=storico><h3 style=color:#ff0;margin:5px 0>📜 STORICO</h3><div id=storico>Vuoto - scan ogni 60 sec</div></div>
<button onclick="testAudio()" style="background:#222;color:#fff;border:1px solid #555">🔔 TEST SUONO</button>
</div>
<script>
let audioCtx=null, audioOn=false, seen=new Set(), first=true;
function unlockAudio(){
  try{
    audioCtx=new (window.AudioContext||window.webkitAudioContext)();
    audioCtx.resume();
    audioOn=true;
    document.getElementById('unlock').innerText='✅ AUDIO ON - ATTIVO';
    document.getElementById('unlock').classList.add('on');
    document.getElementById('status').innerText='✅ Audio sbloccato - ora suonera';
    localStorage.setItem('audio','1');
    // beep breve per confermare
    let o=audioCtx.createOscillator(); let g=audioCtx.createGain();
    o.connect(g); g.connect(audioCtx.destination); o.frequency.value=880; g.gain.value=0.1;
    o.start(); setTimeout(()=>o.stop(),150);
    if(navigator.vibrate) navigator.vibrate(200);
  }catch(e){}
}
function testAudio(){
  if(!audioOn){ unlockAudio(); setTimeout(testAudio,300); return; }
  try{
    let o=audioCtx.createOscillator(); let g=audioCtx.createGain();
    o.connect(g); g.connect(audioCtx.destination); o.frequency.value=880; g.gain.value=0.2;
    o.start(); setTimeout(()=>{o.stop(); let o2=audioCtx.createOscillator(); o2.connect(g); o2.frequency.value=1200; o2.start(); setTimeout(()=>o2.stop(),200);},200);
    if(navigator.vibrate) navigator.vibrate([400,100,400]);
  }catch(e){}
}
function alarm(){
  if(!audioOn) return;
  testAudio();
  if(navigator.vibrate) navigator.vibrate([600,100,600,100,1000]);
}
async function load(){
  try{
    let r=await fetch('/api/signals'); let d=await r.json();
    document.getElementById('timer').innerText=d.ora;
    let h=document.getElementById('storico');
    if(!d.storico||d.storico.length==0) h.innerHTML='Vuoto';
    else { let html=''; d.storico.forEach(s=>{html+=`<div class=row ${s.dir}><span>${s.data} ${s.coppia}</span><span><b>${s.dir}</b> ${s.entry}</span></div>`}); h.innerHTML=html; }
    if(d.nuovi && d.nuovi.length>0){
      d.nuovi.forEach(s=>{
        if(!seen.has(s.id)){
          seen.add(s.id);
          if(!first){
            document.getElementById('l').innerHTML=`<div class=card ${s.dir}><b>🚨 ${s.coppia} ${s.dir}</b> ${s.data}<br>RSI ${s.rsi} STO ${s.stoch} Entry ${s.entry}</div>`+document.getElementById('l').innerHTML;
            alarm();
          }
        }
      });
    }
    if(first){ d.storico.forEach(s=>seen.add(s.id)); first=false; }
  }catch(e){}
}
setInterval(load,5000); load();
// auto unlock se gia salvato
if(localStorage.getItem('audio')=='1'){ setTimeout(()=>{ document.getElementById('status').innerText='Tap una volta ovunque per riattivare audio'; },1000); document.addEventListener('click', ()=>{ if(!audioOn) unlockAudio(); }, {once:true}); }
</script></body></html>"""

@app.route('/')
def home(): return HTML

if __name__=="__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT",10000)))
