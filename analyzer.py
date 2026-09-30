# analyzer.py - V65 LARGO ORA - TESTIAMO SUBITO - POI STRINGIAMO
import yfinance as yf, pandas as pd
from flask import Flask, jsonify
from datetime import datetime
import pytz

app = Flask(__name__)

# OGGI LARGO = 18 COPPIE PER TESTARE SUBITO
MODE = "LENTO"
PAIRS = ["EURUSD=X","GBPUSD=X","USDJPY=X","AUDUSD=X","USDCAD=X","USDCHF=X","EURJPY=X","GBPJPY=X","EURGBP=X","EURCHF=X","AUDJPY=X","GBPCHF=X","NZDJPY=X","EURAUD=X","GBPAUD=X","CADJPY=X","CHFJPY=X","NZDCAD=X"]

# PIANO PER STRINGERE:
# OGGI -> LENTO (largo, 4-6 al giorno, testiamo subito)
# DOMANI -> MEDIO (2-4 al giorno)
# DOPODOMANI -> SICURO (1-2 al giorno ma WINNER)
SETTINGS = {
    "LENTO": {"rsi_buy": (20,42), "rsi_sell": (58,80), "sto_buy": 26, "sto_sell": 74, "tocco": 0.0022, "ratio": 1.8},
    "MEDIO": {"rsi_buy": (24,38), "rsi_sell": (62,76), "sto_buy": 18, "sto_sell": 82, "tocco": 0.0015, "ratio": 2.2},
    "SICURO": {"rsi_buy": (30,36), "rsi_sell": (64,70), "sto_buy": 15, "sto_sell": 85, "tocco": 0.0010, "ratio": 2.8},
}
CFG = SETTINGS[MODE]

def fix_df(df):
    if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
    return df
def rsi(s,p=14):
    d=s.diff(); g=d.where(d>0,0).rolling(p).mean(); l=-d.where(d<0,0).rolling(p).mean()
    return 100-(100/(1+g/l))
def atr(df,p=14):
    hl=df['High']-df['Low']; hc=abs(df['High']-df['Close'].shift()); lc=abs(df['Low']-df['Close'].shift())
    tr=pd.concat([hl,hc,lc],axis=1).max(axis=1); return tr.rolling(p).mean()
def stoch(df,k=14):
    return 100*((df['Close']-df['Low'].rolling(k).min())/(df['High'].rolling(k).max()-df['Low'].rolling(k).min()))

def scan_now():
    tz = pytz.timezone('Europe/Rome')
    now = datetime.now(tz).strftime('%H:%M:%S IT')
    out=[]
    for sym in PAIRS:
        try:
            df15=yf.download(sym, period="5d", interval="15m", progress=False); df15=fix_df(df15)
            if len(df15)<210: continue
            df15['e20']=df15['Close'].ewm(span=20).mean(); df15['e200']=df15['Close'].ewm(span=200).mean()
            df15['rsi']=rsi(df15['Close']); df15['atr']=atr(df15,14); df15['atr_ma']=df15['atr'].rolling(50).mean(); df15['sto']=stoch(df15,14)
            df60=yf.download(sym, period="20d", interval="60m", progress=False); df60=fix_df(df60); df60['e200']=df60['Close'].ewm(span=200).mean()
            last=df15.iloc[-1]; last60=df60.iloc[-1]
            price=float(last['Close']); rsi_v=float(last['rsi']); sto_v=float(last['sto'])
            e20=float(last['e20']); e200=float(last['e200']); e200_60=float(last60['e200'])
            if not ((price>e200_60 and price>e200) or (price<e200_60 and price<e200)): continue
            if last['atr'] < last['atr_ma']*0.70 or last['atr'] > last['atr_ma']*2.0: continue
            if abs(price-e20)/price > CFG["tocco"]: continue
            o=float(last['Open']); h=float(last['High']); l=float(last['Low']); c=float(last['Close'])
            body=abs(c-o); rng=h-l
            if rng==0 or body < rng*0.07 or body > rng*0.30: continue
            up=h-max(o,c); down=min(o,c)-l; ratio=max(up,down)/body if body>0 else 0
            if ratio < CFG["ratio"] or min(up,down) > rng*0.22: continue
            sig=None
            if price>e200 and down>up and CFG["rsi_buy"][0] <= rsi_v <= CFG["rsi_buy"][1] and sto_v < CFG["sto_buy"]: sig="BUY"
            if price<e200 and up>down and CFG["rsi_sell"][0] <= rsi_v <= CFG["rsi_sell"][1] and sto_v > CFG["sto_sell"]: sig="SELL"
            if sig:
                out.append({"pair": sym.replace("=X",""), "dir": sig, "price": f"{price:.5f}", "rsi": int(rsi_v), "sto": int(sto_v), "ratio": f"{ratio:.1f}"})
        except: continue
    return out, now

@app.route('/')
def home():
    return """
<html><head><meta name="viewport" content="width=device-width,initial-scale=1"><title>V65 LARGO TEST</title>
<style>body{background:#0a0a0a;color:white;font-family:Arial;text-align:center;padding:20px}
.btn{background:#00ff88;color:#000;border:none;padding:16px 28px;margin:10px;border-radius:14px;font-weight:bold;font-size:18px;width:85%;max-width:350px;display:block;margin:auto;cursor:pointer}
.card{background:#1a1a1a;border-radius:12px;padding:14px;margin:10px auto;max-width:380px;text-align:left;border-left:4px solid #00ff88}
</style></head><body>
<h1>🔥 V65 """ + MODE + """ TEST LARGO</h1><p style="color:#888">18 coppie | Scan 60s | Ora IT | Testiamo subito</p>
<button class="btn" id="b1" onclick="attiva()">🔇 ATTIVA SUONO</button>
<button class="btn" onclick="cerca()">🔍 SCAN ORA</button>
<p id="info">Caricamento...</p><div id="box"></div><p id="vuoto" style="color:#555">Nessuna pinbar ora - con LARGO dovrebbe trovarne subito</p>
<audio id="snd" src="https://actions.google.com/sounds/v1/alarms/beep_short.ogg" preload="auto"></audio>
<script>
let ok=false; let a=document.getElementById('snd');
function attiva(){ok=true; a.play().then(()=>a.pause()); document.getElementById('b1').innerHTML='🔔 SUONO ATTIVO';}
function cerca(){
 fetch('/api/scan').then(r=>r.json()).then(d=>{
  document.getElementById('info').innerText='Ultima: '+d.time+' - Trovate: '+d.signals.length+' - MODE '+d.mode;
  let h='';
  if(d.signals.length>0){
   if(ok){a.play(); if(navigator.vibrate) navigator.vibrate([500,200,500]); setTimeout(()=>a.pause(),3500);}
   d.signals.forEach(s=>{h+=`<div class="card"><b style="color:${s.dir=='BUY'?'#00ff88':'#ff4d4d'}">${s.dir} ${s.pair} ${s.ratio}x</b><br>RSI ${s.rsi} STO ${s.sto} | ${s.price}<br><small>${d.time}</small></div>`});
   document.getElementById('box').innerHTML=h; document.getElementById('vuoto').style.display='none';
  } else {document.getElementById('box').innerHTML=''; document.getElementById('vuoto').style.display='block';}
 });
}
setInterval(cerca,60000);
window.onload=cerca;
</script></body></html>
"""

@app.route('/api/scan')
def api():
    s,t = scan_now()
    return jsonify({"signals": s, "time": t, "mode": MODE})

if __name__ == "__main__":
    import os
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT",10000)))
