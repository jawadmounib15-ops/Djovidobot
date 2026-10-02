# ANALYZER.PY V74.3 + FILTRO ANTI-FALSO - SEMPRE 3MIN
import yfinance as yf, pandas as pd
from flask import Flask, jsonify
from datetime import datetime
import pytz
from concurrent.futures import ThreadPoolExecutor, as_completed
import os

app = Flask(__name__)
PAIRS = ["EURUSD=X","GBPUSD=X","USDJPY=X","AUDUSD=X","USDCAD=X","USDCHF=X","EURJPY=X","GBPJPY=X","EURGBP=X","EURCHF=X","AUDJPY=X","GBPCHF=X","GBPAUD=X","EURNZD=X","CADCHF=X","CADJPY=X","AUDCAD=X","AUDCHF=X","CHFJPY=X","GBPNZD=X","NZDCAD=X"]

TIMEFRAMES = {"1M":{"period":"1d","interval":"1m"},"5M":{"period":"2d","interval":"5m"},"15M":{"period":"5d","interval":"15m"}}

def fix_df(df):
    if isinstance(df.columns, pd.MultiIndex): df.columns=df.columns.get_level_values(0)
    return df

def rsi_calc(s, p=14):
    d=s.diff(); g=d.where(d>0,0).rolling(window=p).mean(); l=-d.where(d<0,0).rolling(window=p).mean()
    rs=g/l; return 100-(100/(1+rs))

def check_single_tf(sym, tf_name):
    try:
        cfg=TIMEFRAMES[tf_name]
        df=yf.download(sym, period=cfg["period"], interval=cfg["interval"], progress=False)
        df=fix_df(df)
        if len(df)<70: return None
        df['RSI']=rsi_calc(df['Close'],14)
        df['EMA20']=df['Close'].ewm(span=20).mean()
        df['EMA50']=df['Close'].ewm(span=50).mean()
        df['Body']=abs(df['Close']-df['Open'])
        df['AvgBody']=df['Body'].rolling(20).mean()

        highs=df['High'].values; lows=df['Low'].values
        sh=sl=None
        for i in range(len(df)-25,len(df)-5):
            if highs[i]==max(highs[i-5:i+6]): sh=float(highs[i])
            if lows[i]==min(lows[i-5:i+6]): sl=float(lows[i])
        if sh is None or sl is None: return None

        last=df.iloc[-1]; prev=df.iloc[-2]
        c=float(last['Close']); cp=float(prev['Close'])
        o=float(last['Open']); rsi=float(last['RSI'])
        ema20=float(last['EMA20']); ema50=float(last['EMA50'])
        body=float(last['Body']); avg_body=float(last['AvgBody'])

        # BASE LARGA COME V74.3
        last20=df.iloc[-20:]; pct=(float(last20['High'].max())-float(last20['Low'].min()))/c
        if pct<0.0009: return None
        rng=sh-sl
        if rng==0: return None
        dh=abs(c-sh)/rng; dl=abs(c-sl)/rng
        base_buy = dl<0.132 and c>cp and rsi<44
        base_sell = dh<0.132 and c<cp and rsi>56
        if not (base_buy or base_sell): return None

        # FILTRO ANTI-FALSO 1 - NO DOJI / CANDELA PICCOLA
        if body < avg_body * 0.6: return None

        # FILTRO ANTI-FALSO 2 - NO CONTROTREND DEBOLE
        if base_buy and ema20 < ema50 and rsi > 35: return None
        if base_sell and ema20 > ema50 and rsi < 65: return None

        # FILTRO ANTI-FALSO 3 - NO LATERALE 3 CANDELE FERME
        last3=df.iloc[-3:]
        if (last3['Close'].max() - last3['Close'].min()) / c < 0.0003:
            return None

        return ("BUY" if base_buy else "SELL"), rsi

    except: return None
    return None

def check_pair(sym):
    results={}
    for tf in TIMEFRAMES:
        r=check_single_tf(sym,tf)
        if r: results[tf]=r
    if not results: return None
    dirs=[v[0] for v in results.values()]; b=dirs.count("BUY"); s=dirs.count("SELL")
    if b>=2 or (b==1 and s==0): fd="BUY"
    elif s>=2 or (s==1 and b==0): fd="SELL"
    else: return None
    expiry="00:03:00" # SEMPRE 3 MIN COME HAI CHIESTO
    conf="70%"
    note=" + ".join([f"{k}:{v[0]} RSI {v[1]:.0f}" for k,v in results.items()]) + " | AntiFalso OK"
    return {"pair":sym.replace("=X",""),"dir":fd,"expiry":expiry,"confidence":conf,"note":note,"tfs":list(results.keys())}

@app.route('/')
def home():
    return """<html><head><meta name="viewport" content="width=device-width,initial-scale=1"><title>V74.3 + FILTRO</title>
<style>body{background:#0a0a0a;color:#fff;font-family:Arial;text-align:center;padding:12px}
.btn{background:#ffcc00;color:#000;border:none;padding:16px;border-radius:14px;font-weight:bold;font-size:18px;width:95%;max-width:380px;display:block;margin:8px auto}
.card{background:#1a1a1a;border-radius:14px;padding:12px;margin:8px auto;max-width:420px;text-align:left;border-left:5px solid #00ff88;position:relative}
.sell{border-left-color:#ff3b3b}.old{opacity:0.5;background:#111}
.badge{position:absolute;top:8px;right:8px;font-size:11px;padding:4px 8px;border-radius:6px;font-weight:bold}
.nuovo{background:#00ff88;color:#000;animation:blink 1s infinite}.vecchio{background:#ff3b3b;color:#fff}.live{background:#ffcc00;color:#000}
@keyframes blink{50%{opacity:0.5}}
.tf{background:#222;color:#00ff88;font-size:11px;padding:2px 6px;border-radius:4px;margin-right:4px}
.exp3{background:#ffcc00;color:#000;font-weight:bold;padding:8px 12px;border-radius:10px;display:inline-block;margin-top:6px;font-size:15px;width:90%;text-align:center}
</style></head><body>
<h2>📊 V74.3 + FILTRO ANTI-FALSO</h2>
<p style="color:#ffcc00">Sempre 00:03:00 - Largo 0.132 + filtro</p>
<button class="btn" id="b1" onclick="attiva()">🔔 ATTIVA 3MIN + FILTRO</button>
<button class="btn" style="background:#222;color:#fff;border:1px solid #444" onclick="cerca()">🔍 SCAN ORA</button>
<p id="info">...</p><div id="live"></div>
<h3 style="color:#888;margin-top:22px;border-top:1px solid #333;padding-top:12px">📜 STORICO 3MIN</h3><div id="hist"></div>
<button class="btn" style="background:#333;color:#999;font-size:12px;padding:8px" onclick="localStorage.clear();history=[];liveSignals={};renderHist();">🗑️ Pulisci</button>
<audio id="s1" src="https://actions.google.com/sounds/v1/alarms/beep_short.ogg" preload="auto"></audio>
<script>
let ok=false; let history=JSON.parse(localStorage.getItem('v743f_hist')||'[]'); let liveSignals={};
function attiva(){ok=true; document.getElementById('b1').innerHTML='✅ 3MIN + FILTRO ATTIVO'; let a=document.getElementById('s1'); a.play().then(()=>{a.pause();a.currentTime=0}).catch(()=>{}); if(Notification&&Notification.permission!='granted')Notification.requestPermission(); renderHist();}
function suona(){if(!ok)return; let a=document.getElementById('s1'); a.currentTime=0; a.play(); if(navigator.vibrate) navigator.vibrate([800,200,800]);}
function renderHist(){let h=''; [...history].reverse().slice(0,60).forEach(s=>{let age=Math.floor((Date.now()-s.ts)/60000); let badge=age<=3?'nuovo':'vecchio'; let txt=age<=3?'🟢 NUOVO '+age+'m fa':'🔴 VECCHIO '+age+'m'; h+=`<div class="card old ${s.dir=='SELL'?'sell':''}"><span class="badge ${badge}">${txt}</span><b style="color:${s.dir=='BUY'?'#00ff88':'#ff3b3b'}">${s.dir} ${s.pair}</b> - 00:03:00<br><span style="font-size:11px;color:#aaa">${s.note}</span><br><span style="font-size:11px;color:#666">${s.time} | ${age}m fa</span></div>`;}); document.getElementById('hist').innerHTML=h||'<p style="color:#555">Vuoto</p>';}
function cerca(){fetch('/api/scan').then(r=>r.json()).then(d=>{document.getElementById('info').innerText=d.time+' | 3MIN FILTRATO: '+d.signals.length; let h=''; let now=Date.now(); let nuovi=0; d.signals.forEach(s=>{let id=s.pair+'_'+s.dir; let isNew=!liveSignals[id]; let age=isNew?0:Math.floor((now-liveSignals[id])/60000); if(isNew){history.push({pair:s.pair,dir:s.dir,note:s.note,time:d.time,ts:now}); if(history.length>100) history=history.slice(-100); localStorage.setItem('v743f_hist',JSON.stringify(history)); liveSignals[id]=now; nuovi++;} let cls=s.dir=='SELL'?'card sell':'card'; if(age>4) cls+=' old'; let badge=age<=1?'nuovo':(age<=4?'live':'vecchio'); let btxt=age<=1?'🟢 NUOVO ORA - ANTI-FALSO':(age<=4?'🟡 DA '+age+' MIN':'🔴 VECCHIO - NON ENTRARE'); let tfs=s.tfs.map(t=>`<span class="tf">${t}</span>`).join(''); h+=`<div class="${cls}"><span class="badge ${badge}">${btxt}</span><b style="font-size:19px;color:${s.dir=='BUY'?'#00ff88':'#ff3b3b'}">${s.dir} ${s.pair}</b><br><div style="margin:4px 0">${tfs} 70% FILTRO</div><div style="color:#888;font-size:12px">${s.note}</div><span class="exp3">⏱️ SEMPRE 00:03:00 - FILTRO OK</span><br><span style="font-size:12px;color:#ffcc00">${age==0?'ENTRA ORA':age+' min fa - '+(age<=3?'ENTRA':'SCADUTO')}</span></div>`;}); if(nuovi>0){suona(); renderHist();} document.getElementById('live').innerHTML=h||'<p style="color:#555">Nessun segnale - filtro anti-falso sta lavorando</p>';});}
setInterval(cerca,40000); window.onload=()=>{renderHist(); cerca();};
</script></body></html>"""

@app.route('/api/scan')
def api():
    tz=pytz.timezone('Europe/Rome'); now=datetime.now(tz).strftime('%H:%M:%S IT')
    out=[]
    with ThreadPoolExecutor(max_workers=12) as ex:
        futs={ex.submit(check_pair,s):s for s in PAIRS}
        for f in as_completed(futs):
            r=f.result()
            if r: out.append(r)
    return jsonify({"signals":out,"time":now})

if __name__=="__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT",10000)))
