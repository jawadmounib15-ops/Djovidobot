# V85 47 - TUTTI FILTRI LARGHETTO - MIGLIORE COMPROMESSO
import yfinance as yf, pandas as pd
from flask import Flask, jsonify
from datetime import datetime
import pytz, os
from concurrent.futures import ThreadPoolExecutor, as_completed

app = Flask(__name__)

OTC_MAP = {
    "EURUSD-OTC":"EURUSD=X", "GBPUSD-OTC":"GBPUSD=X", "USDJPY-OTC":"USDJPY=X",
    "AUDUSD-OTC":"AUDUSD=X", "USDCAD-OTC":"USDCAD=X", "USDCHF-OTC":"USDCHF=X",
    "EURJPY-OTC":"EURJPY=X", "EURGBP-OTC":"EURGBP=X", "GBPJPY-OTC":"GBPJPY=X",
    "AUDJPY-OTC":"AUDJPY=X", "EURCHF-OTC":"EURCHF=X", "GBPCHF-OTC":"GBPCHF=X",
    "CADJPY-OTC":"CADJPY=X", "CHFJPY-OTC":"CHFJPY=X", "AUDCAD-OTC":"AUDCAD=X",
    "EURAUD-OTC":"EURAUD=X", "GBPAUD-OTC":"GBPAUD=X", "AUDCHF-OTC":"AUDCHF=X",
    "NZDUSD-OTC":"NZDUSD=X", "EURCAD-OTC":"EURCAD=X",
    "American Express OTC":"AXP", "Intel OTC":"INTC", "Johnson & Johnson OTC":"JNJ",
    "Marathon Digital OTC":"MARA", "Palantir OTC":"PLTR", "Tesla OTC":"TSLA",
    "Pfizer OTC":"PFE", "Citigroup OTC":"C", "Cisco OTC":"CSCO", "AMD OTC":"AMD",
    "VISA OTC":"V", "GameStop OTC":"GME", "Boeing OTC":"BA", "FACEBOOK OTC":"META",
    "FedEx OTC":"FDX", "Coinbase OTC":"COIN", "ExxonMobil OTC":"XOM",
    "Apple OTC":"AAPL", "Microsoft OTC":"MSFT", "Amazon OTC":"AMZN",
    "Brent Oil OTC":"BZ=F", "WTI Crude Oil OTC":"CL=F", "Gold OTC":"GC=F",
    "Natural Gas OTC":"NG=F", "Palladium OTC":"PA=F", "Platinum OTC":"PL=F", "Silver OTC":"SI=F"
}

def fix(df):
    if isinstance(df.columns, pd.MultiIndex): df.columns=df.columns.get_level_values(0)
    return df
def add_all(df):
    d=df['Close'].diff()
    df['RSI']=100-(100/(1+d.where(d>0,0).rolling(14).mean()/-d.where(d<0,0).rolling(14).mean()))
    df['EMA21']=df['Close'].ewm(21).mean(); df['EMA50']=df['Close'].ewm(50).mean()
    df['BB_UP']=df['Close'].rolling(20).mean() + df['Close'].rolling(20).std()*2
    df['BB_LOW']=df['Close'].rolling(20).mean() - df['Close'].rolling(20).std()*2
    df['ATR']=(df['High']-df['Low']).rolling(14).mean()
    return df
def lavoro1_trend(df):
    c=float(df.iloc[-1]['Close']); c1=float(df.iloc[-2]['Close']); ema21=float(df.iloc[-1]['EMA21']); ema50=float(df.iloc[-1]['EMA50']); rsi=float(df.iloc[-1]['RSI'])
    # LARGHETTO: 0.0012 invece di 0.0008, RSI 35-58 / 42-65
    if c>ema50 and ema21>ema50 and 35<=rsi<=58 and c>=c1 and abs(c-ema21)/c<0.0012: return "BUY"
    if c<ema50 and ema21<ema50 and 42<=rsi<=65 and c<=c1 and abs(c-ema21)/c<0.0012: return "SELL"
    return None
def lavoro2_boll(df):
    c=float(df.iloc[-1]['Close']); rsi=float(df.iloc[-1]['RSI'])
    if float(df.iloc[-2]['Low']) < float(df.iloc[-2]['BB_LOW']) and c>float(df.iloc[-1]['BB_LOW']) and 32<=rsi<=52: return "BUY"
    if float(df.iloc[-2]['High']) > float(df.iloc[-2]['BB_UP']) and c<float(df.iloc[-1]['BB_UP']) and 48<=rsi<=68: return "SELL"
    return None
def lavoro3_engulf(df):
    o=float(df.iloc[-1]['Open']); c=float(df.iloc[-1]['Close']); o1=float(df.iloc[-2]['Open']); c1=float(df.iloc[-2]['Close']); body=abs(c-o); body1=abs(c1-o1); atr=float(df.iloc[-1]['ATR'])
    # LARGHETTO: 1.5x invece di 1.8x
    if body > body1*1.5 and atr/c>0.00012:
        if c>o and c1<o1: return "BUY"
        if c<o and c1>o1: return "SELL"
    return None
def lavoro4_doppio(df):
    c=float(df.iloc[-1]['Close']); rsi=float(df.iloc[-1]['RSI']); low20=float(df.iloc[-20:]['Low'].min()); high20=float(df.iloc[-20:]['High'].max())
    # LARGHETTO: 0.1% invece di 0.05%
    if c > low20*1.001 and float(df.iloc[-10:]['Low'].min())==low20 and 35<=rsi<=55: return "BUY"
    if c < high20*0.999 and float(df.iloc[-10:]['High'].max())==high20 and 45<=rsi<=65: return "SELL"
    return None
def filtro_ultra(df, direzione):
    try:
        o=float(df.iloc[-1]['Open']); c=float(df.iloc[-1]['Close']); h=float(df.iloc[-1]['High']); l=float(df.iloc[-1]['Low']); body=abs(c-o)
        if body==0: return False
        upper_wick = h - max(o,c); lower_wick = min(o,c) - l
        # LARGHETTO: 1.5x invece di 1.2x, e 0.5 invece di 0.7
        if direzione=="BUY" and upper_wick > body*1.5: return False
        if direzione=="SELL" and lower_wick > body*1.5: return False
        if body < (upper_wick + lower_wick)*0.5: return False
        if body/c < 0.00003: return False
        return True
    except: return False
def check_otc(pair_otc, real_sym):
    try:
        df=yf.download(real_sym, period="5d", interval="1m", progress=False); df=fix(df)
        if len(df)<60: return None
        df=add_all(df); voti={"BUY":[],"SELL":[]}
        for nome, func in [("TREND",lavoro1_trend),("BOLL",lavoro2_boll),("ENGULF",lavoro3_engulf),("DOPPIO",lavoro4_doppio)]:
            r=func(df)
            if r: voti[r].append(nome)
        direzione=None
        if len(voti["BUY"])>=3: direzione="BUY"
        elif len(voti["SELL"])>=3: direzione="SELL"
        else: return None
        if not filtro_ultra(df, direzione): return None
        c=float(df.iloc[-1]['Close']); rsi=float(df.iloc[-1]['RSI'])
        fmt = f"{c:.5f}" if "-OTC" in pair_otc and len(pair_otc)<12 else f"{c:.2f}"
        return {"pair":pair_otc,"dir":direzione,"price":fmt,"note":f"80% {direzione} [{' + '.join(voti[direzione])}] RSI {rsi:.0f} | 1MIN LARGHETTO"}
    except: return None

@app.route('/')
def home():
    return """<html><head><meta name="viewport" content="width=device-width,initial-scale=1"><title>V85 LARGHETTO</title>
<style>
body{background:#0a0a0a;color:#fff;font-family:Arial;text-align:center;padding:16px}
.btn{padding:20px;border-radius:16px;font-weight:bold;font-size:20px;width:95%;max-width:400px;display:block;margin:12px auto;cursor:pointer}
.btn-green{background:#00ff88;color:#000;border:3px solid #00ff88}
.btn-dark{background:#222;color:#fff;border:2px solid #444}
.card{background:#1a1a1a;border-radius:14px;padding:14px;margin:10px auto;max-width:420px;text-align:left;border-left:6px solid #00ff88;position:relative}
.sell{border-left-color:#ff3b3b}
.badge{position:absolute;top:10px;right:10px;font-size:11px;font-weight:bold;padding:4px 8px;border-radius:6px}
.live{background:#00ff88;color:#000}.scaduto{background:#ff3b3b;color:#fff}.warn{background:#ffcc00;color:#000}
.countdown{font-weight:bold;font-size:13px;padding:8px 10px;border-radius:8px;display:inline-block;margin-top:8px;width:92%;text-align:center}
.c-ok{background:#00ff88;color:#000}.c-warn{background:#ffcc00;color:#000}.c-exp{background:#ff3b3b;color:#fff}
.prepara{background:#ffcc00;color:#000;font-weight:bold;padding:10px;border-radius:10px;margin-top:8px;text-align:center;font-size:15px;border:2px solid #fff}
.exp{background:#00ff88;color:#000;font-weight:bold;padding:8px 10px;border-radius:8px;display:inline-block;margin-top:6px;width:90%;text-align:center}
</style></head><body>
<h2>✅ V85 - LARGHETTO MIGLIORE</h2>
<p style="color:#00ff88">TUTTI FILTRI MA UN PO' PIU' LARGHI - PIU' SEGNALI</p>
<div class="btn btn-green" id="b1" onclick="attiva()" ontouchstart="attiva()">🔔 ATTIVA SUONO V85</div>
<div class="btn btn-dark" onclick="cerca()" ontouchstart="cerca()">🔍 SCAN 47 - 1 MIN LARGHETTO</div>
<p id="info">Pronto V85...</p>
<h3 style="color:#00ff88">🔥 LIVE 47 - 1 MIN</h3><div id="live"></div>
<h3 style="color:#888">📜 STORICO</h3><div id="hist"></div>
<script>
let ok=false; let history=JSON.parse(localStorage.getItem('otc_85')||'[]'); let liveSignals={}; const VALIDITA=2;
function attiva(){ok=true; document.getElementById('b1').innerHTML='✅ V85 ATTIVO - LARGHETTO'; document.getElementById('b1').style.background='#00ff88'; let a=new Audio('https://actions.google.com/sounds/v1/alarms/beep_short.ogg'); a.play().catch(()=>{}); if(Notification&&Notification.permission!='granted') Notification.requestPermission(); try{navigator.vibrate(300);}catch(e){} renderHist(); cerca();}
function suona(){if(!ok)return; let a1=new Audio('https://actions.google.com/sounds/v1/alarms/beep_short.ogg'); let a2=new Audio('https://actions.google.com/sounds/v1/alarms/alarm_clock.ogg'); a1.play(); setTimeout(()=>a2.play(),400); try{navigator.vibrate([800,200,800]);}catch(e){} if(Notification&&Notification.permission=='granted'){new Notification('🔥 V85 SEGNALE!',{body:'Segnale larghetto - entra a inizio candela'});}}
function formatTime(ts){return new Date(ts).toLocaleTimeString('it-IT',{hour:'2-digit',minute:'2-digit',second:'2-digit'});}
function getNextCandleTime(){let now=new Date(); let next=new Date(now); next.setSeconds(0,0); next.setMinutes(now.getMinutes()+1); return next;}
function renderHist(){let h='';[...history].reverse().slice(0,40).forEach(s=>{ h+=`<div style="background:#111;padding:8px;margin:5px;border-left:3px solid ${s.dir=='BUY'?'#00ff88':'#ff3b3b'};font-size:12px">${s.dir} ${s.pair} - ${s.time}</div>`;}); document.getElementById('hist').innerHTML=h;}
function aggiornaCountdown(){let now=Date.now(); document.querySelectorAll('.countdown').forEach(el=>{let scad=parseInt(el.dataset.scad); let diff=scad-now; if(diff<=0){el.textContent='⛔ SCADUTO'; el.className='countdown c-exp';} else{let sec=Math.floor(diff/1000); let m=Math.floor(sec/60); let s=sec%60; el.textContent=`⏳ ${m}:${s.toString().padStart(2,'0')} | ${el.dataset.nato} -> ${el.dataset.exp}`; el.className=m>=1?'countdown c-ok':'countdown c-warn';}}); document.querySelectorAll('.prepara').forEach(el=>{let entry=parseInt(el.dataset.entry); let diff=entry-Date.now(); if(diff<=0){el.innerHTML='🔥 ENTRA ORA! INIZIO CANDELA!'; el.style.background='#00ff88';} else{let sec=Math.ceil(diff/1000); el.innerHTML=`⏰ ENTRA TRA ${sec} SEC ALLE ${el.dataset.entrytime}`;}});}
function cerca(){document.getElementById('info').innerText='⏳ Scansione 47 larghetto...'; fetch('/api/scan').then(r=>r.json()).then(d=>{document.getElementById('info').innerText=d.time+' | 47 OTC | 1 MIN LARGHETTO | 3 voti'; let h=''; let now=Date.now(); let nextCandle=getNextCandleTime(); let entryTime=nextCandle.getTime(); let entryStr=nextCandle.toLocaleTimeString('it-IT',{hour:'2-digit',minute:'2-digit'}); let nuovi=0; d.signals.forEach(s=>{let id=s.pair+'_'+s.dir; let isNew=!liveSignals[id]; let ts=isNew?now:liveSignals[id].ts; let scadenza_ts=ts+VALIDITA*60000; if(isNew){liveSignals[id]={ts:now,scadenza_ts:scadenza_ts,entry:entryTime}; history.push({pair:s.pair,dir:s.dir,time:d.time,ts:now}); if(history.length>100) history=history.slice(-100); localStorage.setItem('otc_85',JSON.stringify(history)); nuovi++;} let expired=now>scadenza_ts; let badge=expired?'🔴 SCADUTO':'🟢 NUOVO'; let entryData=isNew?entryTime:liveSignals[id].entry; h+=`<div class="card ${s.dir=='SELL'?'sell':''}"><b style="color:${s.dir=='BUY'?'#00ff88':'#ff3b3b'}">${s.dir} ${s.pair}</b> - ${badge}<br>${s.note}<br>${s.price}<br><div class="prepara" data-entry="${entryData}" data-entrytime="${entryStr}">⏰ ENTRA ALLE ${entryStr}</div><div class="countdown" data-scad="${scadenza_ts}" data-nato="${formatTime(ts)}" data-exp="${formatTime(scadenza_ts)}">⏳...</div><br><span class="exp">TRADE 1 MINUTO</span></div>`;}); if(nuovi>0){suona(); renderHist();} document.getElementById('live').innerHTML=h||'<p style="color:#666">Nessun segnale - mercato fermo, meglio così</p>';});}
setInterval(cerca,20000); setInterval(aggiornaCountdown,1000); window.onload=()=>{renderHist();};
</script></body></html>"""

@app.route('/api/scan')
def api():
    tz=pytz.timezone('Europe/Rome'); now=datetime.now(tz).strftime('%H:%M:%S IT')
    out=[]
    with ThreadPoolExecutor(max_workers=47) as ex:
        futs={ex.submit(check_otc, otc, real): otc for otc, real in OTC_MAP.items()}
        for f in as_completed(futs):
            r=f.result()
            if r: out.append(r)
    return jsonify({"signals":out,"time":now})

if __name__=="__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT",10000)))
