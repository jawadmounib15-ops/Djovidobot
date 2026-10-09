# Analyzer.py - DOPPIO LAVORO + ITALIA + SUONO + STORICO + SCADENZA 6MIN
import os, json, time, requests
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from flask import Flask, render_template_string

TOKEN = (os.getenv("TELEGRAM_TOKEN") or os.getenv("TOKEN") or "").strip()
CHAT_ID = (os.getenv("TELEGRAM_CHAT_ID") or os.getenv("CHAT_ID") or "").strip()
ITALIA = ZoneInfo("Europe/Rome")

def send_telegram(msg):
    if not TOKEN or not CHAT_ID: return
    try: requests.get(f"https://api.telegram.org/bot{TOKEN}/sendMessage", params={"chat_id": CHAT_ID, "text": msg}, timeout=5)
    except: pass

class DoppioLavoro:
    def __init__(self):
        self.file = "storico_doppio.json"
        self.storico = []
        if os.path.exists(self.file):
            try:
                with open(self.file, 'r') as f: self.storico = json.load(f)
            except: self.storico = []
    def save(self):
        try:
            with open(self.file, 'w') as f: json.dump(self.storico, f, indent=2)
        except: pass

    def lavoro1_pinbar(self, df):
        if len(df) < 20: return None
        last = df.iloc[-2]
        o,h,l,c = float(last['open']), float(last['high']), float(last['low']), float(last['close'])
        body = abs(c - o); upper = h - max(c,o); lower = min(c,o) - l; total = h - l
        if total == 0: return None
        if body == 0: body = total * 0.05
        if body > total * 0.38: return None
        sb = (lower/total)*100; ss = (upper/total)*100
        if lower > body * 1.8 and upper < body * 1.1 and sb >= 64 and c > o:
            return "BUY", round(sb,1), f"PINBAR {round(lower/body,1)}x", "L1-PINBAR"
        if upper > body * 1.8 and lower < body * 1.1 and ss >= 64 and c < o:
            return "SELL", round(ss,1), f"PINBAR {round(upper/body,1)}x", "L1-PINBAR"
        return None

    def lavoro2_engulfing(self, df):
        if len(df) < 25: return None
        last = df.iloc[-2]; prev = df.iloc[-3]
        o1,c1 = float(prev['open']), float(prev['close'])
        o2,c2 = float(last['open']), float(last['close'])
        ema10 = df['close'].rolling(10).mean().iloc[-2]
        ema20 = df['close'].rolling(20).mean().iloc[-2]
        if c1 < o1 and c2 > o2 and c2 > o1 and o2 < c1 and c2 > ema10 and ema10 > ema20:
            score = abs(c2 - o2) / max(abs(c1 - o1),0.00001) * 50 + 50
            if score >= 64: return "BUY", round(min(score,95),1), "ENGULFING", "L2-ENGULF"
        if c1 > o1 and c2 < o2 and c2 < o1 and o2 > c1 and c2 < ema10 and ema10 < ema20:
            score = abs(c2 - o2) / max(abs(c1 - o1),0.00001) * 50 + 50
            if score >= 64: return "SELL", round(min(score,95),1), "ENGULFING", "L2-ENGULF"
        return None

    def analyze(self, df, pair):
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
        df.columns = [c.lower() for c in df.columns]
        res = self.lavoro1_pinbar(df)
        if not res: res = self.lavoro2_engulfing(df)
        if not res: return None
        signal, score, dettaglio, lavoro = res
        now = datetime.now(ITALIA)
        expiry = now + timedelta(minutes=6)
        segnale = {
            "pair": pair, "signal": signal, "score": score, "dettaglio": dettaglio, "lavoro": lavoro,
            "prezzo": float(df.iloc[-2]['close']),
            "time_str": now.strftime("%d/%m %H:%M:%S"),
            "expiry_time": expiry.strftime("%H:%M:%S"),
            "expiry_full": expiry.strftime("%d/%m %H:%M:%S"),
            "timestamp": now.timestamp(),
            "expiry_timestamp": expiry.timestamp(),
            "timeframe": "2 MIN", "scadenza": "6 MIN", "status": "ATTIVO"
        }
        if any(s['pair']==pair and abs(s['timestamp']-segnale['timestamp'])<120 for s in self.storico[-15:]): return None
        self.storico.append(segnale); self.save()
        send_telegram(f"🇮🇹 {lavoro} {signal} {pair} SCAD 6MIN\n{dettaglio} {score}%\nENTRATA: {segnale['time_str']} IT\nSCADENZA: {segnale['expiry_full']} IT")
        return segnale

    def get_pending(self):
        now = datetime.now(ITALIA).timestamp()
        for s in self.storico:
            if s['status']=="ATTIVO" and now > s['expiry_timestamp']: s['status']="SCADUTO"
        self.save()
        return [s for s in self.storico if s['status']=="ATTIVO" and now - s['timestamp'] < 400]
    def get_history(self): return self.storico[-60:][::-1]

PAIRS = ["EURUSD=X","GBPUSD=X","USDJPY=X","AUDUSD=X","USDCAD=X","USDCHF=X","NZDUSD=X","EURJPY=X","EURGBP=X","EURCHF=X","EURCAD=X","EURAUD=X","GBPJPY=X","GBPCHF=X","GBPAUD=X","AUDJPY=X","CADJPY=X","CHFJPY=X","NZDJPY=X","AUDCAD=X","NZDCAD=X"]
app = Flask(__name__)
analyzer = DoppioLavoro()
scan_count = 0; pair_index = 0; last_scan = 0; last_debug = "ITALIA MODE"

HTML_PAGE = '''
<!DOCTYPE html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>2MIN -> 6MIN ITALIA</title>
<style>
body{background:#080808;color:#fff;font-family:Arial;padding:10px;margin:0}
.top{text-align:center;color:#00ff88;font-size:28px;font-weight:bold;padding:12px;background:#161616;border-radius:12px;border:1px solid #00ff88}
.sub{text-align:center;color:#ffeb00;font-size:13px;margin:6px 0;font-weight:bold}
.badge{text-align:center;background:#1e1e1e;padding:8px;border-radius:8px;margin:8px 0;font-size:11px;border:1px solid #333}
.card{border-left:5px solid #00e676;border-radius:12px;padding:12px;margin-bottom:8px;background:#1e1e1e;position:relative}
.sell{border-left-color:#ff3b30}
.l1{color:#00ff88;font-size:10px;font-weight:bold;background:#003d1f;padding:2px 5px;border-radius:3px}
.l2{color:#ff9800;font-size:10px;font-weight:bold;background:#3d2800;padding:2px 5px;border-radius:3px}
.exp{background:#ffeb00;color:#000;padding:3px 8px;border-radius:5px;font-weight:bold;font-size:13px}
.r{color:#aaa;font-size:11px;margin-top:4px}
.scad{color:#ff5252;font-size:11px;font-weight:bold}
.storico{margin-top:16px;border-top:2px solid #222;padding-top:10px}
.storico h3{color:#888;font-size:12px;margin:6px 0}
.old{padding:8px 10px;margin-bottom:4px;background:#141414;color:#777;font-size:11px;display:flex;justify-content:space-between;border-radius:6px;border-left:2px solid #333}
.it{color:#00ff88;font-size:10px}
</style></head><body>
<div class="top" id="clock">00:00:00 ITALIA</div>
<div class="sub">⏱ ANALISI 2 MIN → SCADENZA 6 MIN | ORARIO ITALIA</div>
<div class="badge">🎯 LIVE: {{pending|length}} | SCAN: {{scan_count}} | {{last_debug}} | {{now_italia}}</div>

{% for h in pending[::-1] %}
<div class="card {{'sell' if h.signal=='SELL' else ''}}">
<div>
<div><span class="{{'l1' if 'L1' in h.lavoro else 'l2'}}">{{h.lavoro}}</span> <b style="font-size:15px">{{h.pair}}</b> <span style="color:{% if h.signal=='BUY' %}#00e676{% else %}#ff5252{% endif %};font-weight:bold;font-size:15px">{{h.signal}}</span></div>
<div style="margin:6px 0"><span class="exp">SCADENZA {{h.expiry_time}} IT</span> <span style="color:#ccc;font-size:11px">{{h.timeframe}} → {{h.scadenza}}</span></div>
<div class="r">⏰ Entrata: {{h.time_str}} IT | {{h.dettaglio}} | Score {{h.score}}% | {{h.prezzo}}</div>
</div>
</div>
{% endfor %}

{% if pending|length==0 %}
<div style="text-align:center;color:#555;padding:25px;font-size:13px">
🔍 In attesa...<br>
Lavoro 1 = Pinbar 64%<br>
Se non trova → Lavoro 2 = Engulfing<br>
<span style="font-size:10px">Orario Italia attivo</span>
</div>
{% endif %}

<div class="storico">
<h3>📜 STORICO 60 SEGNALI - ORARIO ITALIA</h3>
{% for h in history %}
<div class="old">
<span><span class="it">{{h.time_str}} IT</span> <b>{{h.pair}}</b> {{h.signal}} <span style="font-size:9px">{{h.lavoro}}</span> → <span class="scad">SCAD {{h.expiry_time}} IT</span></span>
<span>{{h.status}} {{h.score}}%</span>
</div>
{% endfor %}
</div>

<!-- SUONO FORTE -->
<audio id="beep" preload="auto" autoplay>
<source src="https://actions.google.com/sounds/v1/alarms/beep_short.ogg" type="audio/ogg">
<source src="https://actions.google.com/sounds/v1/alarms/alarm_clock.ogg" type="audio/ogg">
</audio>

<script>
function upd(){
  let now = new Date().toLocaleString('it-IT', {timeZone: 'Europe/Rome', hour12:false});
  document.getElementById('clock').innerText = now + " ITALIA";
}
setInterval(upd,1000); upd();

function playSound(){
  try{
    let audio = document.getElementById('beep');
    audio.volume = 1.0;
    audio.play();
    // beep extra con Web Audio
    let ctx = new (window.AudioContext || window.webkitAudioContext)();
    let osc = ctx.createOscillator();
    let gain = ctx.createGain();
    osc.frequency.value = 880;
    osc.type = 'sine';
    gain.gain.value = 0.8;
    osc.connect(gain); gain.connect(ctx.destination);
    osc.start();
    setTimeout(()=>{osc.stop()},600);
    // secondo beep
    setTimeout(()=>{
      let osc2 = ctx.createOscillator();
      osc2.frequency.value = 1200;
      osc2.connect(ctx.destination);
      osc2.start(); osc2.stop(ctx.currentTime+0.4);
    },700);
  }catch(e){console.log(e)}
}

// suona se ci sono segnali LIVE
if({{pending|length}} > 0){
  setTimeout(playSound, 800);
  // suona ogni 3 sec finchè c'è segnale attivo
  setInterval(playSound, 3000);
}

setTimeout(()=>location.reload(), 12000);
</script>
</body></html>
'''

def do_scan():
    global scan_count, pair_index, last_scan, last_debug
    if time.time() - last_scan < 15: return
    last_scan = time.time(); scan_count += 1
    batch = PAIRS[pair_index:pair_index+8]
    if len(batch) < 8: batch += PAIRS[:8-len(batch)]
    pair_index = (pair_index + 8) % len(PAIRS)
    f1=f2=0
    for sym in batch:
        try:
            df = yf.Ticker(sym).history(period="1d", interval="2m", auto_adjust=False)
            if len(df) < 10:
                df1 = yf.Ticker(sym).history(period="1d", interval="1m", auto_adjust=False)
                if len(df1) > 4:
                    df = df1.resample('2min').agg({'open':'first','high':'max','low':'min','close':'last','volume':'sum'}).dropna()
            res = analyzer.analyze(df, sym.replace("=X",""))
            if res:
                if "L1" in res['lavoro']: f1+=1
                else: f2+=1
        except: continue
    now_it = datetime.now(ITALIA).strftime("%H:%M:%S IT")
    last_debug = f"L1:{f1} L2:{f2} {batch[0][:6]} {now_it}"

@app.route('/')
def home():
    do_scan()
    return render_template_string(HTML_PAGE, pending=analyzer.get_pending(), history=analyzer.get_history(), scan_count=scan_count, last_debug=last_debug, now_italia=datetime.now(ITALIA).strftime("%d/%m %H:%M:%S IT"))

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
