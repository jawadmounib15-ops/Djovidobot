# Analyzer.py - OTC ONLY + PINBAR PULITA 1.9x
import os, time, threading, random
from flask import Flask, render_template_string, jsonify
import yfinance as yf
import pandas as pd
from curl_cffi import requests as cffi_requests
import requests as req
from datetime import datetime, timedelta

TOKEN = os.getenv("TELEGRAM_TOKEN", os.getenv("TOKEN", "")).strip()
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", os.getenv("CHAT_ID", "")).strip()

# OTC - Quotex style - usiamo i normali ma li marchiamo OTC
OTC_PAIRS = [
    "EURUSD=X","GBPUSD=X","USDJPY=X","AUDUSD=X","USDCAD=X",
    "EURJPY=X","GBPJPY=X","AUDJPY=X","EURGBP=X","GBPCHF=X",
    "EURCHF=X","AUDCAD=X","CADJPY=X","CHFJPY=X","GBPAUD=X",
    "AUDCHF=X","CADCHF=X","NZDUSD=X","NZDCAD=X","USDCHF=X"
]

app = Flask(__name__)
_YF_SESSION = cffi_requests.Session(impersonate="chrome")
signals_log = []
last_scan = {"time":"Avvio OTC 1.9x...","found":0}

HTML = """
<!DOCTYPE html><html><head><title>OTC Analyzer 1.9x</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>
body{background:#0f172a;color:#e2e8f0;font-family:Arial;padding:12px}
.card{background:#1e293b;padding:12px;border-radius:12px;margin:8px 0;border-left:5px solid #f59e0b}
.buy{border-left-color:#22c55e}.sell{border-left-color:#ef4444}
.badge{padding:4px 10px;border-radius:6px;font-weight:bold}
.b-buy{background:#22c55e;color:#000}.b-sell{background:#ef4444;color:#fff}
.timer{color:#facc15;font-weight:bold;font-size:18px}
button{padding:12px;border-radius:10px;color:white;border:none;font-weight:bold;width:100%;margin:5px 0}
.btn-scan{background:#3b82f6}.btn-test{background:#f59e0b;color:#000}
.small{color:#94a3b8;font-size:11px}
table{width:100%;border-collapse:collapse;font-size:11px} th,td{padding:6px;border-bottom:1px solid #334155}
</style></head><body>
<h2>🔶 Analyzer OTC ONLY - 1.9x PULITA</h2>
<div class="card">⏰ {{last.time}} | OTC Trovati: {{last.found}} | Totale: {{logs|length}}</div>
<div class="card">
<button class="btn-scan" onclick="scanNow()">🔍 SCANNA OTC ORA</button>
<button class="btn-test" onclick="testSound()">🔊 TEST SUONO OTC</button>
</div>
<div class="card"><h3>🔴 LIVE 6 Min OTC</h3><div id="live">In attesa pinbar 1.9x OTC...</div></div>
<div class="card"><h3>📜 STORICO OTC</h3>
<table><tr><th>Ora</th><th>Segnale</th><th>Prezzo</th><th>Motivo</th></tr>
{% for s in logs[::-1][:60] %}
<tr><td>{{s.time}}</td><td><span class="badge {{'b-buy' if s.signal=='BUY' else 'b-sell'}}">{{s.signal}} {{s.symbol}} OTC</span></td><td>{{s.price}}</td><td>{{s.reason}}</td></tr>
{% endfor %}</table>
</div>
<script>
let signals = {{logs|tojson}};
function playSound(){
  try{
    const ctx = new (window.AudioContext||window.webkitAudioContext)();
    const o = ctx.createOscillator(); const g = ctx.createGain();
    o.frequency.value=950; o.connect(g); g.connect(ctx.destination);
    g.gain.setValueAtTime(1, ctx.currentTime); o.start();
    setTimeout(()=>{o.stop(); ctx.close()}, 700);
  }catch(e){}
  try{ navigator.vibrate(600); }catch(e){}
}
function testSound(){ playSound(); fetch('/test_signal').then(()=>location.reload()); }
function scanNow(){ fetch('/scan_now').then(r=>r.json()).then(d=>{ if(d.length>0) playSound(); location.reload(); }); }
function renderLive(){
  const now=Date.now(); let html='';
  signals.slice(-10).reverse().forEach(s=>{
    const diff=Math.floor((s.expire_ts*1000-now)/1000);
    if(diff>0){
      const m=Math.floor(diff/60); const sec=diff%60;
      html+=`<div class="card ${s.signal=='BUY'?'buy':'sell'}"><span class="badge ${s.signal=='BUY'?'b-buy':'b-sell'}">${s.signal} ${s.symbol} OTC</span> ${s.price} <span class="timer">00:0${m}:${sec<10?'0':''}${sec}</span><br><span class="small">${s.reason} scade ${s.expire_str}</span></div>`;
    }
  });
  if(html=='') html='<span class="small">Nessun segnale OTC live - attendo pinbar 1.9x pulita</span>';
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

def send(msg):
    if not TOKEN or not CHAT_ID: return
    try: req.get(f"https://api.telegram.org/bot{TOKEN}/sendMessage", params={"chat_id":CHAT_ID,"text":msg}, timeout=8)
    except: pass

def analyze_otc(symbol):
    try:
        clean=symbol.replace("=X","") + " OTC"
        base=symbol
        df=fix_df(yf.Ticker(base, session=_YF_SESSION).history(period="2d", interval="1m"))
        if len(df)<50: return None
        last=df.iloc[-1]
        o=float(last['Open']); h=float(last['High']); l=float(last['Low']); cc=float(last['Close'])
        body=abs(cc-o); rng=h-l
        if rng==0 or body==0: return None
        upper=h-max(o,cc); lower=min(o,cc)-l
        is_green=cc>o; is_red=not is_green

        # PINBAR PULITA 1.9x - SOLO QUESTO
        pin_bull = lower > body*1.8 and body < rng*0.40 and upper < body*0.80
        pin_bear = upper > body*1.8 and body < rng*0.40 and lower < body*0.80

        if pin_bull and is_green:
            return {"symbol":clean,"signal":"BUY","price":round(cc,5),"reason":f"PINBAR 1.8x BULL coda {round(lower/body,1)}x","time":datetime.now().strftime("%H:%M:%S"),"expire_ts":time.time()+360,"expire_str":(datetime.now()+timedelta(minutes=6)).strftime("%H:%M:%S")}
        if pin_bear and is_red:
            return {"symbol":clean,"signal":"SELL","price":round(cc,5),"reason":f"PINBAR 1.8x BEAR coda {round(upper/body,1)}x","time":datetime.now().strftime("%H:%M:%S"),"expire_ts":time.time()+360,"expire_str":(datetime.now()+timedelta(minutes=6)).strftime("%H:%M:%S")}
    except: return None
    return None

def scan_loop():
    global last_scan
    time.sleep(5)
    while True:
        found=0
        for sym in OTC_PAIRS:
            r=analyze_otc(sym)
            if r:
                if not any(x['symbol']==r['symbol'] and time.time()-x['expire_ts']<300 for x in signals_log[-20:]):
                    signals_log.append(r)
                    if len(signals_log)>200: signals_log.pop(0)
                    send(f"🔶 OTC 1.9x {r['signal']} {r['symbol']} {r['price']} {r['reason']}")
                    found+=1
        last_scan={"time":datetime.now().strftime("%H:%M:%S"),"found":found}
        time.sleep(35)

@app.route('/')
def home(): return render_template_string(HTML, logs=signals_log, last=last_scan)
@app.route('/scan_now')
def scan_now():
    res=[]
    for sym in OTC_PAIRS:
        r=analyze_otc(sym)
        if r: res.append(r); signals_log.append(r)
    return jsonify(res)
@app.route('/test_signal')
def test_signal():
    fake={"symbol":random.choice(["EURUSD","GBPUSD","USDJPY"])+" OTC","signal":random.choice(["BUY","SELL"]),"price":round(random.uniform(1,150),4),"reason":"TEST OTC 1.9x PULITA","time":datetime.now().strftime("%H:%M:%S"),"expire_ts":time.time()+360,"expire_str":(datetime.now()+timedelta(minutes=6)).strftime("%H:%M:%S")}
    signals_log.append(fake)
    return jsonify(fake)
@app.route('/api/signals')
def api(): return jsonify(signals_log)

threading.Thread(target=scan_loop, daemon=True).start()
if __name__=="__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT",10000)))
