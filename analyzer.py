# Analyzer.py - OTC WEEKEND TURBO - ANTI LAG 5x - 1MIN->3MIN - SEGNALI SUBITO
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

class OTCTurboAnalyzer:
    def __init__(self):
        self.file = "storico_otc_turbo.json"
        self.storico = []
        if os.path.exists(self.file):
            try:
                with open(self.file, 'r') as f: self.storico = json.load(f)
            except: self.storico = []
    def save(self):
        try:
            with open(self.file, 'w') as f: json.dump(self.storico, f, indent=2)
        except: pass

    def is_pinbar_turbo(self, o,h,l,c):
        body = abs(c - o)
        upper = h - max(c,o)
        lower = min(c,o) - l
        total = h - l
        if total == 0 or body == 0: return None
        if body > total * 0.55: return None
        score_buy = (lower/total)*100
        score_sell = (upper/total)*100
        # TURBO 1.5x - 60% per WEEKEND
        if lower > body * 1.5 and upper < body * 1.2 and score_buy >= 60 and c >= o:
            return "BUY", round(score_buy,1), round(lower/max(body,0.00001),1)
        if upper > body * 1.5 and lower < body * 1.2 and score_sell >= 60 and c <= o:
            return "SELL", round(score_sell,1), round(upper/max(body,0.00001),1)
        return None

    def analyze(self, df, pair_otc):
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
        df.columns = [c.lower() for c in df.columns]
        if len(df) < 25: return None
        last = df.iloc[-2]
        o,h,l,c = float(last['open']), float(last['high']), float(last['low']), float(last['close'])
        res = self.is_pinbar_turbo(o,h,l,c)
        if not res: return None
        signal, score, x_factor = res
        now = datetime.now(ITALIA)
        expiry = now + timedelta(minutes=3)
        if any(s['pair']==pair_otc and abs(s['timestamp']-now.timestamp())<90 for s in self.storico[-15:]): return None
        segnale = {
            "pair": pair_otc, "signal": signal, "score": score, "x_factor": x_factor,
            "prezzo": c,
            "time_str": now.strftime("%d/%m %H:%M:%S"),
            "expiry_time": expiry.strftime("%H:%M:%S"),
            "expiry_full": expiry.strftime("%d/%m %H:%M:%S"),
            "timestamp": now.timestamp(),
            "expiry_timestamp": expiry.timestamp(),
            "timeframe": "1 MIN OTC", "scadenza": "3 MIN", "status": "ATTIVO"
        }
        self.storico.append(segnale); self.save()
        send_telegram(f"🔥 TURBO OTC {signal} {pair_otc} 3MIN\nPINBAR {x_factor}x Score {score}%\nENTRATA {segnale['time_str']} IT\nSCAD {segnale['expiry_full']} IT")
        return segnale

    def get_pending(self):
        now = datetime.now(ITALIA).timestamp()
        for s in self.storico:
            if s['status']=="ATTIVO" and now > s['expiry_timestamp']: s['status']="SCADUTO"
        self.save()
        return [s for s in self.storico if s['status']=="ATTIVO" and now - s['timestamp'] < 200]
    def get_history(self): return self.storico[-50:][::-1]

OTC_MAP = {
    "EURUSD-OTC": "EURUSD=X",
    "GBPUSD-OTC": "GBPUSD=X",
    "USDJPY-OTC": "USDJPY=X",
    "AUDUSD-OTC": "AUDUSD=X",
    "USDCAD-OTC": "USDCAD=X",
    "EURJPY-OTC": "EURJPY=X",
    "GBPJPY-OTC": "GBPJPY=X",
    "EURGBP-OTC": "EURGBP=X",
    "AUDJPY-OTC": "AUDJPY=X",
    "USDCHF-OTC": "USDCHF=X",
    "EURUSD2-OTC": "EURUSD=X",
    "GBPUSD2-OTC": "GBPUSD=X"
}

app = Flask(__name__)
analyzer = OTCTurboAnalyzer()
scan_count = 0; pair_index = 0; last_scan = 0; last_debug = "TURBO OTC 1.5x 60%"

HTML_PAGE = '''
<!DOCTYPE html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>TURBO OTC 5x PINBAR 3MIN</title>
<style>
body{background:#0a0614;color:#fff;font-family:Arial;padding:10px;margin:0}
.top{text-align:center;color:#ff55ff;font-size:28px;font-weight:bold;padding:12px;background:#1a102a;border-radius:12px;border:2px solid #ff55ff;box-shadow:0 0 15px rgba(255,85,255,0.3)}
.sub{text-align:center;color:#ffeb00;font-size:12px;margin:6px 0;font-weight:bold}
.badge{text-align:center;background:#1e142e;padding:8px;border-radius:8px;margin:8px 0;font-size:11px;border:1px solid #5a2a5a}
.card{border-left:6px solid #ff55ff;border-radius:12px;padding:12px;margin-bottom:8px;background:#2a1430;animation:pop 0.3s}
.sell{border-left-color:#ff4444;background:#2a141f}
.otc{color:#ff55ff;font-size:10px;font-weight:bold;background:#4a1a4a;padding:3px 6px;border-radius:4px}
.exp{background:#ffeb00;color:#000;padding:4px 8px;border-radius:5px;font-weight:bold;font-size:13px}
.r{color:#ccc;font-size:11px;margin-top:5px}
.old{padding:8px 10px;margin-bottom:4px;background:#161022;color:#888;font-size:11px;display:flex;justify-content:space-between;border-radius:6px;border-left:2px solid #4a2a5a}
@keyframes pop{0%{transform:scale(0.9)}100%{transform:scale(1)}}
</style></head><body>
<div class="top" id="clock">00:00:00 ITALIA</div>
<div class="sub">🔥 TURBO OTC WEEKEND - ANTI LAG 5x - PINBAR - 1MIN → 3MIN</div>
<div class="badge">🔥 LIVE: {{pending|length}} | SCAN: {{scan_count}} | BATCH: {{batch_info}} | {{last_debug}} | {{now_italia}}</div>
<div style="text-align:center;color:#ff55ff;font-size:11px;margin:5px 0">✅ TURBO: Coda 1.5x | Score 60% | Corpo 55% | 5 coppie ogni 10 sec | 3MIN | Storico+Suono ON</div>
{% for h in pending[::-1] %}
<div class="card {{'sell' if h.signal=='SELL' else ''}}">
<div><span class="otc">TURBO OTC</span> <b style="font-size:16px">{{h.pair}}</b> <span style="color:{% if h.signal=='BUY' %}#ff55ff{% else %}#ff5555{% endif %};font-weight:bold;font-size:16px">{{h.signal}}</span> <span class="exp">SCAD {{h.expiry_time}} IT</span></div>
<div style="margin:5px 0"><span style="color:#ccc;font-size:11px">{{h.timeframe}} → {{h.scadenza}} | PINBAR {{h.x_factor}}x</span></div>
<div class="r">⏰ {{h.time_str}} IT | Score {{h.score}}% | {{h.prezzo}} | Turbo Weekend</div>
</div>
{% endfor %}
{% if pending|length==0 %}
<div style="text-align:center;color:#777;padding:25px;font-size:13px">🔥 Turbo OTC in attesa...<br>Scansiona 5 alla volta - soglia bassa per weekend<br><span style="font-size:10px">Storico + Suono attivi</span></div>
{% endif %}
<div style="margin-top:16px"><h3 style="color:#aaa;font-size:12px">📜 STORICO 50 OTC - SALVATO</h3>
{% for h in history %}
<div class="old"><span><span style="color:#ff55ff">{{h.time_str}} IT</span> <b>{{h.pair}}</b> {{h.signal}} PINBAR {{h.x_factor}}x → SCAD {{h.expiry_time}} IT</span><span>{{h.status}} {{h.score}}%</span></div>
{% endfor %}
</div>
<audio id="beep" preload="auto"><source src="https://actions.google.com/sounds/v1/alarms/beep_short.ogg" type="audio/ogg"></audio>
<script>
function upd(){let now=new Date().toLocaleString('it-IT',{timeZone:'Europe/Rome',hour12:false});document.getElementById('clock').innerText=now+" ITALIA"}setInterval(upd,1000);upd();
function playSound(){try{let a=document.getElementById('beep');a.volume=1;a.currentTime=0;a.play();let ctx=new(window.AudioContext||window.webkitAudioContext)();for(let i=0;i<4;i++){setTimeout(()=>{let o=ctx.createOscillator();let g=ctx.createGain();o.frequency.value=1000+i*150;g.gain.value=0.3;o.connect(g);g.connect(ctx.destination);o.start();setTimeout(()=>o.stop(),300)},i*350)}}catch(e){}}
if({{pending|length}}>0){setTimeout(playSound,500);setInterval(playSound,2800)}
setTimeout(()=>location.reload(),10000);
</script>
</body></html>
'''

def do_scan():
    global scan_count, pair_index, last_scan, last_debug
    if time.time() - last_scan < 10: return
    last_scan = time.time(); scan_count += 1
    all_otc = list(OTC_MAP.items())
    batch = []
    for i in range(5):
        idx = (pair_index + i) % len(all_otc)
        batch.append(all_otc[idx])
    pair_index = (pair_index + 5) % len(all_otc)
    f=0
    names=[]
    for otc_name, real_symbol in batch:
        names.append(otc_name[:3])
        try:
            df = yf.Ticker(real_symbol).history(period="1d", interval="1m", auto_adjust=False)
            if len(df) < 25: continue
            res = analyzer.analyze(df, otc_name)
            if res: f+=1
        except: continue
    last_debug = f"TURBO:{f} {','.join(names)} {datetime.now(ITALIA).strftime('%H:%M:%S')}"

@app.route('/')
def home():
    do_scan()
    all_otc = list(OTC_MAP.keys())
    batch_info = f"{pair_index+1}-{(pair_index+5)%len(all_otc)} di {len(all_otc)}"
    return render_template_string(HTML_PAGE, pending=analyzer.get_pending(), history=analyzer.get_history(), scan_count=scan_count, batch_info=batch_info, last_debug=last_debug, now_italia=datetime.now(ITALIA).strftime("%d/%m %H:%M:%S IT"))

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
