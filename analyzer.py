# Analyzer.py - FINALE PRECISE + ULTRA STRETTO - 21 REALI 3 MIN
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
    def is_pinbar_preciso(self, df):
        if len(df) < 30: return None, 0, 0
        last = df.iloc[-2]; prev = df.iloc[-3]
        o,h,l,c = float(last['open']), float(last['high']), float(last['low']), float(last['close'])
        o2,c2 = float(prev['open']), float(prev['close'])
        body = abs(c - o); upper = h - max(c, o); lower = min(c, o) - l; total = h - l
        if total == 0: return None, 0, 0
        if body == 0: body = total * 0.05
        if body > total * 0.28: return None, 0, 0
        ema20 = df['close'].rolling(20).mean().iloc[-2]
        if lower > body * 2.0 and upper < body * 0.9 and lower > total * 0.55 and c > o and c > ema20 and c2 < o2:
            score = (lower/total)*100
            if score >= 68: return "BUY", round(score,1), round(lower/body,1)
        if upper > body * 2.0 and lower < body * 0.9 and upper > total * 0.55 and c < o and c < ema20 and c2 > o2:
            score = (upper/total)*100
            if score >= 68: return "SELL", round(score,1), round(upper/body,1)
        return None, 0, 0
    def analyze(self, df, pair):
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
        df.columns = [c.lower() for c in df.columns]
        signal, score, tail = self.is_pinbar_preciso(df)
        if not signal: return None
        now = datetime.now(); expiry = now + timedelta(minutes=3)
        segnale = {"pair": pair, "signal": signal, "score": score, "tail": tail, "prezzo": float(df.iloc[-2]['close']),
                   "time_str": now.strftime("%d/%m %H:%M:%S"), "expiry_time": expiry.strftime("%H:%M:%S"),
                   "timestamp": now.timestamp(), "expiry_timestamp": expiry.timestamp(), "scadenza": "3 MIN", "status": "ATTIVO"}
        if any(s['pair']==pair and abs(s['timestamp']-segnale['timestamp'])<180 for s in self.storico[-20:]): return None
        self.storico.append(segnale); self.save()
        send_telegram(f"🎯 PRECISE {signal} {pair} ⏰3 MIN\nscore {score}% coda {tail}x\n{segnale['prezzo']:.5f}\n{segnale['time_str']}->{segnale['expiry_time']}")
        return segnale
    def get_pending(self):
        now = datetime.now().timestamp()
        for s in self.storico:
            if s['status']=="ATTIVO" and now > s['expiry_timestamp']: s['status']="SCADUTO"
        self.save()
        return [s for s in self.storico if s['status']=="ATTIVO" and now - s['timestamp'] < 200]
    def get_history(self): return self.storico[-40:][::-1]

PAIRS = ["EURUSD=X","GBPUSD=X","USDJPY=X","AUDUSD=X","USDCAD=X","USDCHF=X","NZDUSD=X","EURJPY=X","EURGBP=X","EURCHF=X","EURCAD=X","EURAUD=X","GBPJPY=X","GBPCHF=X","GBPAUD=X","AUDJPY=X","CADJPY=X","CHFJPY=X","NZDJPY=X","AUDCAD=X","NZDCAD=X"]
app = Flask(__name__)
analyzer = PinBarAnalyzer()
scan_count = 0; pair_index = 0; last_scan = 0; last_debug = "PRECISE MODE"

HTML = """
<!DOCTYPE html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<style>
body{background:#0e0e0e;color:#fff;font-family:Arial;padding:4px;margin:0}
.top{text-align:center;color:#ffeb00;font-size:16px;font-weight:bold;padding:4px;background:#1a1a1a;border-radius:6px}
.badge{text-align:center;background:#2a2a2a;padding:3px;border-radius:5px;margin:4px 0;font-size:9px}
.card{border-left:3px solid #00e676;border-radius:4px;padding:3px 6px;margin-bottom:3px;background:#1e1e1e;font-size:11px;display:flex;justify-content:space-between}
.sell{border-left-color:#ff5252}.exp{color:#ffeb00;font-weight:bold}.r{color:#999;font-size:9px}
.storico{margin-top:8px;border-top:1px solid #222;padding-top:4px}
.storico h3{color:#666;font-size:9px;margin:2px 0}
.old{padding:2px 5px;margin-bottom:2px;background:#161616;color:#666;font-size:9px;display:flex;justify-content:space-between;border-radius:3px}
</style></head><body>
<div class="top" id="clock">00:00:00</div>
<div class="badge">🎯 PRECISE 68%+ | {{pending|length}} LIVE | Scan {{scan_count}} | {{last_debug}}</div>
{% for h in pending[::-1] %}<div class="card {{'sell' if h.signal=='SELL' else ''}}"><span><b>{{h.pair}}</b> {{h.signal}} <span class="exp">{{h.expiry_time}}</span></span><span class="r">{{h.time_str}} {{h.score}}% {{h.tail}}x</span></div>{% endfor %}
<div class="storico"><h3>📜 STORICO 40</h3>{% for h in history %}<div class="old"><span>{{h.time_str}} {{h.pair}} {{h.signal}}</span><span>{{h.status}} {{h.score}}%</span></div>{% endfor %}</div>
<audio id="beep" preload="auto"><source src="https://actions.google.com/sounds/v1/alarms/beep_short.ogg" type="audio/ogg"></audio>
<script>function upd(){document.getElementById('clock').innerText=new Date().toLocaleTimeString('it-IT')}setInterval(upd,1000);upd();function play(){try{document.getElementById('beep').play();let c=new(window.AudioContext||window.webkitAudioContext)();let o=c.createOscillator();o.frequency.value=950;o.connect(c.destination);o.start();o.stop(c.currentTime+0.3);}catch(e){}}if({{pending|length}}>0){setTimeout(play,300)}setTimeout(()=>location.reload(),15000);</script>
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
    last_debug = f"PRECISE {batch[0][:6]} +{found} live {len(analyzer.get_pending())}"

@app.route('/')
def home():
    do_scan()
    return render_template_string(HTML, pending=analyzer.get_pending(), history=analyzer.get_history(), scan_count=scan_count, last_debug=last_debug, now=datetime.now().strftime("%H:%M:%S"))

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
