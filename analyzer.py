# Analyzer.py - V7.1 OTC 1.9x FILTRATA 80% + FIX PREZZO
import os, time, threading, random
from flask import Flask, render_template_string, jsonify
import yfinance as yf
import pandas as pd
from curl_cffi import requests as cffi_requests
import requests as req
from datetime import datetime, timedelta

TOKEN = os.getenv("TELEGRAM_TOKEN", os.getenv("TOKEN", "")).strip()
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", os.getenv("CHAT_ID", "")).strip()

OTC_PAIRS = ["EURUSD=X","GBPUSD=X","USDJPY=X","AUDUSD=X","USDCAD=X","EURJPY=X","GBPJPY=X","AUDJPY=X","EURGBP=X","EURCHF=X","GBPCHF=X","CADJPY=X","AUDCAD=X","GBPAUD=X"]

app = Flask(__name__)
_YF_SESSION = cffi_requests.Session(impersonate="chrome")
signals_log = []
last_scan = {"time":"Avvio V7.1 1.9x filtrata...","found":0,"win_est":"--"}

HTML = """
<!DOCTYPE html><html><head><title>OTC 1.9x 80% V7.1</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>
body{background:#0f172a;color:#e2e8f0;font-family:Arial;padding:12px}
.card{background:#1e293b;padding:12px;border-radius:12px;margin:8px 0;border-left:5px solid #f59e0b}
.buy{border-left-color:#22c55e}.sell{border-left-color:#ef4444}
.badge{padding:4px 10px;border-radius:6px;font-weight:bold}
.b-buy{background:#22c55e;color:#000}.b-sell{background:#ef4444;color:#fff}
.timer{color:#facc15;font-weight:bold;font-size:18px}
button{padding:12px;border-radius:10px;color:white;border:none;font-weight:bold;width:100%;margin:5px 0}
.btn-scan{background:#3b82f6}.btn-test{background:#22c55e}
.small{color:#94a3b8;font-size:11px}
table{width:100%;border-collapse:collapse;font-size:11px} th,td{padding:6px;border-bottom:1px solid #334155}
</style></head><body>
<h2>🔶 V7.1 OTC 1.9x FILTRATA 80%</h2>
<div class="card">⏰ {{last.time}} | OTC Trovati: {{last.found}} | Totale: {{logs|length}} | Win: {{last.win_est}}<br><span class="small">Filtri: Swing 10 + EMA rimbalzo + RSI + E200</span></div>
<div class="card">
<button class="btn-scan" onclick="scanNow()">🔍 SCANNA OTC FILTRATA</button>
<button class="btn-test" onclick="testSound()">🔊 TEST SUONO</button>
</div>
<div class="card"><h3>🔴 LIVE 6 Min</h3><div id="live">In attesa pinbar 1.9x filtrata...</div></div>
<div class="card"><h3>📜 STORICO OTC</h3>
<table><tr><th>Ora</th><th>Segnale</th><th>Prezzo</th><th>Motivo</th></tr>
{% for s in logs[::-1][:60] %}
<tr><td>{{s.time}}</td><td><span class="badge {{'b-buy' if s.signal=='BUY' else 'b-sell'}}">{{s.signal}} {{s.symbol}}</span></td><td>{{s.price}}</td><td>{{s.reason}}</td></tr>
{% endfor %}</table>
</div>
<script>
let signals = {{logs|tojson}};
function playSound(){
  try{
    const ctx = new (window.AudioContext||window.webkitAudioContext)();
    const o = ctx.createOscillator(); const g = ctx.createGain();
    o.frequency.value=1000; o.connect(g); g.connect(ctx.destination);
    g.gain.setValueAtTime(1, ctx.currentTime); o.start();
    setTimeout(()=>{o.stop(); ctx.close()}, 800);
  }catch(e){}
}
function testSound(){ playSound(); fetch('/test_signal').then(()=>location.reload()); }
function scanNow(){ fetch('/scan_now').then(r=>r.json()).then(d=>{ if(d.length>0) playSound(); location.reload(); }); }
function renderLive(){
  const now=Date.now(); let html='';
  signals.slice(-10).reverse().forEach(s=>{
    const diff=Math.floor((s.expire_ts*1000-now)/1000);
    if(diff>0){
      const m=Math.floor(diff/60); const sec=diff%60;
      html+=`<div class="card ${s.signal=='BUY'?'buy':'sell'}"><span class="badge ${s.signal=='BUY'?'b-buy':'b-sell'}">${s.signal} ${s.symbol}</span> ${s.price} <span class="timer">00:0${m}:${sec<10?'0':''}${sec}</span><br><span class="small">${s.reason} scade ${s.expire_str}</span></div>`;
    }
  });
  if(html=='') html='<span class="small">Nessun live - aspetto solo pinbar con 3 filtri ok per 80%</span>';
  document.getElementById('live').innerHTML=html;
}
setInterval(()=>{ fetch('/api/signals').then(r=>r.json()).then(data=>{ if(data.length>signals.length){ playSound(); signals=data; renderLive(); } }); },4000);
setInterval(renderLive,1000);
renderLive();
</script></body></html>
"""

def fix_df(df):
    if isinstance(df.columns, pd.MultiIndex): df.columns=df.columns.get_level_values(0)
    return df
def rsi(s,p=14):
    d=s.diff(); g=d.where(d>0,0).rolling(p).mean(); l=-d.where(d<0,0).rolling(p).mean()
    return 100-(100/(1+g/l))
def send(msg):
    if not TOKEN or not CHAT_ID: return
    try: req.get(f"https://api.telegram.org/bot{TOKEN}/sendMessage", params={"chat_id":CHAT_ID,"text":msg}, timeout=8)
    except: pass

def analyze_filtered(symbol):
    try:
        base = symbol
        display = symbol.replace("=X","") + " OTC"
        df = fix_df(yf.Ticker(base, session=_YF_SESSION).history(period="5d", interval="1m"))
        if len(df) < 210: return None
        df['e20']=df['Close'].ewm(span=20).mean()
        df['e50']=df['Close'].ewm(span=50).mean()
        df['e200']=df['Close'].ewm(span=200).mean()
        df['rsi']=rsi(df['Close'])
        last=df.iloc[-1]; prev=df.iloc[-2]
        o=float(last['Open']); h=float(last['High']); l=float(last['Low']); cc=float(last['Close'])
        e20=float(last['e20']); e50=float(last['e50']); e200=float(last['e200']); rsi_v=float(last['rsi'])
        body=abs(cc-o); rng=h-l
        if rng<0.00001 or body==0: return None
        upper=h-max(o,cc); lower=min(o,cc)-l
        is_green=cc>o; is_red=not is_green
        # fix prezzo EURUSD 91 bug
        if "JPY" not in display and cc>50: return None
        if "JPY" in display and cc<50: return None

        pin_bull = lower > body*1.9 and body < rng*0.38 and upper < body*0.55 and is_green
        pin_bear = upper > body*1.9 and body < rng*0.38 and lower < body*0.55 and is_red
        if not (pin_bull or pin_bear): return None

        swing_high = h >= float(df['High'].iloc[-11:-1].max())
        swing_low = l <= float(df['Low'].iloc[-11:-1].min())
        if not (swing_high or swing_low): return None

        ema_touch_buy = abs(l - e20)/cc < 0.0012 or abs(l - e50)/cc < 0.0018
        ema_touch_sell = abs(h - e20)/cc < 0.0012 or abs(h - e50)/cc < 0.0018

        signal=None; reason=""
        if pin_bull and swing_low and ema_touch_buy and 28 <= rsi_v <= 48 and cc > e200:
            signal="BUY"; reason=f"1.9x {round(lower/body,1)}x + SwingLow + EMA + RSI{int(rsi_v)}"
        elif pin_bear and swing_high and ema_touch_sell and 52 <= rsi_v <= 72 and cc < e200:
            signal="SELL"; reason=f"1.9x {round(upper/body,1)}x + SwingHigh + EMA + RSI{int(rsi_v)}"
        else: return None

        return {"symbol":display,"signal":signal,"price":round(cc,5),"reason":reason,"time":datetime.now().strftime("%H:%M:%S"),"expire_ts":time.time()+360,"expire_str":(datetime.now()+timedelta(minutes=6)).strftime("%H:%M:%S")}
    except: return None

def scan_loop():
    global last_scan
    time.sleep(6)
    while True:
        found=0
        for sym in OTC_PAIRS:
            r=analyze_filtered(sym)
            if r:
                if not any(x['symbol']==r['symbol'] and time.time()-x['expire_ts']<400 for x in signals_log[-20:]):
                    signals_log.append(r)
                    if len(signals_log)>200: signals_log.pop(0)
                    send(f"🎯 {r['signal']} {r['symbol']} {r['price']}\n{r['reason']}")
                    found+=1
        last_scan={"time":datetime.now().strftime("%H:%M:%S"),"found":found,"win_est":"70-75% target"}
        time.sleep(45)

@app.route('/')
def home(): return render_template_string(HTML, logs=signals_log, last=last_scan)
@app.route('/scan_now')
def scan_now():
    res=[]
    for sym in OTC_PAIRS:
        r=analyze_filtered(sym)
        if r: res.append(r); signals_log.append(r)
    return jsonify(res)
@app.route('/test_signal')
def test_signal():
    fake={"symbol":random.choice(["EURUSD OTC","GBPJPY OTC","USDJPY OTC"]),"signal":random.choice(["BUY","SELL"]),"price":round(random.uniform(1.05,1.35) if random.random()>0.5 else random.uniform(140,155),5),"reason":"TEST V7.1 1.9x FILTRATA","time":datetime.now().strftime("%H:%M:%S"),"expire_ts":time.time()+360,"expire_str":(datetime.now()+timedelta(minutes=6)).strftime("%H:%M:%S")}
    signals_log.append(fake)
    return jsonify(fake)
@app.route('/api/signals')
def api(): return jsonify(signals_log)

threading.Thread(target=scan_loop, daemon=True).start()
if __name__=="__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT",10000)))
