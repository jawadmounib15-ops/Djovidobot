import yfinance as yf
from curl_cffi import requests as cffi_requests
import pytz
from datetime import datetime
import threading, time, os
from flask import Flask, render_template_string

app = Flask(__name__)
session = cffi_requests.Session(impersonate="chrome")
ROMA = pytz.timezone("Europe/Rome")

COPPIE = {
    "EURUSD=X":"EUR/USD (REAL)",
    "GBPUSD=X":"GBP/USD",
    "AUDUSD=X":"AUD/USD",
    "USDJPY=X":"USD/JPY",
    "EURJPY=X":"EUR/JPY",
    "GBPJPY=X":"GBP/JPY",
    "AUDJPY=X":"AUD/JPY",
    "EURGBP=X":"EUR/GBP"
}

HTML = """
<!DOCTYPE html>
<html>
<head>
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>V8.1 PRE-ALERT 70%</title>
<style>
body{background:#0e0e0e;color:white;font-family:Arial;padding:15px;margin:0}
.card{background:#1e1e1e;padding:15px;border-radius:15px;margin-top:15px}
.green{background:#00ff88;color:black;padding:18px;border-radius:12px;font-weight:bold;text-align:center;font-size:20px;border:none;width:100%;cursor:pointer}
.badge{background:#00ff88;color:black;padding:5px 12px;border-radius:20px;font-weight:bold}
.badge-wait{background:#333;color:#aaa;padding:5px 12px;border-radius:20px}
.badge-pre{background:#ffaa00;color:black;padding:5px 12px;border-radius:20px;font-weight:bold;animation: blink 1s infinite}
@keyframes blink {50% {opacity:0.5}}
.top{color:#00ff88;margin:8px 0}
.auto{border:1px solid #00ff88;border-radius:10px;padding:10px;margin:12px 0;color:#00ff88;text-align:center}
.pre-card{border:2px solid #ffaa00;background:#2a1f00;}
.live-card{border:2px solid #00ff88;background:#002a1a;}
</style>
</head>
<body>
<h1>🎯 V8.1 - 70% PRE-ALERT 60s</h1>
<div class="top">⚠️ Pre-allarme 1 min prima + Doppia Conferma 5m/15m</div>
<div class="auto">🟢 AUTO 24H - Pre-allarme 60s + Entrata perfetta</div>

<div class="card {{'pre-card' if 'PREPARATI' in segnale else 'live-card' if 'ENTRA' in segnale else ''}}">
<h3 style="margin:0 0 10px 0">
{% if 'PREPARATI' in segnale %}⚠️ PRE-ALLARME - PREPARATI{% elif 'ENTRA' in segnale %}✅ SEGNALE LIVE - ENTRA ORA{% else %}🚨 Monitor LIVE{% endif %}
</h3>
<div style="font-size:18px;font-weight:bold;padding:12px;background:#0e0e0e;border-radius:10px">
{{segnale}}
</div>
<div style="color:#888;margin-top:8px">{{ora2}} - Candela M5: {{candela_min}}m {{candela_sec}}s</div>
{% if 'PREPARATI' in segnale %}
<div style="color:#ffaa00;margin-top:8px;font-weight:bold">⏰ Hai 60 secondi per preparare EUR/USD, importo, e dito su acquista!</div>
{% endif %}
</div>

<div class="card">
<div style="display:flex;justify-content:space-between">
<div>EUR/USD (REAL) - M5</div><span class="{{'badge' if percent>=60 else 'badge-wait' if percent==0 else 'badge-pre'}}">{{'READY' if percent>=60 else 'PRE' if 'PREPARATI' in segnale else 'WAIT'}}</span>
</div>
<div style="color:#00ff88;font-size:36px;font-weight:bold;margin:8px 0">{{percent}}%</div>
<div style="color:#aaa">{{msg}} - {{ora}}</div>
</div>

<script>setTimeout(()=>location.reload(), 5000)</script>
</body>
</html>
"""

ultimo_stato = {"percent":0,"msg":"Attendo setup 70% largo","segnale":"Cerco 70% LARGO doppia conferma...","candela_min":0,"candela_sec":0}

def analizza_v8_largo():
    for cp, nome in COPPIE.items():
        try:
            df5 = yf.Ticker(cp, session=session).history(period="5d", interval="5m")
            df15 = yf.Ticker(cp, session=session).history(period="5d", interval="15m")
            if len(df5)<60 or len(df15)<40: continue
            cl5 = df5['Close']; cl15 = df15['Close']
            e9_5 = cl5.ewm(span=9).mean(); e21_5 = cl5.ewm(span=21).mean()
            e9_15 = cl15.ewm(span=9).mean(); e21_15 = cl15.ewm(span=21).mean()
            ema9 = e9_5.iloc[-1]; ema21 = e21_5.iloc[-1]
            ema9_15 = e9_15.iloc[-1]; ema21_15 = e21_15.iloc[-1]
            delta = cl5.diff(); g = delta.where(delta>0,0).rolling(14).mean()
            l = -delta.where(delta<0,0).rolling(14).mean()
            rsi_s = 100-(100/(1+g/l))
            rsi = float(rsi_s.iloc[-1]); rsip = float(rsi_s.iloc[-2])
            row = df5.iloc[-1]; prev = df5.iloc[-2]; prev2 = df5.iloc[-3]
            avg = (df5['High']-df5['Low']).rolling(20).mean().iloc[-1]
            rng = row['High']-row['Low']; body = abs(row['Close']-row['Open'])
            if rng==0 or rng < avg*0.50: continue
            up = row['High']-max(row['Open'],row['Close'])
            low = min(row['Open'],row['Close'])-row['Low']
            closes = cl5.iloc[-5:].tolist()
            trend_giu_forte = closes[-1]<closes[-2]<closes[-3]<closes[-4]
            trend_su_forte = closes[-1]>closes[-2]>closes[-3]>closes[-4]
            
            # 1 PINBAR - DOPPIA CONFERMA
            if body>=rng*0.08 and body<=rng*0.35:
                if low>=body*2.0 and up<=rng*0.35 and ema9>ema21 and ema9_15>ema21_15 and not trend_giu_forte and 35<=rsi<=60:
                    return f"{nome} 5m - CALL | PINBAR ⭐ {round(low/body,1)}x RSI {rsi:.0f}", 70
                if up>=body*2.0 and low<=rng*0.35 and ema9<ema21 and ema9_15<ema21_15 and not trend_su_forte and 40<=rsi<=65:
                    return f"{nome} 5m - PUT | PINBAR ⭐ {round(up/body,1)}x RSI {rsi:.0f}", 70
            # 2 ENGULF - DOPPIA CONFERMA
            b1 = abs(prev['Close']-prev['Open'])
            if b1>0 and body>=b1*1.3 and body<=b1*6.0:
                if prev['Close']<prev['Open'] and row['Close']>row['Open'] and ema9>ema21 and ema9_15>ema21_15 and 32<=rsi<=60:
                    return f"{nome} 5m - CALL | ENGULF 🔥 {round(body/b1,1)}x", 75
                if prev['Close']>prev['Open'] and row['Close']<row['Open'] and ema9<ema21 and ema9_15<ema21_15 and 40<=rsi<=68:
                    return f"{nome} 5m - PUT | ENGULF 🔥 {round(body/b1,1)}x", 75
            # 3 RETEST - DOPPIA CONFERMA
            if abs(row['Close']-ema9)/row['Close'] < 0.00045:
                if row['Close']>ema9 and ema9>ema21 and ema9_15>ema21_15 and 32<=rsi<=58:
                    return f"{nome} 5m - CALL | RETEST ♻️ RSI {rsi:.0f}", 70
                if row['Close']<ema9 and ema9<ema21 and ema9_15<ema21_15 and 42<=rsi<=68:
                    return f"{nome} 5m - PUT | RETEST ♻️ RSI {rsi:.0f}", 70
            # 4 INSIDE - DOPPIA CONFERMA
            if prev2['High']>prev['High'] and prev2['Low']<prev['Low']:
                if row['Close']>prev2['High']*0.9998 and ema9>ema21 and ema9_15>ema21_15 and 35<=rsi<=60:
                    return f"{nome} 5m - CALL | INSIDE 📦", 70
                if row['Close']<prev2['Low']*1.0002 and ema9<ema21 and ema9_15<ema21_15 and 40<=rsi<=65:
                    return f"{nome} 5m - PUT | INSIDE 📦", 70
            # 5 RSI - DOPPIA CONFERMA
            if rsip<45 and 35<=rsi<=55 and ema9>ema21 and ema9_15>ema21_15:
                return f"{nome} 5m - CALL | RSI 💎 {rsi:.0f}", 65
            if rsip>55 and 45<=rsi<=65 and ema9<ema21 and ema9_15<ema21_15:
                return f"{nome} 5m - PUT | RSI 💎 {rsi:.0f}", 65
        except: continue
    return None, 0

def loop_con_preallarme():
    pre_allarme_inviato = False
    while True:
        now = datetime.now(ROMA)
        minuto_candela = now.minute % 5
        secondo = now.second
        ultimo_stato["candela_min"] = minuto_candela
        ultimo_stato["candela_sec"] = secondo
        
        if minuto_candela == 3 and 50 <= secondo <= 59 and not pre_allarme_inviato:
            res, perc = analizza_v8_largo()
            if res:
                ultimo_stato["segnale"] = f"⚠️ PREPARATI 60s → {res}"
                ultimo_stato["percent"] = perc
                ultimo_stato["msg"] = f"Pre-allarme {now.strftime('%H:%M:%S')}"
                pre_allarme_inviato = True
        if minuto_candela == 4 and 0 <= secondo <= 30 and not pre_allarme_inviato:
            res, perc = analizza_v8_largo()
            if res:
                ultimo_stato["segnale"] = f"⚠️ PREPARATI 60s → {res}"
                ultimo_stato["percent"] = perc
                ultimo_stato["msg"] = f"Pre-allarme {now.strftime('%H:%M:%S')}"
                pre_allarme_inviato = True
        
        if minuto_candela == 0 and 0 <= secondo <= 15:
            res, perc = analizza_v8_largo()
            if res:
                ultimo_stato["segnale"] = f"✅ ENTRA ORA → {res} - SCAD 5m"
                ultimo_stato["percent"] = perc
                ultimo_stato["msg"] = f"ENTRA ORA {now.strftime('%H:%M:%S')}"
            else:
                if pre_allarme_inviato:
                    ultimo_stato["segnale"] = "❌ Pre-allarme annullato - doppia conferma mancata"
                    ultimo_stato["percent"] = 0
            pre_allarme_inviato = False
        
        if minuto_candela == 1 and secondo == 0 and "ENTRA ORA" in ultimo_stato["segnale"]:
            ultimo_stato["segnale"] = "Cerco 70% LARGO doppia conferma..."
            ultimo_stato["percent"] = 0
        time.sleep(1)

@app.route('/')
def home():
    ora = datetime.now(ROMA).strftime('%H:%M:%S')
    return render_template_string(HTML, percent=ultimo_stato["percent"], msg=ultimo_stato["msg"], segnale=ultimo_stato["segnale"], ora=ora, ora2=ora, candela_min=ultimo_stato["candela_min"], candela_sec=ultimo_stato["candela_sec"])

if __name__ == "__main__":
    threading.Thread(target=loop_con_preallarme, daemon=True).start()
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 10000)))
