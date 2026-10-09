# Analyzer.py - V6.1 FIX STORICO + SCADENZA + SUONO
import os, time, threading
from flask import Flask, render_template_string, jsonify
import yfinance as yf
import pandas as pd
from curl_cffi import requests as cffi_requests
import requests as req
from datetime import datetime, timedelta
import random

TOKEN = os.getenv("TELEGRAM_TOKEN", os.getenv("TOKEN", "")).strip()
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", os.getenv("CHAT_ID", "")).strip()

PAIRS = ["EURUSD=X","GBPUSD=X","USDJPY=X","AUDUSD=X","USDCAD=X","USDCHF=X",
         "EURJPY=X","EURGBP=X","GBPJPY=X","AUDJPY=X","CADJPY=X","CHFJPY=X","EURCHF=X","AUDCAD=X"]

app = Flask(__name__)
_YF_SESSION = cffi_requests.Session(impersonate="chrome")
signals_log = []
last_scan = {"time":"In avvio...","found":0,"debug":"Avvio scan..."}

HTML = """
<!DOCTYPE html><html><head><title>Analyzer V6.1</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>
body{background:#0f172a;color:#e2e8f0;font-family:Arial;padding:12px}
.card{background:#1e293b;padding:12px;border-radius:12px;margin:8px 0;border-left:5px solid #334155}
.buy{border-left-color:#22c55e}.sell{border-left-color:#ef4444}
.badge{padding:4px 10px;border-radius:6px;font-weight:bold}
.b-buy{background:#22c55e;color:#000}.b-sell{background:#ef4444;color:#fff}
.timer{font-size:18px;font-weight:bold;color:#facc15}
button{padding:12px;border-radius:10px;background:#3b82f6;color:white;border:none;font-weight:bold;width:100%;margin:5px 0}
table{width:100%;border-collapse:collapse;font-size:11px} th,td{padding:6px;border-bottom:1px solid #334155}
.small{color:#94a3b8;font-size:11px}
</style></head><body>
<h2>📊 Analyzer V6.1 - FIX 1.5x</h2>
<div class="card">⏰ {{last.time}} | Trovati: {{last.found}} | Totale: {{logs|length}}<br><span class="small">{{last.debug}}</span></div>
<div class="card">
<button onclick="scanNow()">🔍 SCANNA ORA</button>
<button onclick="testSound()" style="background:#22c55e">🔊 TEST SUONO + SEGNALE FAKE</button>
</div>
<div class="card"><h3>🔴 LIVE 6 Min</h3><div id="live">Caricamento...</div></div>
<div class="card"><h3>📜 STORICO</h3>
<table><tr><th>Ora</th><th>Segnale</th><th>Prezzo</th><th>RSI</th><th>Motivo</th></tr>
{% for s in logs[::-1][:50] %}
<tr><td>{{s.time}}</td><td><span class="badge {{'b-buy' if s.signal=='BUY' else 'b-sell'}}">{{s.signal}} {{s.symbol}}</span></td>
<td>{{s.price}}</td><td>{{s.rsi}}</td><td>{{s.reason}}</td></tr>
{% endfor %}</table>
{% if logs|length==0 %}<p class="small">Ancora vuoto - Render ci mette 60 sec al primo avvio, aspetta e clicca SCANNA ORA</p>{% endif %}
</div>
<script>
let signals = {{logs|tojson}};
function playSound(){
  try{
    const ctx = new (window.AudioContext||window.webkitAudioContext)();
    const o = ctx.createOscillator(); const g = ctx.createGain();
    o.frequency.value=880; o.connect(g); g.connect(ctx.destination);
    g.gain.setValueAtTime(1, ctx.currentTime); o.start();
    setTimeout(()=>{o.stop(); ctx.close()}, 600);
  }catch(e){}
  try{ navigator.vibrate(500); }catch(e){}
}
function testSound(){
  playSound();
  fetch('/test_signal').then(r=>r.json()).then(d=>{ alert('TEST: '+d.signal+' '+d.symbol); location.reload(); });
}
function scanNow(){
  playSound();
  fetch('/scan_now').then(r=>r.json()).then(d=>{
    if(d.length>0){ playSound(); }
    location.reload();
  });
}
function renderLive(){
  const now = Date.now();
  let html='';
  signals.slice(-10).reverse().forEach(s=>{
    const diff = Math.floor((s.expire_ts*1000 - now)/1000);
    if(diff>0){
      const m=Math.floor(diff/60); const sec=diff%60;
      html+=`<div class="card ${s.signal=='BUY'?'buy':'sell'}"><span class="badge ${s.signal=='BUY'?'b-buy':'b-sell'}">${s.signal} ${s.symbol}</span> ${s.price} <span class="timer">00:0${m}:${sec<10?'0':''}${sec}</span><br><span class="small">${s.reason} scade ${s.expire_str}</span></div>`;
    }
  });
  if(html=='') html='<span class="small">Nessun live - in attesa pinbar 1.5x</span>';
  document.getElementById('live').innerHTML=html;
}
setInterval(()=>{
  fetch('/api/signals').then(r=>r.json()).then(data=>{
    if(data.length>signals.length){ playSound(); signals=data; renderLive(); }
  });
},5000);
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

def analyze_pair(symbol):
    try:
        clean=symbol.replace("=X","")
        df=fix_df(yf.Ticker(symbol, session=_YF_SESSION).history(period="2d", interval="2m"))
        if len(df)<100: return None, f"{clean} no data"
        df['e20']=df['Close'].ewm(span=20).mean()
        df['e50']=df['Close'].ewm(span=50).mean()
        df['rsi']=rsi(df['Close'])
        last=df.iloc[-1]
        o=float(last['Open']); h=float(last['High']); l=float(last['Low']); cc=float(last['Close'])
        e20=float(last['e20']); e50=float(last['e50']); rsi_v=float(last['rsi'])
        body=abs(cc-o); rng=h-l
        if rng<0.00001 or body==0: return None, f"{clean} body 0"
        upper=h-max(o,cc); lower=min(o,cc)-l
        is_green=cc>o; is_red=not is_green

        # FIX: 1.5x LARGO come tuo screen CADJPY
        pin_bull = lower > body*1.5 and body < rng*0.80 and is_green
        pin_bear = upper > body*1.5 and body < rng*0.80 and is_red
        if not (pin_bull or pin_bear):
            return None, f"{clean} no pinbar"

        swing_high = h >= float(df['High'].iloc[-6:-1].max())*0.9999
        swing_low = l <= float(df['Low'].iloc[-6:-1].min())*1.0001

        signal=None; reason=""
        if pin_bear and swing_high and 38<=rsi_v<=78:
            signal="SELL"; reason=f"SWING HIGH {round(upper/body,1)}x"
        elif pin_bull and swing_low and 22<=rsi_v<=38:
            signal="BUY"; reason=f"SWING LOW {round(lower/body,1)}x"
        elif pin_bull and e20>e50 and 25<=rsi_v<=60:
            signal="BUY"; reason=f"TREND {round(lower/body,1)}x"
        elif pin_bear and e20<e50 and 55<=rsi_v<=75:
            signal="SELL"; reason=f"TREND {round(upper/body,1)}x"
        else:
            return None, f"{clean} RSI {int(rsi_v)} no filtro"

        if signal:
            return {"symbol":clean,"signal":signal,"price":round(cc,5),"rsi":int(rsi_v),
                    "reason":reason,"time":datetime.now().strftime("%H:%M:%S"),
                    "expire_ts":time.time()+360,"expire_str":(datetime.now()+timedelta(minutes=6)).strftime("%H:%M:%S")}, "ok"
    except Exception as e:
        return None, f"ERR {e}"
    return None, "no"

def scan_loop():
    global last_scan
    time.sleep(8)
    while True:
        logs_debug=[]
        found=0
        for sym in PAIRS:
            r,dbg=analyze_pair(sym)
            logs_debug.append(dbg)
            if r:
                if not any(x['symbol']==r['symbol'] and abs(time.time()-x['expire_ts'])<300 for x in signals_log[-20:]):
                    signals_log.append(r)
                    if len(signals_log)>200: signals_log.pop(0)
                    send(f"🔔 {r['signal']} {r['symbol']} {r['price']} {r['reason']} scade {r['expire_str']}")
                    found+=1
        last_scan={"time":datetime.now().strftime("%H:%M:%S"),"found":found,"debug":" | ".join(logs_debug[:4])}
        time.sleep(40)

@app.route('/')
def home(): return render_template_string(HTML, logs=signals_log, last=last_scan)
@app.route('/scan_now')
def scan_now():
    res=[]
    for sym in PAIRS:
        r,_=analyze_pair(sym)
        if r: res.append(r); signals_log.append(r)
    return jsonify(res)
@app.route('/test_signal')
def test_signal():
    fake={"symbol":random.choice(["CADJPY","EURUSD","GBPJPY"]),"signal":random.choice(["BUY","SELL"]),
          "price":round(random.uniform(100,150),3),"rsi":random.randint(35,65),
          "reason":"TEST SUONO 1.5x","time":datetime.now().strftime("%H:%M:%S"),
          "expire_ts":time.time()+360,"expire_str":(datetime.now()+timedelta(minutes=6)).strftime("%H:%M:%S")}
    signals_log.append(fake)
    return jsonify(fake)
@app.route('/api/signals')
def api(): return jsonify(signals_log)

threading.Thread(target=scan_loop, daemon=True).start()

if __name__=="__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT",10000)))
