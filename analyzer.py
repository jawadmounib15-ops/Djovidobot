# Analyzer.py - V6.0 CON STORICO + SCADENZA 6MIN + SUONO
import os, time, threading
from flask import Flask, render_template_string, jsonify
import yfinance as yf
import pandas as pd
from curl_cffi import requests as cffi_requests
import requests as req
from datetime import datetime, timedelta

TOKEN = os.getenv("TELEGRAM_TOKEN", os.getenv("TOKEN", "")).strip()
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", os.getenv("CHAT_ID", "")).strip()

PAIRS = ["EURUSD=X","GBPUSD=X","USDJPY=X","AUDUSD=X","USDCAD=X","USDCHF=X",
         "EURJPY=X","EURGBP=X","GBPJPY=X","GBPCHF=X","AUDJPY=X","CADJPY=X",
         "CHFJPY=X","AUDCHF=X","EURCHF=X","AUDCAD=X","CADCHF=X","GBPAUD=X"]

app = Flask(__name__)
_YF_SESSION = cffi_requests.Session(impersonate="chrome")
signals_log = []
last_scan = {"time":"Mai","found":0}

HTML = """
<!DOCTYPE html><html><head><title>Analyzer V6</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>
body{background:#0f172a;color:#e2e8f0;font-family:Arial;padding:12px;margin:0}
.card{background:#1e293b;padding:12px;border-radius:12px;margin:8px 0;border-left:5px solid #334155}
.buy{border-left-color:#22c55e}.sell{border-left-color:#ef4444}
.badge{padding:4px 10px;border-radius:6px;font-weight:bold;display:inline-block}
.b-buy{background:#22c55e;color:#000}.b-sell{background:#ef4444;color:#fff}
.small{color:#94a3b8;font-size:11px}
.timer{font-size:18px;font-weight:bold;color:#facc15}
.expired{color:#ef4444}.live{color:#22c55e}
button{padding:12px 20px;border-radius:10px;background:#3b82f6;color:white;border:none;font-weight:bold;width:100%}
table{width:100%;border-collapse:collapse;font-size:12px}
th,td{padding:8px;border-bottom:1px solid #334155;text-align:left}
</style></head><body>
<h2>📊 Analyzer V6 - Storico + 6Min + Suono</h2>
<div class="card">⏰ Ultima: {{last.time}} | Trovati: {{last.found}} | Totale: {{logs|length}}</div>
<div class="card"><button onclick="scanNow()">🔍 SCANNA ORA + TEST SUONO</button>
<audio id="beep" preload="auto"><source src="data:audio/wav;base64,UklGRlQAAABXQVZFZm10IBAAAAABAAEAQB8AAEAfAAABAAgAZGF0YVgAAACAAP//AP//AP//AP8A/wD/AP8A/wD//wD/AP//AP//AAD//wAA/v8AAP//AAD//wAA//8AAP//AAD//wAA/v8AAP8A/wD/AP8A/wAAAP8A/wD//wAA" type="audio/wav"></audio>
</div>

<div class="card"><h3>🔴 LIVE (scadenza 6 min come Quotex)</h3><div id="live"></div></div>

<div class="card"><h3>📜 STORICO COMPLETO</h3>
<table><tr><th>Ora</th><th>Segnale</th><th>Prezzo</th><th>RSI</th><th>Motivo</th><th>Stato</th></tr>
{% for s in logs[::-1][:50] %}
<tr><td>{{s.time}}</td><td><span class="badge {{'b-buy' if s.signal=='BUY' else 'b-sell'}}">{{s.signal}} {{s.symbol}}</span></td>
<td>{{s.price}}</td><td>{{s.rsi}}</td><td>{{s.reason}}</td><td class="small">{{s.status}}</td></tr>
{% endfor %}</table></div>

<script>
let signals = {{logs|tojson}};
let lastCount = signals.length;

function playSound(){
  try{
    const ctx = new (window.AudioContext||window.webkitAudioContext)();
    const o = ctx.createOscillator(); const g = ctx.createGain();
    o.type='sine'; o.frequency.value=880; o.connect(g); g.connect(ctx.destination);
    g.gain.setValueAtTime(0.8, ctx.currentTime);
    o.start(); setTimeout(()=>{o.stop(); ctx.close()}, 400);
  }catch(e){ document.getElementById('beep').play(); }
}

function renderLive(){
  const now = Date.now();
  const liveDiv = document.getElementById('live');
  let html = '';
  let hasLive = false;
  signals.slice(-10).reverse().forEach(s=>{
    const exp = new Date(s.expire_ts*1000);
    const diff = Math.floor((exp - now)/1000);
    if(diff>0){
      hasLive=true;
      const m = Math.floor(diff/60); const sec = diff%60;
      html += `<div class="card ${s.signal=='BUY'?'buy':'sell'}"><span class="badge ${s.signal=='BUY'?'b-buy':'b-sell'}">${s.signal} ${s.symbol}</span> ${s.price} <span class="timer live">00:0${m}:${sec<10?'0':''}${sec}</span><br><span class="small">${s.reason} | Scade ${exp.toLocaleTimeString()}</span></div>`;
    }
  });
  if(!hasLive) html='<span class="small">Nessun segnale live - in attesa di pinbar 1.9x</span>';
  liveDiv.innerHTML=html;
}

function scanNow(){
  playSound();
  fetch('/scan_now').then(r=>r.json()).then(d=>{
    if(d.length>0){ playSound(); alert(d.length+' SEGNALE! '+d[0].signal+' '+d[0].symbol); }
    location.reload();
  });
}

// polling ogni 5 sec per nuovi segnali
setInterval(()=>{
  fetch('/api/signals').then(r=>r.json()).then(data=>{
    if(data.length>lastCount){
      playSound();
      if(Notification && Notification.permission=="granted"){
        const n = data[0];
        new Notification(`🎯 ${n.signal} ${n.symbol}`, {body:`${n.price} RSI${n.rsi} ${n.reason}`});
      }
      lastCount=data.length;
      signals=data;
    }
    renderLive();
  });
},5000);

setInterval(renderLive,1000);
renderLive();
if(Notification && Notification.permission!="granted"){ Notification.requestPermission(); }
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

def analyze_pair(symbol, interval="2m"):
    try:
        clean=symbol.replace("=X","")
        df=fix_df(yf.Ticker(symbol, session=_YF_SESSION).history(period="5d", interval=interval))
        if len(df)<210: return None
        df['e20']=df['Close'].ewm(span=20).mean()
        df['e50']=df['Close'].ewm(span=50).mean()
        df['rsi']=rsi(df['Close'])
        last=df.iloc[-1]
        o=float(last['Open']); h=float(last['High']); l=float(last['Low']); cc=float(last['Close'])
        e20=float(last['e20']); e50=float(last['e50']); rsi_v=float(last['rsi'])
        body=abs(cc-o); rng=h-l
        if rng<0.00001 or body==0: return None
        upper=h-max(o,cc); lower=min(o,cc)-l
        is_green=cc>o; is_red=not is_green
        pin_bull = lower > body*1.9 and body < rng*0.40 and upper < body*0.80 and is_green
        pin_bear = upper > body*1.9 and body < rng*0.40 and lower < body*0.80 and is_red
        if not (pin_bull or pin_bear): return None
        swing_high = h >= float(df['High'].iloc[-6:-1].max())
        swing_low = l <= float(df['Low'].iloc[-6:-1].min())
        signal=None; reason=""
        if pin_bear and swing_high and 20<=rsi_v<=38:
            signal="SELL"; reason="SWING HIGH (come tuo CADJPY foto)"
        elif pin_bull and swing_low and 55<=rsi_v<=75:
            signal="BUY"; reason="SWING LOW"
        else:
            if pin_bull and e20>e50 and 20<=rsi_v<=38:
                signal="BUY"; reason="Trend 1.9x"
            if pin_bear and e20<e50 and 55<=rsi_v<=75:
                signal="SELL"; reason="Trend 1.9x"
        if signal:
            now_ts = time.time()
            expire_ts = now_ts + 360 # 6 minuti come Quotex
            return {
                "symbol":clean,"signal":signal,"price":round(cc,5),
                "rsi":int(rsi_v),"reason":reason,
                "time":datetime.now().strftime("%H:%M:%S"),
                "expire_ts":expire_ts,
                "expire_str": (datetime.now()+timedelta(minutes=6)).strftime("%H:%M:%S"),
                "status":f"Scade { (datetime.now()+timedelta(minutes=6)).strftime('%H:%M:%S') }",
                "ratio": round((upper if signal=="SELL" else lower)/body,1)
            }
    except: return None
    return None

def scan_loop():
    global last_scan
    while True:
        found=0
        for sym in PAIRS:
            r=analyze_pair(sym,"2m")
            if r:
                # evita doppioni ultimi 6 min
                if not any(x['symbol']==r['symbol'] and time.time()-x['expire_ts']>-300 for x in signals_log[-10:]):
                    signals_log.append(r)
                    if len(signals_log)>200: signals_log.pop(0)
                    send(f"🔔 {r['signal']} {r['symbol']} {r['price']} RSI{r['rsi']}\n{r['reason']}\nScadenza {r['expire_str']} (6min)")
                    found+=1
        last_scan={"time":datetime.now().strftime("%H:%M:%S"),"found":found}
        time.sleep(50)

@app.route('/')
def home(): return render_template_string(HTML, logs=signals_log, last=last_scan)
@app.route('/scan_now')
def scan_now():
    res=[]
    for sym in PAIRS[:10]:
        r=analyze_pair(sym,"2m")
        if r: res.append(r); signals_log.append(r)
    return jsonify(res)
@app.route('/api/signals')
def api(): return jsonify(signals_log)

threading.Thread(target=scan_loop, daemon=True).start()

if __name__=="__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT",10000)))
