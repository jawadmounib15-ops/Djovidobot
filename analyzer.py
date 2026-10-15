import os, time, threading
from flask import Flask, jsonify
from datetime import datetime, timedelta
import yfinance as yf
import pandas as pd
import requests

TOKEN = os.getenv("TELEGRAM_TOKEN", os.getenv("TOKEN", ""))
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", os.getenv("CHAT_ID", ""))

PAIRS = ["EURUSD=X","GBPUSD=X","USDJPY=X","AUDUSD=X","USDCAD=X","USDCHF=X","NZDUSD=X","EURJPY=X","EURGBP=X","EURCHF=X","EURCAD=X","EURAUD=X","GBPJPY=X","GBPCHF=X","GBPAUD=X","AUDJPY=X","CADJPY=X","CHFJPY=X","NZDJPY=X","AUDCAD=X","NZDCAD=X"]

app = Flask(__name__)

pins_live = []
pins_storico = []
cooldown = {}

def ora_now(): return datetime.now().strftime("%H:%M:%S")
def data_now(): return datetime.now().strftime("%d/%m %H:%M:%S")

def send(msg):
    try: requests.get(f"https://api.telegram.org/bot{TOKEN}/sendMessage", params={"chat_id":CHAT_ID,"text":msg}, timeout=10)
    except: pass

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

def stochastic(df,k=14,d=3):
    lo=df['Low'].rolling(k).min(); hi=df['High'].rolling(k).max()
    k_perc=100*((df['Close']-lo)/(hi-lo))
    return k_perc, k_perc.rolling(d).mean()

def scan():
    global pins_live, pins_storico
    count_this_scan=0
    for symbol in PAIRS:
        if count_this_scan>=2: break
        clean=symbol.replace("=X","")
        if clean in cooldown and time.time()-cooldown[clean] < 5400: continue
        try:
            df=yf.download(symbol, period="5d", interval="15m", progress=False)
            df=fix_df(df)
            if len(df)<210: continue
            df['e20']=df['Close'].ewm(span=20).mean()
            df['e200']=df['Close'].ewm(span=200).mean()
            df['rsi']=rsi(df['Close'])
            df['atr']=atr(df,14)
            df['atr_ma50']=df['atr'].rolling(50).mean()
            df['stoch_k'],_ = stochastic(df)
            last=df.iloc[-1]
            price=float(last['Close']); rsi_v=float(last['rsi']); stoch_k=float(last['stoch_k'])

            if last['atr'] < last['atr_ma50']*0.70: continue
            if last['atr'] > last['atr_ma50']*1.8: continue

            tocco_e20=abs(price-float(last['e20']))/price < 0.003
            dist_e200=abs(price-float(last['e200']))/price
            if dist_e200 < 0.001: continue

            signal=None
            if price>float(last['e200']) and tocco_e20 and 30<=rsi_v<=36 and stoch_k<15: signal="BUY"
            if price<float(last['e200']) and tocco_e20 and 64<=rsi_v<=70 and stoch_k>85: signal="SELL"

            if signal:
                # SCADENZA 15 MINUTI
                scad_time = datetime.now() + timedelta(minutes=15)
                pin = {
                    "asset": clean,
                    "dir": "CALL SU" if signal=="BUY" else "PUT GIÙ",
                    "signal": signal,
                    "entry": round(price,5),
                    "rsi": round(rsi_v,0),
                    "sto": round(stoch_k,0),
                    "ora": ora_now(),
                    "data": data_now(),
                    "scadenza": scad_time.strftime("%H:%M:%S"),
                    "scad_ts": scad_time.timestamp(),
                    "scad": "15 MIN"
                }
                pins_live.insert(0,pin)
                pins_storico.insert(0,pin)
                pins_live=pins_live[:20]
                pins_storico=pins_storico[:100]

                send(f"🎯 L4 PELO {signal} {clean} RSI {rsi_v:.0f} STO {stoch_k:.0f} Entry {price:.5f} Scad {pin['scadenza']}")
                cooldown[clean]=time.time()
                count_this_scan+=1
        except: continue

def loop():
    send(f"🚀 V61.1 STRETTO + SUONO/STORICO/SCADENZA - {len(PAIRS)} coppie")
    while True:
        try: scan()
        except: pass
        time.sleep(60)

@app.route('/')
def home():
    return """
<!DOCTYPE html><html><head><meta name='viewport' content='width=device-width, initial-scale=1'>
<title>V61.1 STRETTO</title>
<style>
body{background:#0a0a0a;color:#fff;font-family:Arial;padding:12px;margin:0}
h2{color:#00ff88}
.card{background:#1e1e1e;padding:12px;margin:8px 0;border-radius:10px;display:flex;justify-content:space-between;align-items:center}
.call{border-left:5px solid #00ff88}.put{border-left:5px solid #ff4444}
button{background:#00ff88;color:#000;border:0;padding:14px;width:100%;border-radius:10px;font-weight:bold;font-size:17px;margin:6px 0}
.tab{background:#222;color:#fff;border:1px solid #333;padding:10px 18px;border-radius:8px;margin-right:6px}
.tab.active{background:#00ff88;color:#000;font-weight:bold}
small{color:#aaa}
.scad{color:#ffaa00;font-weight:bold}
</style>
</head><body>
<h2>📡 V61.1 STRETTO + SUONO</h2>
<button id="btn" onclick="attiva()">🔔 ATTIVA SUONO FORTE</button>
<div style="margin:10px 0">
<button class="tab active" id="tLive" onclick="show('live')">LIVE</button>
<button class="tab" id="tStor" onclick="show('stor')">STORICO (<span id="numStor">0</span>)</button>
</div>
<div id="ora"></div>
<div id="listLive">Avvio scanner... 60 sec</div>
<div id="listStor" style="display:none"></div>
<script>
let audioCtx=null,suono=false,last=0;
function attiva(){audioCtx=new(window.AudioContext||window.webkitAudioContext)();suono=true;document.getElementById('btn').innerHTML='🔊 SUONO ATTIVO';document.getElementById('btn').style.background='#ffaa00';beep();}
function beep(){if(!audioCtx)return;for(let i=0;i<3;i++){setTimeout(()=>{let o=audioCtx.createOscillator(),g=audioCtx.createGain();o.type='square';o.frequency.value=880;g.gain.value=0.9;o.connect(g);g.connect(audioCtx.destination);o.start();g.gain.exponentialRampToValueAtTime(0.01,audioCtx.currentTime+0.4);o.stop(audioCtx.currentTime+0.4);},i*500);}}
function show(t){document.getElementById('tLive').classList.toggle('active',t=='live');document.getElementById('tStor').classList.toggle('active',t=='stor');document.getElementById('listLive').style.display=t=='live'?'block':'none';document.getElementById('listStor').style.display=t=='stor'?'block':'none';}
function render(data,el){
  let h=''; let now=Date.now()/1000;
  data.forEach(p=>{
    let scaduta = p.scad_ts && now > p.scad_ts? '<span style="color:#f44">SCADUTO</span>' : '<span class="scad">Scad '+p.scadenza+'</span>';
    h+=`<div class='card ${p.signal=='BUY'?'call':'put'}'><div><b style="font-size:18px">${p.asset}</b> <small>RSI ${p.rsi} STO ${p.sto}</small><br><small>Entry: ${p.entry} | ${p.scad}</small><br><small>${p.data}</small></div><div style='text-align:right'><b style='color:${p.signal=='BUY'?'#00ff88':'#ff4444'};font-size:17px'>${p.dir}</b><br>${scaduta}</div></div>`;
  });
  if(data.length==0) h='<p style="color:#888;text-align:center">Scanner attivo...<br>In attesa di L4 PELO</p>';
  document.getElementById(el).innerHTML=h;
}
async function load(){
  let r1=await fetch('/api/pins'); let live=await r1.json();
  let r2=await fetch('/api/storico'); let stor=await r2.json();
  document.getElementById('ora').innerText=new Date().toLocaleTimeString()+' | Live:'+live.length+' Storico:'+stor.length;
  document.getElementById('numStor').innerText=stor.length;
  if(live.length>last && last!=0 && suono){beep(); if(navigator.vibrate) navigator.vibrate([300,100,300,100,600]);}
  last=live.length;
  render(live,'listLive'); render(stor,'listStor');
}
load(); setInterval(load, 8000);
</script>
</body></html>
"""

@app.route('/api/pins')
def api_pins(): return jsonify(pins_live)

@app.route('/api/storico')
def api_storico(): return jsonify(pins_storico)

threading.Thread(target=loop, daemon=True).start()

if __name__=="__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT",10000)))
