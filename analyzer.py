# Analyzer.py - V3 70% + RSI + ANTI-LOSS - 2MIN -> 6MIN ITALIA
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
    rsi = 100 - (100 / (1 + rs))
    return rsi

class AnalyzerV3:
    def __init__(self):
        self.file = "storico_v3.json"
        self.storico = []
        if os.path.exists(self.file):
            try:
                with open(self.file, 'r') as f: self.storico = json.load(f)
            except: self.storico = []
    def save(self):
        try:
            with open(self.file, 'w') as f: json.dump(self.storico, f, indent=2)
        except: pass

    # LAVORO 1 - PINBAR 70% + RSI + TREND
    def lavoro1_pinbar_70(self, df):
        if len(df) < 30: return None
        last = df.iloc[-2]
        o,h,l,c = float(last['open']), float(last['high']), float(last['low']), float(last['close'])
        body = abs(c - o); upper = h - max(c,o); lower = min(c,o) - l; total = h - l
        if total == 0: return None
        if body == 0: body = total * 0.04
        if body > total * 0.32: return None # corpo più piccolo = pinbar migliore

        rsi = calc_rsi(df['close']).iloc[-2]
        ema10 = df['close'].rolling(10).mean().iloc[-2]
        ema21 = df['close'].rolling(21).mean().iloc[-2]

        score_buy = (lower/total)*100
        score_sell = (upper/total)*100

        # BUY solo se RSI non ipercomprato e trend UP
        if lower > body * 2.0 and upper < body * 0.8 and score_buy >= 70 and c > o and rsi < 62 and c > ema10 and ema10 > ema21:
            return "BUY", round(score_buy,1), f"PINBAR {round(lower/body,1)}x RSI {round(rsi,0)}", "L1-70%"

        # SELL solo se RSI non ipervenduto e trend DOWN
        if upper > body * 2.0 and lower < body * 0.8 and score_sell >= 70 and c < o and rsi > 38 and c < ema10 and ema10 < ema21:
            return "SELL", round(score_sell,1), f"PINBAR {round(upper/body,1)}x RSI {round(rsi,0)}", "L1-70%"
        return None

    # LAVORO 2 - ENGULFING 80% + RSI
    def lavoro2_engulf_80(self, df):
        if len(df) < 30: return None
        last = df.iloc[-2]; prev = df.iloc[-3]
        o1,c1 = float(prev['open']), float(prev['close'])
        o2,c2 = float(last['open']), float(last['close'])
        rsi = calc_rsi(df['close']).iloc[-2]
        ema10 = df['close'].rolling(10).mean().iloc[-2]
        ema21 = df['close'].rolling(21).mean().iloc[-2]

        # BUY engulfing forte
        if c1 < o1 and c2 > o2 and c2 > o1 and o2 < c1 and abs(c2-o2) > abs(c1-o1)*1.2:
            score = min(abs(c2-o2)/max(abs(c1-o1),0.0001)*50+50, 97)
            if score >= 80 and rsi < 60 and rsi > 35 and c2 > ema10:
                return "BUY", round(score,1), f"ENGULF RSI {round(rsi,0)}", "L2-80%"
        # SELL engulfing forte
        if c1 > o1 and c2 < o2 and c2 < o1 and o2 > c1 and abs(c2-o2) > abs(c1-o1)*1.2:
            score = min(abs(c2-o2)/max(abs(c1-o1),0.0001)*50+50, 97)
            if score >= 80 and rsi > 40 and rsi < 65 and c2 < ema10:
                return "SELL", round(score,1), f"ENGULF RSI {round(rsi,0)}", "L2-80%"
        return None

    def analyze(self, df, pair):
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
        df.columns = [c.lower() for c in df.columns]

        # ANTI-JPY: se ho già 1 JPY LIVE, non prendo altro JPY
        pending = self.get_pending_raw()
        if "JPY" in pair:
            if sum(1 for p in pending if "JPY" in p['pair']) >= 1:
                return None

        res = self.lavoro1_pinbar_70(df)
        if not res: res = self.lavoro2_engulf_80(df)
        if not res: return None

        signal, score, dettaglio, lavoro = res
        now = datetime.now(ITALIA)
        expiry = now + timedelta(minutes=6)

        # FILTRO SCORE ALTO - solo > 85% manda segnale
        if score < 75: # salva ma non avvisa se sotto 75
            pass

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
        if any(s['pair']==pair and abs(s['timestamp']-segnale['timestamp'])<180 for s in self.storico[-15:]): return None
        self.storico.append(segnale); self.save()
        if score >= 75:
            send_telegram(f"🇮🇹 V3 {lavoro} {signal} {pair}\n{dettaglio} {score}%\nENTRATA {segnale['time_str']} IT\nSCAD {segnale['expiry_full']} IT")
        return segnale

    def get_pending_raw(self):
        now = datetime.now(ITALIA).timestamp()
        return [s for s in self.storico if s['status']=="ATTIVO" and now - s['timestamp'] < 400 and now < s['expiry_timestamp']]

    def get_pending(self):
        now = datetime.now(ITALIA).timestamp()
        for s in self.storico:
            if s['status']=="ATTIVO" and now > s['expiry_timestamp']: s['status']="SCADUTO"
        self.save()
        return self.get_pending_raw()

    def get_history(self): return self.storico[-60:][::-1]

PAIRS = ["EURUSD=X","GBPUSD=X","USDJPY=X","AUDUSD=X","USDCAD=X","USDCHF=X","NZDUSD=X","EURJPY=X","EURGBP=X","EURCHF=X","EURCAD=X","EURAUD=X","GBPJPY=X","GBPCHF=X","GBPAUD=X","AUDJPY=X","CADJPY=X","CHFJPY=X","NZDJPY=X","AUDCAD=X","NZDCAD=X"]
app = Flask(__name__)
analyzer = AnalyzerV3()
scan_count = 0; pair_index = 0; last_scan = 0; last_debug = "V3 70% RSI"

HTML_PAGE = '''
<!DOCTYPE html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>V3 70% ITALIA</title>
<style>
body{background:#050505;color:#fff;font-family:Arial;padding:10px;margin:0}
.top{text-align:center;color:#00ff88;font-size:28px;font-weight:bold;padding:12px;background:#121212;border-radius:12px;border:2px solid #00ff88}
.sub{text-align:center;color:#ffeb00;font-size:12px;margin:6px 0;font-weight:bold}
.badge{text-align:center;background:#1a1a1a;padding:8px;border-radius:8px;margin:8px 0;font-size:11px;border:1px solid #333}
.card{border-left:6px solid #00e676;border-radius:12px;padding:12px;margin-bottom:8px;background:#1e1e1e}
.sell{border-left-color:#ff3b30}
.l1{color:#00ff88;font-size:10px;font-weight:bold;background:#003d1f;padding:3px 6px;border-radius:4px}
.l2{color:#ff9800;font-size:10px;font-weight:bold;background:#3d2800;padding:3px 6px;border-radius:4px}
.exp{background:#ffeb00;color:#000;padding:4px 8px;border-radius:5px;font-weight:bold;font-size:13px}
.r{color:#aaa;font-size:11px;margin-top:5px}
.winrate{text-align:center;color:#00ff88;font-size:11px;margin:5px 0}
.old{padding:8px 10px;margin-bottom:4px;background:#141414;color:#777;font-size:11px;display:flex;justify-content:space-between;border-radius:6px;border-left:2px solid #333}
.it{color:#00ff88}
</style></head><body>
<div class="top" id="clock">00:00:00 ITALIA</div>
<div class="sub">🔥 V3 - 2 MIN → 6 MIN | 70% + RSI + TREND | ITALIA</div>
<div class="badge">LIVE: {{pending|length}} | SCAN: {{scan_count}} | {{last_debug}} | {{now_italia}} | V3 FILTRATO</div>
<div class="winrate">✅ Filtro: Score min 70% | Coda 2.0x | RSI | ANTI-JPY doppio | Solo segnali forti</div>

{% for h in pending[::-1] %}
<div class="card {{'sell' if h.signal=='SELL' else ''}}">
<div><span class="{{'l1' if 'L1' in h.lavoro else 'l2'}}">{{h.lavoro}}</span> <b style="font-size:16px">{{h.pair}}</b> <span style="color:{% if h.signal=='BUY' %}#00e676{% else %}#ff5252{% endif %};font-weight:bold;font-size:16px">{{h.signal}}</span> <span class="exp">SCAD {{h.expiry_time}} IT</span></div>
<div class="r">⏰ Entrata: {{h.time_str}} IT | {{h.dettaglio}} | Score {{h.score}}% | {{h.prezzo}}</div>
</div>
{% endfor %}

{% if pending|length==0 %}
<div style="text-align:center;color:#555;padding:25px;font-size:13px">🔍 V3 in attesa segnali FORTI >75%...<br><span style="font-size:10px">Meno segnali ma più WIN - Filtro RSI + ANTI-JPY attivo</span></div>
{% endif %}

<div style="margin-top:16px"><h3 style="color:#888;font-size:12px">📜 STORICO 60 - ORARIO ITALIA</h3>
{% for h in history %}
<div class="old"><span><span class="it">{{h.time_str}} IT</span> <b>{{h.pair}}</b> {{h.signal}} <span style="font-size:9px">{{h.lavoro}}</span> {{h.dettaglio}} → <span style="color:#ff5252;font-weight:bold">SCAD {{h.expiry_time}} IT</span></span><span>{{h.status}} {{h.score}}%</span></div>
{% endfor %}
</div>

<audio id="beep" preload="auto"><source src="https://actions.google.com/sounds/v1/alarms/beep_short.ogg" type="audio/ogg"></audio>
<script>
function upd(){let now=new Date().toLocaleString('it-IT',{timeZone:'Europe/Rome',hour12:false});document.getElementById('clock').innerText=now+" ITALIA"}setInterval(upd,1000);upd();
function playSound(){try{let a=document.getElementById('beep');a.volume=1;a.play();let ctx=new(window.AudioContext||window.webkitAudioContext)();let osc=ctx.createOscillator();osc.frequency.value=900;osc.connect(ctx.destination);osc.start();setTimeout(()=>osc.stop(),500)}catch(e){}}
if({{pending|length}}>0){setTimeout(playSound,800);setInterval(playSound,3500)}
setTimeout(()=>location.reload(),12000);
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
            if len(df) < 15:
                df1 = yf.Ticker(sym).history(period="1d", interval="1m", auto_adjust=False)
                if len(df1) > 10:
                    df = df1.resample('2min').agg({'open':'first','high':'max','low':'min','close':'last','volume':'sum'}).dropna()
            res = analyzer.analyze(df, sym.replace("=X",""))
            if res:
                if "L1" in res['lavoro']: f1+=1
                else: f2+=1
        except: continue
    last_debug = f"L1-70%:{f1} L2-80%:{f2} {batch[0][:6]} {datetime.now(ITALIA).strftime('%H:%M:%S IT')}"

@app.route('/')
def home():
    do_scan()
    return render_template_string(HTML_PAGE, pending=analyzer.get_pending(), history=analyzer.get_history(), scan_count=scan_count, last_debug=last_debug, now_italia=datetime.now(ITALIA).strftime("%d/%m %H:%M:%S IT"))

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
