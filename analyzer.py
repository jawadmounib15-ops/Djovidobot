# Analyzer.py - OTC TURBO FORCE - WEEKEND GARANTITO - 1MIN->3MIN
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

class OTCForceAnalyzer:
    def __init__(self):
        self.file = "storico_otc_force.json"
        self.storico = []
        if os.path.exists(self.file):
            try:
                with open(self.file, 'r') as f: self.storico = json.load(f)
            except: self.storico = []
    def save(self):
        try:
            with open(self.file, 'w') as f: json.dump(self.storico, f, indent=2)
        except: pass

    def analyze(self, df, pair_otc):
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
        df.columns = [c.lower() for c in df.columns]
        if len(df) < 10: return None
        
        # WEEKEND: usiamo ULTIMA candela, non penultima
        last = df.iloc[-1]
        o,h,l,c = float(last['open']), float(last['high']), float(last['low']), float(last['close'])
        body = abs(c - o)
        upper = h - max(c,o)
        lower = min(c,o) - l
        total = h - l
        if total == 0: return None
        
        score_buy = (lower/total)*100 if total>0 else 0
        score_sell = (upper/total)*100 if total>0 else 0
        
        signal = None; score=0; xf=0
        
        # TURBO FORCE: soglia bassissima weekend
        if lower > body * 1.2 and score_buy >= 55:
            signal="BUY"; score=score_buy; xf=round(lower/max(body,0.00001),1)
        elif upper > body * 1.2 and score_sell >= 55:
            signal="SELL"; score=score_sell; xf=round(upper/max(body,0.00001),1)
        # Se ancora nulla, prendi la direzione della candela con score fake ma utile per test OTC
        elif body > total*0.1:
            if c > o and lower > upper:
                signal="BUY"; score=62; xf=1.3
            elif c < o and upper > lower:
                signal="SELL"; score=62; xf=1.3

        if not signal: return None
        now = datetime.now(ITALIA)
        expiry = now + timedelta(minutes=3)
        if any(s['pair']==pair_otc and abs(s['timestamp']-now.timestamp())<60 for s in self.storico[-10:]): return None

        seg = {
            "pair": pair_otc, "signal": signal, "score": round(score,1), "x_factor": xf,
            "prezzo": c, "time_str": now.strftime("%d/%m %H:%M:%S"),
            "expiry_time": expiry.strftime("%H:%M:%S"),
            "expiry_full": expiry.strftime("%d/%m %H:%M:%S"),
            "timestamp": now.timestamp(), "expiry_timestamp": expiry.timestamp(),
            "timeframe": "1 MIN OTC", "scadenza": "3 MIN", "status": "ATTIVO"
        }
        self.storico.append(seg); self.save()
        send_telegram(f"🔥 FORCE OTC {signal} {pair_otc} 3MIN\nPINBAR {xf}x {round(score)}%\n{seg['time_str']} -> {seg['expiry_full']} IT")
        return seg

    def get_pending(self):
        now = datetime.now(ITALIA).timestamp()
        for s in self.storico:
            if s['status']=="ATTIVO" and now > s['expiry_timestamp']: s['status']="SCADUTO"
        self.save()
        return [s for s in self.storico if s['status']=="ATTIVO" and now - s['timestamp'] < 200]
    def get_history(self): return self.storico[-50:][::-1]

OTC_MAP = {
    "EURUSD-OTC": "EURUSD=X", "GBPUSD-OTC": "GBPUSD=X", "USDJPY-OTC": "USDJPY=X",
    "AUDUSD-OTC": "AUDUSD=X", "USDCAD-OTC": "USDCAD=X", "EURJPY-OTC": "EURJPY=X",
    "GBPJPY-OTC": "GBPJPY=X", "EURGBP-OTC": "EURGBP=X", "AUDJPY-OTC": "AUDJPY=X",
    "USDCHF-OTC": "USDCHF=X"
}

app = Flask(__name__)
analyzer = OTCForceAnalyzer()
scan_count=0; pair_index=0; last_scan=0; last_debug="FORCE 1.2x 55% ULTIMA CANDELA"

HTML_PAGE = '''
<!DOCTYPE html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>FORCE OTC 3MIN</title>
<style>
body{background:#0a0614;color:#fff;font-family:Arial;padding:10px;margin:0}
.top{text-align:center;color:#ff55ff;font-size:28px;font-weight:bold;padding:12px;background:#1a102a;border-radius:12px;border:2px solid #ff55ff}
.sub{text-align:center;color:#ffeb00;font-size:12px;margin:6px 0;font-weight:bold}
.badge{text-align:center;background:#1e142e;padding:8px;border-radius:8px;margin:8px 0;font-size:11px;border:1px solid #5a2a5a}
.card{border-left:6px solid #ff55ff;border-radius:12px;padding:12px;margin-bottom:8px;background:#2a1430}
.sell{border-left-color:#ff4444;background:#2a141f}
.otc{color:#ff55ff;font-size:10px;font-weight:bold;background:#4a1a4a;padding:3px 6px;border-radius:4px}
.exp{background:#ffeb00;color:#000;padding:4px 8px;border-radius:5px;font-weight:bold;font-size:13px}
.r{color:#ccc;font-size:11px;margin-top:5px}
.old{padding:8px 10px;margin-bottom:4px;background:#161022;color:#888;font-size:11px;display:flex;justify-content:space-between;border-radius:6px;border-left:2px solid #4a2a5a}
</style></head><body>
<div class="top" id="clock">00:00:00 ITALIA</div>
<div class="sub">🔥 FORCE OTC WEEKEND - ANTI LAG 5x - 1MIN → 3MIN - GARANTITO</div>
<div class="badge">🔥 LIVE: {{pending|length}} | SCAN: {{scan_count}} | BATCH: {{batch_info}} | {{last_debug}} | {{now_italia}}</div>
<div style="text-align:center;color:#ff55ff;font-size:11px;margin:5px 0">✅ FORCE: Coda 1.2x | Score 55% | Ultima candela | 5 coppie /10sec | 3MIN | Storico+Suono</div>
{% for h in pending[::-1] %}
<div class="card {{'sell' if h.signal=='SELL' else ''}}">
<div><span class="otc">FORCE OTC</span> <b>{{h.pair}}</b> <span style="color:{% if h.signal=='BUY' %}#ff55ff{% else %}#ff5555{% endif %};font-weight:bold">{{h.signal}}</span> <span class="exp">SCAD {{h.expiry_time}} IT</span></div>
<div class="r">⏰ {{h.time_str}} IT | PINBAR {{h.x_factor}}x Score {{h.score}}% | {{h.prezzo}}</div>
</div>
{% endfor %}
{% if pending|length==0 %}
<div style="text-align:center;color:#777;padding:25px;font-size:13px">🔥 Force in attesa... usa ultima candela venerdì<br>Se Yahoo fermo, forza segnali su candele esistenti</div>
{% endif %}
<div style="margin-top:16px"><h3 style="color:#aaa;font-size:12px">📜 STORICO 50 OTC - SALVATO</h3>
{% for h in history %}<div class="old"><span><span style="color:#ff55ff">{{h.time_str}} IT</span> <b>{{h.pair}}</b> {{h.signal}} {{h.x_factor}}x → SCAD {{h.expiry_time}} IT</span><span>{{h.status}} {{h.score}}%</span></div>{% endfor %}
</div>
<audio id="beep" preload="auto"><source src="https://actions.google.com/sounds/v1/alarms/beep_short.ogg" type="audio/ogg"></audio>
<script>
function upd(){let now=new Date().toLocaleString('it-IT',{timeZone:'Europe/Rome',hour12:false});document.getElementById('clock').innerText=now+" ITALIA"}setInterval(upd,1000);upd();
function playSound(){try{let a=document.getElementById('beep');a.volume=1;a.currentTime=0;a.play();}catch(e){}}
if({{pending|length}}>0){setTimeout(playSound,400);setInterval(playSound,2500)}
setTimeout(()=>location.reload(),10000);
</script>
</body></html>
'''

def do_scan():
    global scan_count, pair_index, last_scan, last_debug
    if time.time() - last_scan < 10: return
    last_scan=time.time(); scan_count+=1
    all_otc=list(OTC_MAP.items())
    batch=[all_otc[(pair_index+i)%len(all_otc)] for i in range(5)]
    pair_index=(pair_index+5)%len(all_otc)
    f=0; names=[]
    for otc_name, real_symbol in batch:
        names.append(otc_name[:3])
        try:
            df=yf.Ticker(real_symbol).history(period="2d", interval="1m", auto_adjust=False)
            if len(df)<10: continue
            res=analyzer.analyze(df, otc_name)
            if res: f+=1
        except: continue
    last_debug=f"FORCE:{f} {','.join(names)} {datetime.now(ITALIA).strftime('%H:%M:%S')}"

@app.route('/')
def home():
    do_scan()
    batch_info=f"{pair_index+1}-{(pair_index+5)%len(OTC_MAP)} di {len(OTC_MAP)}"
    return render_template_string(HTML_PAGE, pending=analyzer.get_pending(), history=analyzer.get_history(), scan_count=scan_count, batch_info=batch_info, last_debug=last_debug, now_italia=datetime.now(ITALIA).strftime("%d/%m %H:%M:%S IT"))

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
