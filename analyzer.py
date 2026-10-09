# Analyzer.py - FINALE 64% BILANCIATO - MEDIO STRETTO
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
    def is_pinbar_64(self, df):
        if len(df) < 25: return None, 0, 0
        last = df.iloc[-2]
        o,h,l,c = float(last['open']), float(last['high']), float(last['low']), float(last['close'])
        body = abs(c - o); upper = h - max(c, o); lower = min(c, o) - l; total = h - l
        if total == 0: return None, 0, 0
        if body == 0: body = total * 0.06
        if body > total * 0.35: return None, 0, 0
        sb = (lower/total)*100; ss = (upper/total)*100
        if lower > body * 1.7 and upper < body * 1.0 and sb >= 64 and c > o:
            return "BUY", round(sb,1), round(lower/max(body,0.00001),1)
        if upper > body * 1.7 and lower < body * 1.0 and ss >= 64 and c < o:
            return "SELL", round(ss,1), round(upper/max(body,0.00001),1)
        return None, 0, 0
    def analyze(self, df, pair):
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
        df.columns = [c.lower() for c in df.columns]
        signal, score, tail = self.is_pinbar_64(df)
        if not signal: return None
        now = datetime.now(); expiry = now + timedelta(minutes=3)
        segnale = {"pair": pair, "signal": signal, "score": score, "tail": tail, "prezzo": float(df.iloc[-2]['close']),
                   "time_str": now.strftime("%d/%m %H:%M:%S"), "expiry_time": expiry.strftime("%H:%M:%S"),
                   "timestamp": now.timestamp(), "expiry_timestamp": expiry.timestamp(), "scadenza": "3 MIN", "status": "ATTIVO"}
        if any(s['pair']==pair and abs(s['timestamp']-segnale['timestamp'])<150 for s in self.storico[-20:]): return None
        self.storico.append(segnale); self.save()
        send_telegram(f"🎯 64% {signal} {pair} ⏰3 MIN\nscore {score}% coda {tail}x\n{segnale['prezzo']:.5f}\n{segnale['time_str']}->{segnale['expiry_time']}")
        return segnale
    def get_pending(self):
        now = datetime.now().timestamp()
        for s in self.storico:
            if s['status']=="ATTIVO" and now > s['expiry_timestamp']: s['status']="SCADUTO"
        self.save()
        return [s for s in self.storico if s['status']=="ATTIVO" and now - s['timestamp'] < 200]
    def get_history(self): return self.storico[-40:][::-1]

PAIRS = ["EURUSD=X","GBPUSD=X","USDJPY=X","AUDUSD=X","USDCAD=X","USDCHF=X","NZDUSD=X","EURJPY=X","EURGBP=X","EURCHF=X","EURCAD=X","EURAUD=X","GBPJPY=X","GBPCHF=X","GBPAUD=X","AUDJPY=X","CADJPY=X","CHFJPY=X","AUDCAD=X"]
app = Flask(__name__)
analyzer = PinBarAnalyzer()
scan_count = 0; pair_index = 0; last_scan = 0; last_debug = "64% MODE"

HTML = """
<!DOCTYPE html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<style>
body{background:#0f0f0f;color:#fff;font-family:Arial;padding:8px;margin:0}
.top{text-align:center;color:#ffeb00;font-size:22px;font-weight:bold;padding:8px;background:#1c1c1c;border-radius:10px}
.badge{text-align:center;background:#252525;padding:6px;border-radius:7px;margin:6px 0;font-size:11px}
.card{border:1.5px solid #00e676;border-radius:8px;padding:7px 10px;margin-bottom:5px;background:#1e1e1e;font-size:13px;display:flex;justify-content:space-between;align-items:center}
.sell{border-color:#ff5252}
.exp{color:#ffeb00;font-weight:bold;margin-left:6px}
.r{color:#aaa;font-size:11px}
.storico{margin-top:12px;border-top:1px solid #2a2a2a;padding-top:8px}
.storico h3{color:#888;font-size:11px;margin:5px 0}
.old{padding:5px 8px;margin-bottom:3px;background:#181818;color:#777;font-size:11px;display:flex;justify-content:space-between;border-radius:5px}
</style></head><body>
<div class="top" id="clock">00:00:00</div>
<div class="badge">🎯 64% | {{pending|length}} LIVE | Scan {{scan_count}} | {{last_debug}}</div>
{% for h in pending[::-1] %}<div class="card {{'sell' if h.signal=='SELL' else ''}}"><span>🎯 <b>{{h.pair}}</b> {{h.signal}} <span class="exp">⏰ {{h.expiry_time}}</span></span><span class="r">{{h.time_str}} {{h.score}}% {{h.tail}}x</span></
