# ANALYZER.PY V82 WEEKEND OTC - SABATO/DOMENICA
import yfinance as yf, pandas as pd
from flask import Flask, jsonify
from datetime import datetime
import pytz, os
from concurrent.futures import ThreadPoolExecutor, as_completed

app = Flask(__name__)
# 20 OTC PRINCIPALI - mappate su forex reale (OTC segue reale)
OTC_MAP = {
    "EURUSD-OTC":"EURUSD=X", "GBPUSD-OTC":"GBPUSD=X", "USDJPY-OTC":"USDJPY=X",
    "AUDUSD-OTC":"AUDUSD=X", "USDCAD-OTC":"USDCAD=X", "USDCHF-OTC":"USDCHF=X",
    "EURJPY-OTC":"EURJPY=X", "EURGBP-OTC":"EURGBP=X", "GBPJPY-OTC":"GBPJPY=X",
    "AUDJPY-OTC":"AUDJPY=X", "EURCHF-OTC":"EURCHF=X", "GBPCHF-OTC":"GBPCHF=X",
    "CADJPY-OTC":"CADJPY=X", "CHFJPY-OTC":"CHFJPY=X", "AUDCAD-OTC":"AUDCAD=X",
    "EURAUD-OTC":"EURAUD=X", "GBPAUD-OTC":"GBPAUD=X", "AUDCHF-OTC":"AUDCHF=X",
    "NZDUSD-OTC":"NZDUSD=X", "EURCAD-OTC":"EURCAD=X"
}

def fix(df):
    if isinstance(df.columns, pd.MultiIndex): df.columns=df.columns.get_level_values(0)
    return df

def add_all(df):
    d=df['Close'].diff()
    df['RSI']=100-(100/(1+d.where(d>0,0).rolling(14).mean()/-d.where(d<0,0).rolling(14).mean()))
    df['EMA21']=df['Close'].ewm(21).mean()
    df['EMA50']=df['Close'].ewm(50).mean()
    df['BB_UP']=df['Close'].rolling(20).mean() + df['Close'].rolling(20).std()*2
    df['BB_LOW']=df['Close'].rolling(20).mean() - df['Close'].rolling(20).std()*2
    df['ATR']=(df['High']-df['Low']).rolling(14).mean()
    return df

# LAVORI LARGHI PER OTC - più volatile
def lavoro1_trend(df):
    c=float(df.iloc[-1]['Close']); c1=float(df.iloc[-2]['Close'])
    ema21=float(df.iloc[-1]['EMA21']); ema50=float(df.iloc[-1]['EMA50']); rsi=float(df.iloc[-1]['RSI'])
    if c>ema50 and ema21>ema50 and 30<=rsi<=68 and c>=c1: return "BUY"
    if c<ema50 and ema21<ema50 and 32<=rsi<=70 and c<=c1: return "SELL"
    return None

def lavoro2_boll(df):
    c=float(df.iloc[-1]['Close']); bb_up=float(df.iloc[-1]['BB_UP']); bb_low=float(df.iloc[-1]['BB_LOW']); rsi=float(df.iloc[-1]['RSI'])
    if float(df.iloc[-2]['Low']) < float(df.iloc[-2]['BB_LOW']) and c>bb_low and 25<=rsi<=55: return "BUY"
    if float(df.iloc[-2]['High']) > float(df.iloc[-2]['BB_UP']) and c<bb_up and 45<=rsi<=75: return "SELL"
    return None

def lavoro3_engulf(df):
    o=float(df.iloc[-1]['Open']); c=float(df.iloc[-1]['Close']); o1=float(df.iloc[-2]['Open']); c1=float(df.iloc[-2]['Close'])
    body=abs(c-o); body1=abs(c1-o1)
    if body > body1*1.15:
        if c>o and c1<o1: return "BUY"
        if c<o and c1>o1: return "SELL"
    return None

def check_otc(pair_otc, real_sym):
    try:
        df=yf.download(real_sym, period="5d", interval="5m", progress=False) # 5d per prendere venerdì
        df=fix(df)
        if len(df)<50: return None
        df=add_all(df)
        voti=[]
        for f in [lavoro1_trend, lavoro2_boll, lavoro3_engulf]:
            r=f(df)
            if r: voti.append(r)
        # OTC largo - basta 1
        if voti.count("BUY")>=2 and voti.count("BUY")>=voti.count("SELL"):
            c=float(df.iloc[-1]['Close']); return {"pair":pair_otc,"dir":"BUY","price":f"{c:.5f}","note":f"OTC BUY RSI {float(df.iloc[-1]['RSI']):.0f}"}
        if voti.count("SELL")>=2 and voti.count("SELL")>=voti.count("BUY"):
            c=float(df.iloc[-1]['Close']); return {"pair":pair_otc,"dir":"SELL","price":f"{c:.5f}","note":f"OTC SELL RSI {float(df.iloc[-1]['RSI']):.0f}"}
    except: return None

@app.route('/')
def home():
    return """<html><head><meta name="viewport" content="width=device-width,initial-scale=1"><title>V82 OTC WEEKEND</title>
<style>body{background:#0a0a0a;color:#fff;font-family:Arial;text-align:center;padding:16px}
.btn{background:#ffcc00;color:#000;border:none;padding:16px;border-radius:14px;font-weight:bold;font-size:19px;width:95%;max-width:400px;display:block;margin:10px auto}
.card{background:#1a1a1a;border-radius:14px;padding:14px;margin:10px auto;max-width:420px;text-align:left;border-left:6px solid #ffcc00;position:relative}
.sell{border-left-color:#ff3b3b}.old{opacity:0.5}
.badge{position:absolute;top:10px;right:10px;background:#ffcc00;color:#000;font-size:11px;font-weight:bold;padding:4px 8px;border-radius:6px}
.exp{background:#ffcc00;color:#000;font-weight:bold;padding:5px 9px;border-radius:8px;display:inline-block;margin-top:6px}
</style></head><body>
<h2>🔥 V82 OTC WEEKEND</h2>
<p style="color:#ffcc00">20 coppie OTC - Sab/Dom<br><small>EURUSD-OTC, GBPUSD-OTC, ecc</small></p>
<button class="btn" id="b1" onclick="attiva()">🔔 ATTIVA ALLARME</button>
<button class="btn" style="background:#222;color:#fff;border:1px solid #444" onclick="cerca()">🔍 SCAN 20 OTC</button>
<p id="info">...</p><div id="live"></div><hr style="border-top:1px solid #333;margin:18px 0">
<h3 style="color:#888">📜 STORICO OTC</h3><div id="hist"></div>
<button class="btn" style="background:#333;color:#999;font-size:14px" onclick="localStorage.clear();history=[];renderHist();">🗑️ Pulisci</button>
<audio id="s1" src="https://actions.google.com/sounds/v1/alarms/beep_short.ogg"></audio>
<audio id="s2" src="https://actions.google.com/sounds/v1/alarms/alarm_clock.ogg"></audio>
<script>
let ok=false,a1=document.getElementById('s1'),a2=document.getElementById('s2'),history=JSON.parse(localStorage.getItem('otcweekend')||'[]');
function attiva(){ok=true;a1.play().then(()=>{a1.pause();a1.currentTime=0}).catch(()=>{});a2.play().then(()=>{a2.pause();a2.currentTime=0}).catch(()=>{});document.getElementById('b1').innerHTML='✅ ALLARME OTC ATTIVO';if(Notification&&Notification.permission!='granted')Notification.requestPermission();renderHist();}
function suona(){if(!ok)return;a1.currentTime=0;a1.play();setTimeout(()=>{a2.currentTime=0;a2.play()},400);if(navigator.vibrate)navigator.vibrate([800,200,800]);if(Notification&&Notification.permission=='granted')new Notification('🔥 SEGNALE OTC!',{body:'ENTRA 00:05:00'});}
function renderHist(){let h='';[...history].reverse().forEach(s=>{h+=`<div class="card old ${s.dir=='SELL'?'sell':''}"><span class="badge" style="background:#555;color:#fff">${s.time}</span><b style="color:${s.dir=='BUY'?'#ffcc00':'#ff3b3b'}">${s.dir} ${s.pair}</b><br>${s.note}<br>${s.price}</div>`});document.getElementById('hist').innerHTML=h||'<p style="color:#555">Vuoto</p>';}
function cerca(){fetch('/api/scan').then(r=>r.json()).then(d=>{document.getElementById('info').innerText=d.time+' | OTC: '+d.signals.length+' / 20';let h='';let nuovi=0;d.signals.forEach(s=>{let id=s.pair+s.dir+s.price;if(!history.find(x=>x.id==id)){history.push({id:id,pair:s.pair,dir:s.dir,price:s.price,note:s.note,time:d.time});nuovi++;}h+=`<div class="card ${s.dir=='SELL'?'sell':''}"><span class="badge">OTC LIVE</span><b style="font-size:19px;color:${s.dir=='BUY'?'#ffcc00':'#ff3b3b'}">${s.dir} ${s.pair}</b><br>${s.note}<br>${s.price}<br><span class="exp">⏱️ ENTRA 00:05:00</span></div>`});if(nuovi>0){localStorage.setItem('otcweekend',JSON.stringify(history.slice(-50)));suona();renderHist();}document.getElementById('live').innerHTML=h||'<p style="color:#666">Nessun OTC ora - mercato chiuso, uso dati venerdì</p>';});}
setInterval(cerca,60000);window.onload=()=>{renderHist();cerca();}
</script></body></html>"""

@app.route('/api/scan')
def api():
    tz=pytz.timezone('Europe/Rome'); now=datetime.now(tz).strftime('%H:%M:%S IT WEEKEND')
    out=[]
    with ThreadPoolExecutor(max_workers=20) as ex:
        futs={ex.submit(check_otc, otc, real): otc for otc, real in OTC_MAP.items()}
        for f in as_completed(futs):
            r=f.result()
            if r: out.append(r)
    return jsonify({"signals":out,"time":now})

if __name__=="__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT",10000)))
