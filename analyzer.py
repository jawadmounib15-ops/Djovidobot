# Analyzer.py - V4.1 BILANCIATO - 3MIN -> 5MIN - COMPLETO
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

def calc_rsi(series, period=14):
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def calc_bollinger(series, period=20):
    sma = series.rolling(period).mean()
    std = series.rolling(period).std()
    upper = sma + std * 2
    lower = sma - std * 2
    return lower, sma, upper

class SafeAnalyzer:
    def __init__(self):
        self.file = "storico_v4_safe.json"
        self.storico = []
        if os.path.exists(self.file):
            try:
                with open(self.file, 'r') as f: self.storico = json.load(f)
            except: self.storico = []
    def save(self):
        try:
            with open(self.file, 'w') as f: json.dump(self.storico, f, indent=2)
        except: pass

    def analyze_safe(self, df, pair):
        if len(df) < 40: return None
        last = df.iloc[-2]
        prev = df.iloc[-3]
        o,h,l,c = float(last['open']), float(last['high']), float(last['low']), float(last['close'])
        o1,c1 = float(prev['open']), float(prev['close'])
        body = abs(c - o); upper = h - max(c,o); lower = min(c,o) - l; total = h - l
        if total == 0 or body == 0: return None
        if body > total * 0.35: return None

        rsi = calc_rsi(df['close']).iloc[-2]
        bb_low, bb_mid, bb_high = calc_bollinger(df['close'])
        ema20 = df['close'].ewm(span=20).mean().iloc[-2]

        ora_it = datetime.now(ITALIA).hour
        if ora_it < 7 or ora_it > 23: return None

        score_buy = (lower/total)*100
        score_sell = (upper/total)*100

        # BUY bilanciato 2.2x
        if lower > body * 2.2 and upper < body * 1.0 and score_buy >= 72 and c > o and 28 < rsi < 62 and c > ema20:
            if c < bb_mid.iloc[-2]:
                return "BUY", round(score_buy,1), f"PINBAR {round(lower/body,1)}x RSI {round(rsi,0)}", "V4.1"

        # SELL bilanciato
        if upper > body * 2.2 and lower < body * 1.0 and score_sell >= 72 and c < o and 38 < rsi < 72 and c < ema20:
            if c > bb_mid.iloc[-2]:
                return "SELL", round(score_sell,1), f"PINBAR {round(upper/body,1)}x RSI {round(rsi,0)}", "V4.1"

        # ENGULFING
        if c1 < o1 and c > o and c > o1 and o < c1 and abs(c-o) > abs(c1-o1)*1.3 and 30 < rsi < 60 and c > ema20:
            sc = min(abs(c-o)/max(abs(c1-o1),0.0001)*40+60, 96)
            if sc >= 78:
                return "BUY", round(sc,1), f"ENGULF RSI {round(rsi,0)}", "V4.1"

        if c1 > o1 and c < o and c < o1 and o > c1 and abs(c-o) > abs(c1-o1)*1.3 and 40 < rsi < 70 and c < ema20:
            sc = min(abs(c-o)/max(abs(c1-o1),0.0001)*40+60, 96)
            if sc >= 78:
                return "SELL", round(sc,1), f"ENGULF RSI {round(rsi,0)}", "V4.1"

        return None

    def analyze(self, df, pair):
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
        df.columns = [c.lower() for c in df.columns]
        res = self.analyze_safe(df, pair)
        if not res: return None
        signal, score, dettaglio, lavoro = res
        now = datetime.now(ITALIA)
        expiry = now + timedelta(minutes=5)

        if any(s['pair']==pair and abs(s['timestamp']-now.timestamp())<240 for s in self.storico[-10:]): return None

        segnale = {
            "pair": pair, "signal": signal, "score": score, "dettaglio": dettaglio, "lavoro": lavoro,
            "prezzo": float(df.iloc[-2]['close']),
            "time_str": now.strftime("%d/%m %H:%M:%S"),
            "expiry_time": expiry.strftime("%H:%M:%S"),
            "expiry_full": expiry.strftime("%d/%m %H:%M:%S"),
            "timestamp": now.timestamp(),
            "expiry_timestamp": expiry.timestamp(),
            "timeframe": "3 MIN", "scadenza": "5 MIN", "status": "ATTIVO"
        }
        self.storico.append(segnale); self.save()
        send_telegram(f"🛡️ V4.1 {signal} {pair} 5MIN\n{dettaglio} {score}%\nENTRATA {segnale['time_str']} IT\nSCAD {segnale['expiry_full']} IT")
        return segnale

    def get_pending(self):
        now = datetime.now(ITALIA).timestamp()
        for s in self.storico:
            if s['status']=="ATTIVO" and now > s['expiry_timestamp']: s['status']="SCADUTO"
        self.save()
        return [s for s in self.storico if s['status']=="ATTIVO" and now - s['timestamp'] < 360]
    def get_history(self): return self.storico[-50:][::-1]

PAIRS = ["EURUSD=X","GBPUSD=X","USDJPY=X","AUDUSD=X","USDCAD=X","EURJPY=X","GBPJPY=X","EURGBP=X","AUDJPY=X","USDCHF=X"]
app = Flask(__name__)
analyzer = SafeAnalyzer()
scan_count = 0; last_scan = 0; last_debug = "V4.1 BILANCIATO 3->5"

HTML_PAGE = '''
<!DOCTYPE html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>V4.1 BILANCIATO 3->5</title>
<style>
body{background:#060a06;color:#fff;font-family:Arial;padding:10px;margin:0}
.top{text-align:center;color:#00ff88;font-size:28px;font-weight:bold;padding:12px;background:#101a10;border-radius:12px;border:2px solid #00ff88}
.sub{text-align:center;color:#ffeb00;font-size:12px;margin:6px 0;font-weight:bold}
.badge{text-align:center;background:#151a15;padding:8px;border-radius:8px;margin:8px 0;font-size:11px;border:1px solid #2a3a2a}
.card{border-left:6px solid #00ff88;border-radius:12px;padding:12px;margin-bottom:8px;background:#1a251a}
.sell{border-left-color:#ff4444;background:#251a1a}
.safe{color:#00ff88;font-size:10px;font-weight:bold;background:#003d1f;padding:3px 6px;border-radius:4px}
.exp{background:#ffeb00;color:#000;padding:4px 8px;border-radius:5px;font-weight:bold;font-size:13px}
.r{color:#aaa;font-size:11px;margin-top:5px}
.old{padding:8px 10px;margin-bottom:4px;background:#111611;color:#777;font-size:11px;display:flex;justify-content:space-between;border-radius:6px;border-left:2px solid #333}
</style></head><body>
<div class="top" id="clock">00:00:00 ITALIA</div>
<div class="sub">🛡️ V4.1 BILANCIATO - 3 MIN → 5 MIN | 72% + BB MID + RSI + EMA | ITALIA</div>
<div class="badge">🛡️ LIVE: {{pending|length}} | SCAN: {{scan_count}} | {{last_debug}} | {{now_italia}} | 10 PAIRS</div>
<div style="text-align:center;color:#00ff88;font-size:11px;margin:5px 0">✅ Filtro BILANCIATO: Coda 2.2x | Score 72% | BB mid | RSI 28-72 | EMA20 | 10 coppie</div>
{% for h in pending[::-1] %}
<div class="card {{'sell' if h.signal=='SELL' else ''}}">
<div><span class="safe">{{h.lavoro}}</span> <b style="font-size:16px">{{h.pair}}</b> <span style="color:{% if h.signal=='BUY' %}#00ff88{% else %}#ff5555{% endif %};font-weight:bold;font-size:16px">{{h.signal}}</span> <span class="exp">SCAD {{h.expiry_time}} IT</span></div>
<div style="margin:5px 0"><span style="color:#ccc;font-size:11px">{{h.timeframe}} → {{h.scadenza}}</span></div>
<div class="r">⏰ {{h.time_str}} IT | {{h.dettaglio}} | Score {{h.score}}% | {{h.prezzo}}</div>
</div>
{% endfor %}
{% if pending|length==0 %}
<div style="text-align:center;color:#555;padding:25px;font-size:13px">🛡️ V4.1 in attesa segnali bilanciati...<br><span style="font-size:10px">3-5 segnali/ora - 10 coppie - 3MIN->5MIN</span></div>
{% endif %}
<div style="margin-top:16px"><h3 style="color:#888;font-size:12px">📜 STORICO 50 - ITALIA</h3>
{% for h in history %}
<div class="old"><span><span style="color:#00ff88">{{h.time_str}} IT</span> <b>{{h.pair}}</b> {{h.signal}} {{h.dettaglio}} → SCAD {{h.expiry_time}} IT</span><span>{{h.status}} {{h.score}}%</span></div>
{% endfor %}
</div>
<audio id="beep" preload="auto"><source src="https://actions.google.com/sounds/v1/alarms/beep_short.ogg" type="audio/ogg"></audio>
<script>
function upd(){let now=new Date().toLocaleString('it-IT',{timeZone:'Europe/Rome',hour12:false});document.getElementById('clock').innerText=now+" ITALIA"}setInterval(upd,1000);upd();
function playSound(){try{let a=document.getElementById('beep');a.volume=1;a.play();}catch(e){}}
if({{pending|length}}>0){setTimeout(playSound,800);setInterval(playSound,3500)}
setTimeout(()=>location.reload(),12000);
</script>
</body></html>
'''

def do_scan():
    global scan_count, last_scan, last_debug
    if time.time() - last_scan < 15: return
    last_scan = time.time(); scan_count += 1
    f=0
    for sym in PAIRS:
        try:
            df1 = yf.Ticker(sym).history(period="1d", interval="1m", auto_adjust=False)
            if len(df1) < 60: continue
            df = df1.resample('3min').agg({'open':'first','high':'max','low':'min','close':'last','volume':'sum'}).dropna()
            if len(df) < 40: continue
            res = analyzer.analyze(df, sym.replace("=X",""))
            if res: f+=1
        except: continue
    last_debug = f"V4.1:{f} {datetime.now(ITALIA).strftime('%H:%M:%S IT')} 3->5MIN"

@app.route('/')
def home():
    do_scan()
    return render_template_string(HTML_PAGE, pending=analyzer.get_pending(), history=analyzer.get_history(), scan_count=scan_count, last_debug=last_debug, now_italia=datetime.now(ITALIA).strftime("%d/%m %H:%M:%S IT"))

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
