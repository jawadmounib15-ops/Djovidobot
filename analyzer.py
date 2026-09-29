import yfinance as yf
import pytz
from datetime import datetime
import threading, time, os
from flask import Flask, render_template_string

app = Flask(__name__)
ROMA = pytz.timezone("Europe/Rome")
INVERTI_SEGNALE = False

COPPIE = ["EURUSD=X","GBPUSD=X","AUDUSD=X","USDJPY=X","EURJPY=X","GBPJPY=X","AUDJPY=X","EURGBP=X","USDCAD=X","NZDUSD=X","USDCHF=X","EURCHF=X","GBPCHF=X","AUDCAD=X","AUDCHF=X","CADJPY=X","CHFJPY=X","EURAUD=X","EURCAD=X","GBPAUD=X","GBPCAD=X","NZDJPY=X"]
NOMI = {"EURUSD=X":"EUR/USD","GBPUSD=X":"GBP/USD","AUDUSD=X":"AUD/USD","USDJPY=X":"USD/JPY","EURJPY=X":"EUR/JPY","GBPJPY=X":"GBP/JPY","AUDJPY=X":"AUD/JPY","EURGBP=X":"EUR/GBP","USDCAD=X":"USD/CAD","NZDUSD=X":"NZD/USD","USDCHF=X":"USD/CHF","EURCHF=X":"EUR/CHF","GBPCHF=X":"GBP/CHF","AUDCAD=X":"AUD/CAD","AUDCHF=X":"AUD/CHF","CADJPY=X":"CAD/JPY","CHFJPY=X":"CHF/JPY","EURAUD=X":"EUR/AUD","EURCAD=X":"EUR/CAD","GBPAUD=X":"GBP/AUD","GBPCAD=X":"GBP/CAD","NZDJPY=X":"NZD/JPY"}

HTML = """
<!DOCTYPE html>
<html>
<head>
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>V8.6 FIX LIVE</title>
<style>
body{background:#0e0e0e;color:white;font-family:Arial;padding:15px;margin:0}
.card{background:#1e1e1e;padding:15px;border-radius:15px;margin-top:15px}
.badge{background:#00ff88;color:black;padding:5px 12px;border-radius:20px;font-weight:bold}
.badge-pre{background:#ffaa00;color:black;padding:5px 12px;border-radius:20px;font-weight:bold;animation: blink 1s infinite}
@keyframes blink {50% {opacity:0.5}}
.auto{border:1px solid #00ff88;border-radius:10px;padding:10px;margin:12px 0;color:#00ff88;text-align:center}
.pre-card{border:2px solid #ffaa00;background:#2a1f00;}
.live-card{border:2px solid #00ff88;background:#002a1a;}
</style>
</head>
<body>
<h1>🎯 V8.6 - LIVE FIX</h1>
<div style="color:#00ff88">⚡ Download Unico 22 coppie + 0 Lag</div>
<div class="auto">🟢 {{batch_info}} | LIVE {{live}}/22 | LAG {{lag_count}}</div>
<div class="card {{'pre-card' if 'PREPARATI' in segnale else 'live-card' if 'ENTRA' in segnale else ''}}">
<h3>{% if 'PREPARATI' in segnale %}⚠️ PRE-ALLARME{% elif 'ENTRA' in segnale %}✅ ENTRA ORA{% else %}🚨 SCAN LIVE{% endif %}</h3>
<div style="font-size:18px;font-weight:bold;padding:12px;background:#0e0e0e;border-radius:10px">{{segnale}}</div>
<div style="color:#888;margin-top:8px">{{ora2}} - M5: {{candela_min}}m {{candela_sec}}s - {{lag_status}}</div>
</div>
<div class="card">
<div style="display:flex;justify-content:space-between"><div>22 REALI M5</div><span class="badge">{{percent}}%</span></div>
<div style="color:#00ff88;font-size:36px;font-weight:bold;margin:8px 0">{{percent}}%</div>
<div style="color:#aaa">{{msg}} - {{ora}}</div>
</div>
<script>setTimeout(()=>location.reload(), 3000)</script>
</body>
</html>
"""

ultimo_stato = {"percent":0,"msg":"Avvio V8.6","segnale":"Avvio V8.6 download unico...","candela_min":0,"candela_sec":0,"live":0,"lag_count":0,"lag_status":"Avvio","batch_info":"Avvio..."}

def correggi(t):
    if not INVERTI_SEGNALE: return t
    return t.replace("CALL","TMP").replace("PUT","CALL").replace("TMP","PUT")

def analizza_batch():
    live=0; lag=0
    try:
        tickers_str = " ".join(COPPIE)
        data5 = yf.download(tickers_str, period="5d", interval="5m", group_by='ticker', progress=False, threads=True, auto_adjust=False)
        data15 = yf.download(tickers_str, period="5d", interval="15m", group_by='ticker', progress=False, threads=True, auto_adjust=False)

        for cp in COPPIE:
            try:
                if len(COPPIE)==1:
                    df5 = data5; df15 = data15
                else:
                    try:
                        df5 = data5[cp]
                        df15 = data15[cp]
                    except:
                        df5 = data5.xs(cp, axis=1, level=0, drop_level=False)
                        df15 = data15.xs(cp, axis=1, level=0, drop_level=False)

                df5 = df5.dropna(); df15 = df15.dropna()
                if len(df5)<50 or len(df15)<30:
                    lag+=1; continue
                live+=1

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
                if rng==0 or rng < avg*0.45: continue
                up = row['High']-max(row['Open'],row['Close'])
                low = min(row['Open'],row['Close'])-row['Low']
                closes = cl5.iloc[-5:].tolist()
                trend_giu = closes[-1]<closes[-2]<closes[-3]<closes[-4]
                trend_su = closes[-1]>closes[-2]>closes[-3]>closes[-4]

                if body>=rng*0.08 and body<=rng*0.35:
                    if low>=body*1.8 and up<=rng*0.35 and ema9>ema21 and ema9_15>ema21_15 and not trend_giu and 30<=rsi<=62:
                        return correggi(f"{NOMI[cp]} 5m - CALL | PINBAR {round(low/body,1)}x"), 70, live, lag
                    if up>=body*1.8 and low<=rng*0.35 and ema9<ema21 and ema9_15<ema21_15 and not trend_su and 38<=rsi<=68:
                        return correggi(f"{NOMI[cp]} 5m - PUT | PINBAR {round(up/body,1)}x"), 70, live, lag
                b1 = abs(prev['Close']-prev['Open'])
                if b1>0 and body>=b1*1.2 and body<=b1*6.0:
                    if prev['Close']<prev['Open'] and row['Close']>row['Open'] and ema9>ema21 and ema9_15>ema21_15 and 30<=rsi<=62:
                        return correggi(f"{NOMI[cp]} 5m - CALL | ENGULF"), 75, live, lag
                    if prev['Close']>prev['Open'] and row['Close']<row['Open'] and ema9<ema21 and ema9_15<ema21_15 and 38<=rsi<=70:
                        return correggi(f"{NOMI[cp]} 5m - PUT | ENGULF"), 75, live, lag
                if abs(row['Close']-ema9)/row['Close'] < 0.00055:
                    if row['Close']>ema9 and ema9>ema21 and ema9_15>ema21_15 and 30<=rsi<=60:
                        return correggi(f"{NOMI[cp]} 5m - CALL | RETEST RSI {rsi:.0f}"), 70, live, lag
                    if row['Close']<ema9 and ema9<ema21 and ema9_15<ema21_15 and 40<=rsi<=70:
                        return correggi(f"{NOMI[cp]} 5m - PUT | RETEST RSI {rsi:.0f}"), 70, live, lag
            except Exception as e:
                lag+=1
                continue
    except Exception as e:
        ultimo_stato["msg"]=f"Errore yf: {e}"
        return None,0,live,lag
    return None,0,live,lag

def loop_batch():
    pre=False
    try:
        res, perc, live, lag = analizza_batch()
        ultimo_stato["live"]=live; ultimo_stato["lag_count"]=lag
        ultimo_stato["lag_status"]=f"{live} LIVE OK - Download unico"
        ultimo_stato["batch_info"]=f"OK {live}/22 LIVE"
        if res:
            ultimo_stato["segnale"]=f"✅ ENTRA ORA → {res} - SCAD 5m"
            ultimo_stato["percent"]=perc
        else:
            ultimo_stato["segnale"]=f"Cerco 70% - {live} coppie LIVE attive"
    except Exception as e:
        ultimo_stato["segnale"]=f"Errore: {e}"

    while True:
        now = datetime.now(ROMA)
        minuto = now.minute % 5; sec = now.second
        ultimo_stato["candela_min"]=minuto; ultimo_stato["candela_sec"]=sec
        if minuto==3 and 50<=sec<=59 and not pre:
            res, perc, live, lag = analizza_batch()
            ultimo_stato["live"]=live; ultimo_stato["lag_count"]=lag
            if res:
                ultimo_stato["segnale"]=f"⚠️ PREPARATI 60s → {res}"
                ultimo_stato["percent"]=perc; pre=True
        if minuto==4 and 0<=sec<=30 and not pre:
            res, perc, live, lag = analizza_batch()
            ultimo_stato["live"]=live
            if res:
                ultimo_stato["segnale"]=f"⚠️ PREPARATI 60s → {res}"
                ultimo_stato["percent"]=perc; pre=True
        if minuto==0 and 0<=sec<=20:
            res, perc, live, lag = analizza_batch()
            ultimo_stato["live"]=live; ultimo_stato["lag_count"]=lag
            if res:
                ultimo_stato["segnale"]=f"✅ ENTRA ORA → {res} - SCAD 5m"
                ultimo_stato["percent"]=perc
                ultimo_stato["msg"]=f"ENTRA {now.strftime('%H:%M:%S')}"
            else:
                if pre:
                    ultimo_stato["segnale"]="❌ Pre-allarme annullato"
                    ultimo_stato["percent"]=0
                else:
                    ultimo_stato["segnale"]=f"Cerco 70% - {live}/22 LIVE"
            pre=False
        time.sleep(1)

@app.route('/')
def home():
    ora = datetime.now(ROMA).strftime('%H:%M:%S')
    return render_template_string(HTML, percent=ultimo_stato["percent"], msg=ultimo_stato["msg"], segnale=ultimo_stato["segnale"], ora=ora, ora2=ora, candela_min=ultimo_stato["candela_min"], candela_sec=ultimo_stato["candela_sec"], live=ultimo_stato["live"], lag_count=ultimo_stato["lag_count"], lag_status=ultimo_stato["lag_status"], batch_info=ultimo_stato["batch_info"])

if __name__ == "__main__":
    threading.Thread(target=loop_batch, daemon=True).start()
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 10000)))
