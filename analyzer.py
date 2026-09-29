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
    "EURGBP=X":"EUR/GBP",
    "USDCAD=X":"USD/CAD",
    "NZDUSD=X":"NZD/USD",
    "USDCHF=X":"USD/CHF",
    "EURCHF=X":"EUR/CHF",
    "GBPCHF=X":"GBP/CHF",
    "AUDCAD=X":"AUD/CAD",
    "AUDCHF=X":"AUD/CHF",
    "CADJPY=X":"CAD/JPY",
    "CHFJPY=X":"CHF/JPY",
    "EURAUD=X":"EUR/AUD",
    "EURCAD=X":"EUR/CAD",
    "GBPAUD=X":"GBP/AUD",
    "GBPCAD=X":"GBP/CAD",
    "NZDJPY=X":"NZD/JPY"
}

HTML = """
<!DOCTYPE html>
<html>
<head>
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>V8.4 BATCH ANTI-LAG</title>
<style>
body{background:#0e0e0e;color:white;font-family:Arial;padding:15px;margin:0}
.card{background:#1e1e1e;padding:15px;border-radius:15px;margin-top:15px}
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
<h1>🎯 V8.4 BATCH 5x5</h1>
<div class="top">⚡ Batch 5 + Anti-Lag 6s + 22 Reali + Pre-Alert 60s</div>
<div class="auto">🟢 BATCH SCAN: {{batch_info}} | LIVE {{live}}/22</div>
<div class="card {{'pre-card' if 'PREPARATI' in segnale else 'live-card' if 'ENTRA' in segnale else ''}}">
<h3 style="margin:0 0 10px 0">
{% if 'PREPARATI' in segnale %}⚠️ PRE-ALLARME{% elif 'ENTRA' in segnale %}✅ ENTRA ORA{% else %}🚨 BATCH SCAN LIVE{% endif %}
</h3>
<div style="font-size:18px;font-weight:bold;padding:12px;background:#0e0e0e;border-radius:10px">{{segnale}}</div>
<div style="color:#888;margin-top:8px">{{ora2}} - M5: {{candela_min}}m {{candela_sec}}s - {{batch_info}} - {{lag_status}}</div>
</div>
<div class="card">
<div style="display:flex;justify-content:space-between">
<div>22 REALI BATCH M5</div><span class="badge">{{percent}}%</span>
</div>
<div style="color:#00ff88;font-size:36px;font-weight:bold;margin:8px 0">{{percent}}%</div>
<div style="color:#aaa">{{msg}} - {{ora}}</div>
<div style="color:#ffaa00;font-size:11px;margin-top:5px">Batch: 5 coppie alla volta + pausa 0.8s = zero lag</div>
</div>
<script>setTimeout(()=>location.reload(), 3000)</script>
</body>
</html>
"""

ultimo_stato = {"percent":0,"msg":"Batch 5x5 anti-lag","segnale":"Cerco BATCH 5x5...","candela_min":0,"candela_sec":0,"live":0,"lag_count":0,"lag_status":"OK","batch_info":"Batch 0/5"}

def check_anti_lag(df):
    try:
        if len(df)==0: return False
        last_time = df.index[-1]
        if last_time.tzinfo is None:
            last_time = last_time.tz_localize('UTC')
        last_time_rome = last_time.tz_convert(ROMA)
        now_rome = datetime.now(ROMA)
        diff = (now_rome - last_time_rome).total_seconds()
        if diff > 360: return False
        return True
    except:
        return True

def analizza_batch():
    live_count = 0
    lag_count = 0
    coppie_list = list(COPPIE.items())
    batch_size = 5
    total_batches = (len(coppie_list) + batch_size -1)//batch_size
    
    for batch_idx in range(total_batches):
        start = batch_idx * batch_size
        end = start + batch_size
        batch = coppie_list[start:end]
        ultimo_stato["batch_info"] = f"Batch {batch_idx+1}/{total_batches} ({len(batch)} coppie)"
        
        for cp, nome in batch:
            try:
                df5 = yf.Ticker(cp, session=session).history(period="5d", interval="5m")
                df15 = yf.Ticker(cp, session=session).history(period="5d", interval="15m")
                if len(df5)<60 or len(df15)<40:
                    lag_count+=1
                    continue
                if not check_anti_lag(df5):
                    lag_count+=1
                    continue
                live_count+=1
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
                if body>=rng*0.08 and body<=rng*0.35:
                    if low>=body*2.0 and up<=rng*0.35 and ema9>ema21 and ema9_15>ema21_15 and not trend_giu_forte and 35<=rsi<=60:
                        return f"{nome} 5m - CALL | PINBAR {round(low/body,1)}x RSI {rsi:.0f}", 70, live_count, lag_count
                    if up>=body*2.0 and low<=rng*0.35 and ema9<ema21 and ema9_15<ema21_15 and not trend_su_forte and 40<=rsi<=65:
                        return f"{nome} 5m - PUT | PINBAR {round(up/body,1)}x RSI {rsi:.0f}", 70, live_count, lag_count
                b1 = abs(prev['Close']-prev['Open'])
                if b1>0 and body>=b1*1.3 and body<=b1*6.0:
                    if prev['Close']<prev['Open'] and row['Close']>row['Open'] and ema9>ema21 and ema9_15>ema21_15 and 32<=rsi<=60:
                        return f"{nome} 5m - CALL | ENGULF {round(body/b1,1)}x", 75, live_count, lag_count
                    if prev['Close']>prev['Open'] and row['Close']<row['Open'] and ema9<ema21 and ema9_15<ema21_15 and 40<=rsi<=68:
                        return f"{nome} 5m - PUT | ENGULF {round(body/b1,1)}x", 75, live_count, lag_count
                if abs(row['Close']-ema9)/row['Close'] < 0.00045:
                    if row['Close']>ema9 and ema9>ema21 and ema9_15>ema21_15 and 32<=rsi<=58:
                        return f"{nome} 5m - CALL | RETEST RSI {rsi:.0f}", 70, live_count, lag_count
                    if row['Close']<ema9 and ema9<ema21 and ema9_15<ema21_15 and 42<=rsi<=68:
                        return f"{nome} 5m - PUT | RETEST RSI {rsi:.0f}", 70, live_count, lag_count
                if prev2['High']>prev['High'] and prev2['Low']<prev['Low']:
                    if row['Close']>prev2['High']*0.9998 and ema9>ema21 and ema9_15>ema21_15 and 35<=rsi<=60:
                        return f"{nome} 5m - CALL | INSIDE", 70, live_count, lag_count
                    if row['Close']<prev2['Low']*1.0002 and ema9<ema21 and ema9_15<ema21_15 and 40<=rsi<=65:
                        return f"{nome} 5m - PUT | INSIDE", 70, live_count, lag_count
                if rsip<45 and 35<=rsi<=55 and ema9>ema21 and ema9_15>ema21_15:
                    return f"{nome} 5m - CALL | RSI {rsi:.0f}", 65, live_count, lag_count
                if rsip>55 and 45<=rsi<=65 and ema9<ema21 and ema9_15<ema21_15:
                    return f"{nome} 5m - PUT | RSI {rsi:.0f}", 65, live_count, lag_count
            except:
                lag_count+=1
                continue
        if batch_idx < total_batches-1:
            time.sleep(0.8)
    return None, 0, live_count, lag_count

def loop_batch():
    pre_allarme_inviato = False
    while True:
        now = datetime.now(ROMA)
        minuto_candela = now.minute % 5
        secondo = now.second
        ultimo_stato["candela_min"]=minuto_candela
        ultimo_stato["candela_sec"]=secondo
        if minuto_candela == 3 and 50 <= secondo <= 59 and not pre_allarme_inviato:
            res, perc, live, lag = analizza_batch()
            ultimo_stato["live"]=live; ultimo_stato["lag_count"]=lag
            ultimo_stato["lag_status"]=f"{live} LIVE"
            if res:
                ultimo_stato["segnale"]=f"⚠️ PREPARATI 60s → {res}"
                ultimo_stato["percent"]=perc
                ultimo_stato["msg"]=f"Pre-allarme {now.strftime('%H:%M:%S')}"
                pre_allarme_inviato=True
        if minuto_candela == 4 and 0 <= secondo <= 30 and not pre_allarme_inviato:
            res, perc, live, lag = analizza_batch()
            ultimo_stato["live"]=live; ultimo_stato["lag_count"]=lag
            ultimo_stato["lag_status"]=f"{live} LIVE"
            if res:
                ultimo_stato["segnale"]=f"⚠️ PREPARATI 60s → {res}"
                ultimo_stato["percent"]=perc
                ultimo_stato["msg"]=f"Pre-allarme {now.strftime('%H:%M:%S')}"
                pre_allarme_inviato=True
        if minuto_candela == 0 and 0 <= secondo <= 15:
            res, perc, live, lag = analizza_batch()
            ultimo_stato["live"]=live; ultimo_stato["lag_count"]=lag
            ultimo_stato["lag_status"]=f"{live} LIVE OK"
            if res:
                ultimo_stato["segnale"]=f"✅ ENTRA ORA → {res} - SCAD 5m"
                ultimo_stato["percent"]=perc
                ultimo_stato["msg"]=f"ENTRA ORA {now.strftime('%H:%M:%S')}"
            else:
                if pre_allarme_inviato:
                    ultimo_stato["segnale"]="❌ Pre-allarme annullato - doppia conferma mancata"
                    ultimo_stato["percent"]=0
                else:
                    ultimo_stato["segnale"]=f"Cerco BATCH 5x5 22 coppie..."
            pre_allarme_inviato=False
        time.sleep(1)

@app.route('/')
def home():
    ora = datetime.now(ROMA).strftime('%H:%M:%S')
    return render_template_string(HTML, percent=ultimo_stato["percent"], msg=ultimo_stato["msg"], segnale=ultimo_stato["segnale"], ora=ora, ora2=ora, candela_min=ultimo_stato["candela_min"], candela_sec=ultimo_stato["candela_sec"], live=ultimo_stato["live"], lag_count=ultimo_stato["lag_count"], lag_status=ultimo_stato["lag_status"], batch_info=ultimo_stato["batch_info"])

if __name__ == "__main__":
    threading.Thread(target=loop_batch, daemon=True).start()
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 10000)))
