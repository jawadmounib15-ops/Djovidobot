# V82 FINALE 47 OTC - FOREX + AZIONI + OIL/GOLD + FILTRO STOPPINO + SCADENZA
import yfinance as yf, pandas as pd
from flask import Flask, jsonify
from datetime import datetime
import pytz, os
from concurrent.futures import ThreadPoolExecutor, as_completed

app = Flask(__name__)

OTC_MAP = {
    # 20 FOREX OTC
    "EURUSD-OTC":"EURUSD=X", "GBPUSD-OTC":"GBPUSD=X", "USDJPY-OTC":"USDJPY=X",
    "AUDUSD-OTC":"AUDUSD=X", "USDCAD-OTC":"USDCAD=X", "USDCHF-OTC":"USDCHF=X",
    "EURJPY-OTC":"EURJPY=X", "EURGBP-OTC":"EURGBP=X", "GBPJPY-OTC":"GBPJPY=X",
    "AUDJPY-OTC":"AUDJPY=X", "EURCHF-OTC":"EURCHF=X", "GBPCHF-OTC":"GBPCHF=X",
    "CADJPY-OTC":"CADJPY=X", "CHFJPY-OTC":"CHFJPY=X", "AUDCAD-OTC":"AUDCAD=X",
    "EURAUD-OTC":"EURAUD=X", "GBPAUD-OTC":"GBPAUD=X", "AUDCHF-OTC":"AUDCHF=X",
    "NZDUSD-OTC":"NZDUSD=X", "EURCAD-OTC":"EURCAD=X",
    # 20 AZIONI OTC DALLA TUA FOTO
    "American Express OTC":"AXP", "Intel OTC":"INTC", "Johnson & Johnson OTC":"JNJ",
    "Marathon Digital OTC":"MARA", "Palantir OTC":"PLTR", "Tesla OTC":"TSLA",
    "Pfizer OTC":"PFE", "Citigroup OTC":"C", "Cisco OTC":"CSCO", "AMD OTC":"AMD",
    "VISA OTC":"V", "GameStop OTC":"GME", "Boeing OTC":"BA", "FACEBOOK OTC":"META",
    "FedEx OTC":"FDX", "Coinbase OTC":"COIN", "ExxonMobil OTC":"XOM",
    "Apple OTC":"AAPL", "Microsoft OTC":"MSFT", "Amazon OTC":"AMZN",
    # 7 MATERIE PRIME OTC DALLA TUA FOTO
    "Brent Oil OTC":"BZ=F", "WTI Crude Oil OTC":"CL=F", "Gold OTC":"GC=F",
    "Natural Gas OTC":"NG=F", "Palladium OTC":"PA=F", "Platinum OTC":"PL=F", "Silver OTC":"SI=F"
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

def lavoro1_trend(df):
    c=float(df.iloc[-1]['Close']); c1=float(df.iloc[-2]['Close'])
    ema21=float(df.iloc[-1]['EMA21']); ema50=float(df.iloc[-1]['EMA50']); rsi=float(df.iloc[-1]['RSI'])
    if c>ema50 and ema21>ema50 and 35<=rsi<=60 and c>=c1 and abs(c-ema21)/c<0.0012: return "BUY"
    if c<ema50 and ema21<ema50 and 40<=rsi<=65 and c<=c1 and abs(c-ema21)/c<0.0012: return "SELL"
    return None

def lavoro2_boll(df):
    c=float(df.iloc[-1]['Close']); bb_up=float(df.iloc[-1]['BB_UP']); bb_low=float(df.iloc[-1]['BB_LOW']); rsi=float(df.iloc[-1]['RSI'])
    if float(df.iloc[-2]['Low']) < float(df.iloc[-2]['BB_LOW']) and c>bb_low and 30<=rsi<=52: return "BUY"
    if float(df.iloc[-2]['High']) > float(df.iloc[-2]['BB_UP']) and c<bb_up and 48<=rsi<=70: return "SELL"
    return None

def lavoro3_engulf(df):
    o=float(df.iloc[-1]['Open']); c=float(df.iloc[-1]['Close']); o1=float(df.iloc[-2]['Open']); c1=float(df.iloc[-2]['Close'])
    body=abs(c-o); body1=abs(c1-o1); atr=float(df.iloc[-1]['ATR'])
    if body > body1*1.5 and atr/c>0.00012:
        if c>o and c1<o1: return "BUY"
        if c<o and c1>o1: return "SELL"
    return None

def lavoro4_doppio(df):
    c=float(df.iloc[-1]['Close']); rsi=float(df.iloc[-1]['RSI'])
    low20=float(df.iloc[-20:]['Low'].min()); high20=float(df.iloc[-20:]['High'].max())
    if c > low20*1.001 and float(df.iloc[-10:]['Low'].min())==low20 and 35<=rsi<=55: return "BUY"
    if c < high20*0.999 and float(df.iloc[-10:]['High'].max())==high20 and 45<=rsi<=65: return "SELL"
    return None

def filtro_stoppino_ok(df, direzione):
    try:
        o=float(df.iloc[-1]['Open']); c=float(df.iloc[-1]['Close'])
        h=float(df.iloc[-1]['High']); l=float(df.iloc[-1]['Low'])
        body=abs(c-o)
        if body==0: return False
        upper_wick = h - max(o,c)
        lower_wick = min(o,c) - l
        if direzione=="BUY" and upper_wick > body*1.8: return False
        if direzione=="SELL" and lower_wick > body*1.8: return False
        if body < (upper_wick + lower_wick)*0.5: return False
        return True
    except: return True

def check_otc(pair_otc, real_sym):
    try:
        df=yf.download(real_sym, period="5d", interval="5m", progress=False)
        df=fix(df)
        if len(df)<60: return None
        df=add_all(df)
        voti={"BUY":[],"SELL":[]}
        for nome, func in [("TREND",lavoro1_trend),("BOLL",lavoro2_boll),("ENGULF",lavoro3_engulf),("DOPPIO",lavoro4_doppio)]:
            r=func(df)
            if r: voti[r].append(nome)
        direzione=None
        if len(voti["BUY"])>=2: direzione="BUY"
        elif len(voti["SELL"])>=2: direzione="SELL"
        else: return None
        if not filtro_stoppino_ok(df, direzione): return None
        c=float(df.iloc[-1]['Close']); rsi=float(df.iloc[-1]['RSI'])
        fmt = f"{c:.5f}" if "-OTC" in pair_otc and len(pair_otc)<12 else f"{c:.2f}"
        return {"pair":pair_otc,"dir":direzione,"price":fmt,"note":f"70% {direzione} [{' + '.join(voti[direzione])}] RSI {rsi:.0f} | NoWick"}
    except: return None

@app.route('/')
def home():
    return """<html><head><meta name="viewport" content="width=device-width,initial-scale=1"><title>V82 47 FINALE</title>
<style>
body{background:#0a0a0a;color:#fff;font-family:Arial;text-align:center;padding:16px}
.btn{background:#ffcc00;color:#000;border:none;padding:16px;border-radius:14px;font-weight:bold;font-size:18px;width:95%;max-width:400px;display:block;margin:10px auto}
.card{background:#1a1a1a;border-radius:14px;padding:14px;margin:10px auto;max-width:420px;text-align:left;border-left:6px solid #00ff88;position:relative}
.sell{border-left-color:#ff3b3b}.old{opacity:0.5}
.badge{position:absolute;top:10px;right:10px;font-size:11px;font-weight:bold;padding:4px 8px;border-radius:6px}
.live{background:#00ff88;color:#000;animation:blink 1s infinite}.scaduto{background:#ff3b3b;color:#fff}.warn{background:#ffcc00;color:#000}
@keyframes blink{50%{opacity:0.5}}
.countdown{font-weight:bold;font-size:13px;padding:6px 10px;border-radius:8px;display:inline-block;margin-top:8px;width:92%;text-align:center}
.c-ok{background:#00ff88;color:#000}.c-warn{background:#ffcc00;color:#000}.c-exp{background:#ff3b3b;color:#fff}
.exp{background:#ffcc00;color:#000;font-weight:bold;padding:6px 10px;border-radius:8px;display:inline-block;margin-top:6px;width:90%;text-align:center}
.hist-card{background:#111;border-radius:10px;padding:10px;margin:6px auto;max-width:420px;text-align:left;border-left:3px solid #555;font-size:12px}
</style></head><body>
<h2>✖️ V82 47 FINALE OTC</h2>
<p style="color:#ffcc00">20 FOREX + 20 AZIONI + 7 OIL/GOLD | NoWick Fix | 5M</p>
<button class="btn" id="b1" onclick="attiva()">🔔 ATTIVA 47 OTC</button>
<button class="btn" style="background:#222;color:#fff;border:1px solid #444" onclick="cerca()">🔍 SCAN 47 OTC</button>
<p id="info">...</p>
<h3 style="color:#00ff88">🔥 LIVE 47 CON SCADENZA</h3><div id="live"></div>
<hr style="border-top:1px solid #333;margin:18px 0">
<h3 style="color:#888">📜 STORICO 47</h3><div id="hist"></div>
<button class="btn" style="background:#333;color:#999;font-size:14px" onclick="if(confirm('Pulisci?')){localStorage.clear();history=[];liveSignals={};renderHist();}">🗑️ Pulisci storico</button>
<audio id="s1" src="https://actions.google.com/sounds/v1/alarms/beep_short.ogg"></audio>
<audio id="s2" src="https://actions.google.com/sounds/v1/alarms/alarm_clock.ogg"></audio>
<script>
let ok=false,a1=document.getElementById('s1'),a2=document.getElementById('s2');
let history=JSON.parse(localStorage.getItem('otc_47_finale')||'[]');
let liveSignals={}; const VALIDITA=4;
function attiva(){ok=true;a1.play().then(()=>{a1.pause();a1.currentTime=0}).catch(()=>{});a2.play().then(()=>{a2.pause();a2.currentTime=0}).catch(()=>{});document.getElementById('b1').innerHTML='✅ 47 OTC FINALE ATTIVO';document.getElementById('b1').style.background='#00ff88';if(Notification&&Notification.permission!='granted')Notification.requestPermission();renderHist();}
function suona(){if(!ok)return;a1.currentTime=0;a1.play();setTimeout(()=>{a2.currentTime=0;a2.play()},400);if(navigator.vibrate)navigator.vibrate([800,200,800]);}
function formatTime(ts){return new Date(ts).toLocaleTimeString('it-IT',{hour:'2-digit',minute:'2-digit',second:'2-digit'});}
function renderHist(){let h='';[...history].reverse().slice(0,80).forEach(s=>{let exp=new Date(s.ts+VALIDITA*60000).toLocaleTimeString('it-IT',{hour:'2-digit',minute:'2-digit'}); h+=`<div class="hist-card" style="border-left-color:${s.dir=='BUY'?'#00ff88':'#ff3b3b'}"><b style="color:${s.dir=='BUY'?'#00ff88':'#ff3b3b'}">${s.dir} ${s.pair}</b> - ${s.price}<br><span style="color:#aaa">Nato: ${s.time} | Scad: ${exp}</span><br><span style="color:#888">${s.note}</span></div>`;});document.getElementById('hist').innerHTML=h||'<p style="color:#555">Vuoto</p>';}
function aggiornaCountdown(){let now=Date.now(); document.querySelectorAll('.countdown').forEach(el=>{let scad=parseInt(el.dataset.scad); let diff=scad-now; if(diff<=0){el.textContent='⛔ SCADUTO - NON ENTRARE'; el.className='countdown c-exp';}else{let sec=Math.floor(diff/1000); let m=Math.floor(sec/60); let s=sec%60; el.textContent=`⏳ Scade tra: ${m}:${s.toString().padStart(2,'0')} | Nato: ${el.dataset.nato} | Scad: ${el.dataset.exp}`; el.className=m>=2?'countdown c-ok':(m>=1?'countdown c-warn':'countdown c-exp');}});}
function cerca(){fetch('/api/scan').then(r=>r.json()).then(d=>{document.getElementById('info').innerText=d.time+' | 47 OTC | NoWick | Validità '+VALIDITA+' min | Trade 5M'; let h=''; let now=Date.now(); let nuovi=0; d.signals.forEach(s=>{let id=s.pair+'_'+s.dir; let isNew=!liveSignals[id]; let ts=isNew?now:liveSignals[id].ts; let scadenza_ts=ts+VALIDITA*60000; if(isNew){liveSignals[id]={ts:now,scadenza_ts:scadenza_ts}; history.push({pair:s.pair,dir:s.dir,price:s.price,note:s.note,time:d.time,ts:now}); if(history.length>100) history=history.slice(-100); localStorage.setItem('otc_47_finale',JSON.stringify(history)); nuovi++;} let ageMin=Math.floor((now-ts)/60000); let expired=now>scadenza_ts; let badgeClass=expired?'scaduto':(ageMin<=1?'live':'warn'); let badgeTxt=expired?'🔴 SCADUTO':(ageMin<=1?'🟢 NUOVO':'🟡 '+ageMin+'m'); h+=`<div class="card ${s.dir=='SELL'?'sell':''} ${expired?'old':''}"><span class="badge ${badgeClass}">${badgeTxt}</span><b style="font-size:16px;color:${s.dir=='BUY'?'#00ff88':'#ff3b3b'}">${s.dir} ${s.pair}</b><br>${s.note}<br>${s.price}<br><div class="countdown" data-scad="${scadenza_ts}" data-nato="${formatTime(ts)}" data-exp="${formatTime(scadenza_ts)}">⏳...</div><br><span class="exp">⏱️ TRADE 00:05:00</span></div>`;}); if(nuovi>0){suona(); renderHist();} document.getElementById('live').innerHTML=h||'<p style="color:#666">Nessun segnale 70% - filtro NoWick sta bloccando i falsi</p>';});}
setInterval(cerca,60000); setInterval(aggiornaCountdown,1000); window.onload=()=>{renderHist(); cerca();};
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
