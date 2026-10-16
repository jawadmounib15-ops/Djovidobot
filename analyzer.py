import os, time, threading
from flask import Flask, jsonify
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import pandas as pd
from curl_cffi import requests as cffi_requests

PAIRS = ["EURUSD=X","GBPUSD=X","EURGBP=X","USDJPY=X","AUDUSD=X","EURJPY=X","GBPJPY=X","AUDJPY=X","CHFJPY=X","USDCAD=X","USDCHF=X","EURCHF=X","CADJPY=X","CADCHF=X","AUDCHF=X","AUDCAD=X","GBPCAD=X"]
ITALY = ZoneInfo("Europe/Rome")
app = Flask(__name__)
pins_live = []
pins_storico = []
cooldown = {}

def rsi(s,p=14):
    d=s.diff(); g=d.where(d>0,0).rolling(p).mean(); l=-d.where(d<0,0).rolling(p).mean()
    return 100-(100/(1+g/l))
def atr(df,p=14):
    hl=df['High']-df['Low']; hc=abs(df['High']-df['Close'].shift()); lc=abs(df['Low']-df['Close'].shift())
    tr=pd.concat([hl,hc,lc],axis=1).max(axis=1)
    return tr.rolling(p).mean()
def stochastic(df,k=14,d=3):
    lo=df['Low'].rolling(k).min(); hi=df['High'].rolling(k).max()
    k_perc=100*((df['Close']-lo)/(hi-lo))
    return k_perc, k_perc.rolling(d).mean()
def get_df_fast(symbol):
    try:
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?interval=15m&range=5d"
        r = cffi_requests.get(url, impersonate="chrome120", timeout=8)
        quote=r.json()['chart']['result'][0]['indicators']['quote'][0]
        df=pd.DataFrame({'High':quote['high'],'Low':quote['low'],'Close':quote['close']}).dropna()
        return df.tail(300)
    except: return pd.DataFrame()
def scan():
    global pins_live, pins_storico
    count=0
    for symbol in PAIRS:
        if count>=3: break
        clean=symbol.replace("=X","")
        if clean in cooldown and time.time()-cooldown[clean] < 1800: continue
        df=get_df_fast(symbol)
        if len(df)<210: continue
        try:
            df['e20']=df['Close'].ewm(span=20).mean()
            df['e200']=df['Close'].ewm(span=200).mean()
            df['rsi']=rsi(df['Close'])
            df['atr']=atr(df,14)
            df['atr_ma50']=df['atr'].rolling(50).mean()
            df['stoch_k'],_ = stochastic(df)
            last=df.iloc[-1]
            price=float(last['Close']); rsi_v=float(last['rsi']); stoch_k=float(last['stoch_k'])
            if last['atr'] < last['atr_ma50']*0.60: continue
            if last['atr'] > last['atr_ma50']*2.2: continue
            if abs(price-float(last['e20']))/price > 0.005: continue
            if abs(price-float(last['e200']))/price < 0.0004: continue
            if stoch_k==0: continue
            signal=None
            if price>float(last['e200']) and 24<=rsi_v<=42 and stoch_k<25: signal="BUY"
            if price<float(last['e200']) and 58<=rsi_v<=76 and stoch_k>75: signal="SELL"
            if signal:
                pin={"asset":clean,"dir":"CALL SU" if signal=="BUY" else "PUT GIÙ","signal":signal,"entry":round(price,5),"rsi":round(rsi_v),"sto":round(stoch_k),"ora":datetime.now(ITALY).strftime("%H:%M:%S"),"data":datetime.now(ITALY).strftime("%d/%m %H:%M:%S"),"scadenza":(datetime.now(ITALY)+timedelta(minutes=15)).strftime("%H:%M:%S"),"id":f"{clean}{time.time()}"}
                pins_live.insert(0,pin); pins_storico.insert(0,pin)
                pins_live=pins_live[:30]; pins_storico=pins_storico[:1000]
                cooldown[clean]=time.time(); count+=1
        except: pass
def loop():
    while True:
        try: scan()
        except: pass
        time.sleep(50)

@app.route('/')
def home():
    return """<!DOCTYPE html><html><head><meta name='viewport' content='width=device-width, initial-scale=1'><title>V68 FINALE</title><style>body{background:#0a0a0a;color:#fff;font-family:Arial;padding:12px}h2{color:#00ff88}.card{background:#1e1e1e;padding:12px;margin:8px 0;border-radius:10px;display:flex;justify-content:space-between}.call{border-left:5px solid #00ff88}.put{border-left:5px solid #ff4444}button{padding:14px;width:100%;border-radius:10px;font-weight:bold;margin:6px 0;border:0}small{color:#aaa}.scad{color:#ffaa00}</style></head><body>
<h2>📡 V68 FINALE - STRETTO GIUSTO</h2>
<button id="btn" onclick="attiva()" style="background:#ff4444;color:#fff;font-size:18px">🔴 ATTIVA SUONO</button>
<div style="margin:12px 0"><button onclick="show('live')" style="background:#00ff88;padding:10px 16px;border-radius:8px;border:0;font-weight:bold">LIVE</button> <button onclick="show('stor')" style="background:#222;color:#fff;padding:10px 16px;border-radius:8px;border:1px solid #333">STORICO (<span id="numStor">0</span>)</button> <button onclick="localStorage.clear();location.reload()" style="background:#ff4444;color:#fff;padding:10px;border-radius:8px;border:0">🗑️ PULISCI</button></div>
<div id="ora" style="color:#0f8"></div><div id="listLive"></div><div id="listStor" style="display:none"></div>
<script>
let audioCtx=null,suono=false,last=0;
let storico = JSON.parse(localStorage.getItem('v68_storico')||'[]');
let live = JSON.parse(localStorage.getItem('v68_live')||'[]');
function attiva(){audioCtx=new(window.AudioContext||window.webkitAudioContext)();suono=true;document.getElementById('btn').innerHTML='🟢 SUONO ATTIVO';document.getElementById('btn').style.background='#00ff88';document.getElementById('btn').style.color='#000';let o=audioCtx.createOscillator(),g=audioCtx.createGain();o.frequency.value=880;g.gain.value=0.8;o.connect(g);g.connect(audioCtx.destination);o.start();setTimeout(()=>o.stop(),400);}
function beep(){if(!suono||!audioCtx) return;if(audioCtx.state==='suspended') audioCtx.resume();for(let i=0;i<3;i++){setTimeout(()=>{let o=audioCtx.createOscillator(),g=audioCtx.createGain();o.type='square';o.frequency.value=900;g.gain.value=0.9;o.connect(g);g.connect(audioCtx.destination);o.start();setTimeout(()=>o.stop(),350);},i*500);}if(navigator.vibrate) navigator.vibrate([300,100,300]);}
function show(t){document.getElementById('listLive').style.display=t=='live'?'block':'none';document.getElementById('listStor').style.display=t=='stor'?'block':'none';}
function render(d,el){let h='';d.forEach(p=>{h+=`<div class='card ${p.signal=='BUY'?'call':'put'}'><div><b>${p.asset}</b> <small>RSI ${p.rsi} STO ${p.sto}</small><br><small>Entry ${p.entry} | ${p.data} IT</small><br><small class='scad'>Scad ${p.scadenza}</small></div><div style='text-align:right'><b style='color:${p.signal=='BUY'?'#0f8':'#f44'}'>${p.dir}</b></div></div>`;});if(d.length==0) h='<p style="color:#888;text-align:center">Storico salvato nel telefono - filtro finale</p>';document.getElementById(el).innerHTML=h;}
async function load(){
 try{
  let r1=await fetch('/api/pins');let l=await r1.json();
  let r2=await fetch('/api/storico');let s=await r2.json();
  l.forEach(p=>{if(!live.find(x=>x.id==p.id)) live.unshift(p);});
  s.forEach(p=>{if(!storico.find(x=>x.id==p.id)) storico.unshift(p);});
  live=live.slice(0,30);storico=storico.slice(0,1000);
  localStorage.setItem('v68_live',JSON.stringify(live));
  localStorage.setItem('v68_storico',JSON.stringify(storico));
  document.getElementById('ora').innerText=new Date().toLocaleString('it-IT',{timeZone:'Europe/Rome'})+' | Storico: '+storico.length;
  document.getElementById('numStor').innerText=storico.length;
  if(live.length>last&&last!=0&&suono) beep();
  last=live.length;
  render(live,'listLive');render(storico,'listStor');
 }catch(e){}
}
load();setInterval(load,6000);
</script></body></html>"""

@app.route('/api/pins')
def api_pins(): return jsonify(pins_live)
@app.route('/api/storico')
def api_storico(): return jsonify(pins_storico)
threading.Thread(target=loop, daemon=True).start()
if __name__=="__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT",10000)))
