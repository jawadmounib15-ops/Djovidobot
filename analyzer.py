# Analyzer.py - COMPATTO - 21 REALI - 3 MIN - SUONO + STORICO
import os, json, time, requests
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta
from flask import Flask, render_template_string

TOKEN = (os.getenv("TELEGRAM_TOKEN") or os.getenv("TOKEN") or "").strip()
CHAT_ID = (os.getenv("TELEGRAM_CHAT_ID") or os.getenv("CHAT_ID") or "").strip()

def send_telegram(msg):
    if not TOKEN or not CHAT_ID: return
    try: requests.get(f"https://api.telegram.org/bot{TOKEN}/sendMessage", params={"chat_id": CHAT_ID, "text": msg}, timeout=5)
    except: pass

class PinBarAnalyzer:
    def __init__(self):
        self.storico_file = "storico_segnali.json"
        self.storico = []
        if os.path.exists(self.storico_file):
            try:
                with open(self.storico_file, 'r') as f: self.storico = json.load(f)
            except: self.storico = []
    def save(self):
        try:
            with open(self.storico_file, 'w') as f: json.dump(self.storico, f, indent=2)
        except: pass
    def is_pinbar(self, o, h, l, c):
        body = abs(c - o); upper = h - max(c, o); lower = min(c, o) - l; total = h - l
        if total == 0: return None, 0, 0
        if body == 0: body = total * 0.06
        if body > total * 0.60: return None, 0, 0
        if lower > body * 1.3 and upper < body * 1.2 and c > (l + total*0.5):
            return "BUY", round((lower/total)*100, 1), round(lower/body, 1)
        if upper > body * 1.3 and lower < body * 1.2 and c < (l + total*0.5):
            return "SELL", round((upper/total)*100, 1), round(upper/body, 1)
        return None, 0, 0
    def analyze(self, df, pair):
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
        df.columns = [c.lower() for c in df.columns]
        if len(df) < 50: return None
        last = df.iloc[-2]
        o,h,l,c = float(last['open']), float(last['high']), float(last['low']), float(last['close'])
        signal, score, tail = self.is_pinbar(o,h,l,c)
        if not signal or score < 58: return None
        now = datetime.now(); expiry = now + timedelta(minutes=3)
        segnale = {"pair": pair, "signal": signal, "score": score, "tail": tail, "prezzo": c,
                   "time_str": now.strftime("%d/%m %H:%M:%S"), "expiry_time": expiry.strftime("%H:%M:%S"),
                   "timestamp": now.timestamp(), "expiry_timestamp": expiry.timestamp(),
                   "scadenza": "3 MIN", "status": "ATTIVO"}
        if any(s['pair']==pair and abs(s['timestamp']-segnale['timestamp'])<120 for s in self.storico[-20:]): return None
        self.storico.append(segnale); self.save()
        send_telegram(f"🎯 PINBAR {signal} {pair} ⏰3 MIN\nscore {score}% coda {tail}x\n{c:.5f}\n{segnale['time_str']} -> {segnale['expiry_time']}")
        return segnale
    def get_pending(self):
        now = datetime.now().timestamp()
        for s in self.storico:
            if s['status']=="ATTIVO" and now > s['expiry_timestamp']: s['status']="SCADUTO"
        self.save()
        return [s for s in self.storico if s['status']=="ATTIVO" and now - s['timestamp'] < 200]
    def get_history(self): return self.storico[-30:][::-1]

PAIRS = ["EURUSD=X","GBPUSD=X","USDJPY=X","AUDUSD=X","USDCAD=X","USDCHF=X","EURJPY=X","EURGBP=X","EURCHF=X","EURAUD=X","GBPJPY=X","GBPCHF=X","GBPAUD=X","AUDJPY=X","CADJPY=X","AUDCHF=X","AUDUSD=X","CHFJPY=X","AUDCAD=X"]
app = Flask(__name__)
analyzer = PinBarAnalyzer()
scan_count = 0; pair_index = 0; last_scan = 0; last_debug = "Pronto 21 coppie stretto"

HTML = """
<!DOCTYPE html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<style>
body{background:#0e0e0e;color:#fff;font-family:Arial;padding:6px;margin:0}
.top{text-align:center;color:#ffeb00;font-size:20px;font-weight:bold;padding:6px;background:#1a1a1a;border-radius:8px}
.badge{text-align:center;background:#2a2a2a;padding:4px;border-radius:6px;margin:5px 0;font-size:10px}
.card{border:1px solid #00e676;border-radius:6px;padding:5px 8px;margin-bottom:4px;background:#1e1e1e;font-size:12px;display:flex;justify-content:space-between;align-items:center}
.sell{border-color:#ff5252}
.exp{color:#ffeb00;font-weight:bold;font-size:11px}
.right{font-size:10px;color:#aaa}
.storico{margin-top:10px;border-top:1px solid #333;padding-top:6px}
.storico h3{color:#aaa;font-size:11px;margin:4px 0}
.card-old{border:1px solid #333;border-radius:5px;padding:3px 6px;margin-bottom:3px;background:#181818;color:#777;font-size:10px;display:flex;justify-content:space-between}
</style></head><body>
<div class="top" id="clock">00:00:00</div>
<div class="badge">🟢 21 REALI 1M->3M | {{pending|length}} attivi | Scan:{{scan_count}}</div>
{% for h in pending[::-1] %}
<div class="card {{'sell' if h.signal=='SELL' else ''}}">
<span>🎯 <b>{{h.pair}}</b> {{h.signal}} <span class="exp">⏰ {{h.expiry_time}}</span></span>
<span class="right">{{h.time_str}} s{{h.score}}% c{{h.tail}}x</span>
</div>
{% endfor %}
<div class="storico">
<h3>📜 STORICO 30</h3>
{% for h in history %}
<div class="card-old"><span>{{h.time_str}} {{h.pair}} {{h.signal}}</span><span>{{h.status}} {{h.score}}%</span></div>
{% endfor %}
</div>
<div style="font-size:9px;color:#555;margin-top:6px">{{last_debug}} - {{now}}</div>
<audio id="beep" preload="auto"><source src="https://actions.google.com/sounds/v1/alarms/beep_short.ogg" type="audio/ogg"></audio>
<script>
let lastCount={{pending|length}};
function upd(){document.getElementById('clock').innerText=new Date().toLocaleTimeString('it-IT')}setInterval(upd,1000);upd();
function playSound(){try{document.getElementById('beep').play();let ctx=new(window.AudioContext||window.webkitAudioContext)();let o=ctx.createOscillator();o.frequency.value=900;o.connect(ctx.destination);o.start();o.stop(ctx.currentTime+0.4);}catch(e){}}
if(lastCount>0){setTimeout(playSound,400)}
setTimeout(()=>location.reload(),15000);
</script>
</body></html>
"""

def do_scan():
    global scan_count, pair_index, last_scan, last_debug
    if time.time() - last_scan < 20: return
    last_scan = time.time(); scan_count += 1
    batch = PAIRS[pair_index:pair_index+7]
    if len(batch) < 7: batch += PAIRS[:7-len(batch)]
    pair_index = (pair_index + 7) % len(PAIRS)
    found = 0
    for sym in batch:
        try:
            df = yf.Ticker(sym).history(period="1d", interval="1m", auto_adjust=False)
            if analyzer.analyze(df, sym.replace("=X","")): found += 1
        except: continue
    last_debug = f"Scan {scan_count} {batch[0][:6]} trovati {found} attivi {len(analyzer.get_pending())}"

@app.route('/')
def home():
    do_scan()
    return render_template_string(HTML, pending=analyzer.get_pending(), history=analyzer.get_history(), scan_count=scan_count, last_debug=last_debug, now=datetime.now().strftime("%H:%M:%S"))

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
