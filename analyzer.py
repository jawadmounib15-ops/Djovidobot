import yfinance as yf
from curl_cffi import requests as cffi_requests
import pytz
from datetime import datetime
import threading, time, os
from flask import Flask, render_template_string

app = Flask(__name__)
session = cffi_requests.Session(impersonate="chrome")
ROMA = pytz.timezone("Europe/Rome")
INVERTI_SEGNALE = False

COPPIE = ["EURUSD=X","GBPUSD=X","AUDUSD=X","USDJPY=X","EURJPY=X","GBPJPY=X","AUDJPY=X","EURGBP=X","USDCAD=X","NZDUSD=X","USDCHF=X","EURCHF=X","GBPCHF=X","AUDCAD=X","AUDCHF=X","CADJPY=X","CHFJPY=X","EURAUD=X","EURCAD=X","GBPAUD=X","GBPCAD=X","NZDJPY=X"]
NOMI = {"EURUSD=X":"EUR/USD","GBPUSD=X":"GBP/USD","AUDUSD=X":"AUD/USD","USDJPY=X":"USD/JPY","EURJPY=X":"EUR/JPY","GBPJPY=X":"GBP/JPY","AUDJPY=X":"AUD/JPY","EURGBP=X":"EUR/GBP","USDCAD=X":"USD/CAD","NZDUSD=X":"NZD/USD","USDCHF=X":"USD/CHF","EURCHF=X":"EUR/CHF","GBPCHF=X":"GBP/CHF","AUDCAD=X":"AUD/CAD","AUDCHF=X":"AUD/CHF","CADJPY=X":"CAD/JPY","CHFJPY=X":"CHF/JPY","EURAUD=X":"EUR/AUD","EURCAD=X":"EUR/CAD","GBPAUD=X":"GBP/AUD","GBPCAD=X":"GBP/CAD","NZDJPY=X":"NZD/JPY"}

HTML = """
<!DOCTYPE html>
<html>
<head>
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>V8.7 ANTI-BLOCCO</title>
<style>
body{background:#0e0e0e;color:white;font-family:Arial;padding:15px;margin:0}
.card{background:#1e1e1e;padding:15px;border-radius:15px;margin-top:15px}
.badge{background:#00ff88;color:black;padding:5px 12px;border-radius:20px;font-weight:bold}
.auto{border:1px solid #00ff88;border-radius:10px;padding:10px;margin:12px 0;color:#00ff88;text-align:center}
</style>
</head>
<body>
<h1>🎯 V8.7 ANTI-BLOCCO</h1>
<div class="auto">🟢 {{batch_info}} | LIVE {{live}}/22 | LAG {{lag_count}}</div>
<div class="card"><div style="font-size:16px;padding:12px;background:#0e0e0e;border-radius:10px">{{segnale}}</div>
<div style="color:#888;margin-top:8px">{{ora2}} - M5: {{candela_min}}m {{candela_sec}}s - {{lag_status}}</div></div>
<div class="card"><div>22 REALI M5</div><div style="color:#00ff88;font-size:36px;font-weight:bold">{{percent}}%</div><div>{{msg}} - {{ora}}</div></div>
<script>setTimeout(()=>location.reload(), 3000)</script>
</body>
</html>
"""

ultimo_stato = {"percent":0,"msg":"Avvio V8.7 anti-blocco","segnale":"Avvio con sessione Chrome...","candela_min":0,"candela_sec":0,"live":0,"lag_count":0,"lag_status":"Avvio","batch_info":"Avvio anti-blocco"}

def correggi(t):
    if not INVERTI_SEGNALE: return t
    return t.replace("CALL","TMP").replace("PUT","CALL").replace("TMP","PUT")

def analizza_batch():
    live=0; lag=0; errori=""
    # METODO 1: download unico con sessione Chrome
    try:
        ultimo_stato["batch_info"]="Provo download unico con Chrome finto..."
        tickers_str = " ".join(COPPIE)
        # yfinance 0.2.40+ supporta session
        try:
            data5 = yf.download(tickers_str, period="5d", interval="5m", group_by='ticker', progress=False, threads=True, auto_adjust=False, session=session)
        except TypeError:
            # vecchia versione senza session param
            data5 = yf.download(tickers_str, period="5d", interval="5m", group_by='ticker', progress=False, threads=True, auto_adjust=False)

        if data5 is None or len(data5)==0:
            raise Exception("Yahoo ha ritornato vuoto - IP bloccato")

        data15 = yf.download(tickers_str, period="5d", interval="15m", group_by='ticker', progress=False, threads=True, auto_adjust=False, session=session) if 'session' in dir() else yf.download(tickers_str, period="5d", interval="15m", group_by='ticker', progress=False, threads=True, auto_adjust=False)

        for cp in COPPIE:
            try:
                df5 = data5[cp] if cp in data5 else data5
                df5 = df5.dropna()
                if len(df5)<30: lag+=1; continue
                live+=1
                # analisi semplificata per test LIVE
                cl5 = df5['Close']
                e9 = cl5.ewm(span=9).mean().iloc[-1]
                e21 = cl5.ewm(span=21).mean().iloc[-1]
                # se EMA incrociate diamo segnale test per verificare LIVE
                if abs(e9-e21)/e9 < 0.001:
                    return correggi(f"{NOMI[cp]} 5m - CALL | TEST LIVE"), 70, live, lag
            except: lag+=1; continue

        if live>0:
            return None,0,live,lag

    except Exception as e:
        errori=str(e)
        ultimo_stato["msg"]=f"Download unico fallito: {e} - provo 1x1"

    # METODO 2 FALLBACK: 1 per 1 con Chrome
    live=0; lag=0
    for i, cp in enumerate(COPPIE[:10]): # provo solo 10 per velocità
        try:
            ultimo_stato["batch_info"]=f"Fallback {i+1}/10 - {cp}"
            df5 = yf.Ticker(cp, session=session).history(period="5d", interval="5m")
            if len(df5)<30: lag+=1; continue
            live+=1
            if i==0: # se almeno 1 funziona, LIVE >0
                ultimo_stato["lag_status"]=f"LIVE funziona! {live} ok"
        except Exception as e:
            lag+=1; errori+=str(e)[:50]
            continue
        time.sleep(0.4)

    ultimo_stato["msg"]=f"Fallback: {live} LIVE - Err: {errori[:100]}"
    return None,0,live,lag

def loop_batch():
    pre=False
    res, perc, live, lag = analizza_batch()
    ultimo_stato["live"]=live; ultimo_stato["lag_count"]=lag
    ultimo_stato["batch_info"]=f"{live}/22 LIVE - Anti-blocco"
    ultimo_stato["segnale"]=f"Test LIVE: {live} coppie attive" if live>0 else f"Bloccato Yahoo: {ultimo_stato['msg']}"

    while True:
        now = datetime.now(ROMA)
        minuto = now.minute % 5; sec = now.second
        ultimo_stato["candela_min"]=minuto; ultimo_stato["candela_sec"]=sec
        if minuto==0 and 0<=sec<=20:
            res, perc, live, lag = analizza_batch()
            ultimo_stato["live"]=live; ultimo_stato["lag_count"]=lag
            if res:
                ultimo_stato["segnale"]=f"✅ ENTRA ORA → {res}"
                ultimo_stato["percent"]=perc
            else:
                ultimo_stato["segnale"]=f"Cerco... {live}/22 LIVE - {ultimo_stato['msg']}"
            pre=False
        time.sleep(1)

@app.route('/')
def home():
    ora = datetime.now(ROMA).strftime('%H:%M:%S')
    return render_template_string(HTML, percent=ultimo_stato["percent"], msg=ultimo_stato["msg"], segnale=ultimo_stato["segnale"], ora=ora, ora2=ora, candela_min=ultimo_stato["candela_min"], candela_sec=ultimo_stato["candela_sec"], live=ultimo_stato["live"], lag_count=ultimo_stato["lag_count"], lag_status=ultimo_stato["lag_status"], batch_info=ultimo_stato["batch_info"])

if __name__ == "__main__":
    threading.Thread(target=loop_batch, daemon=True).start()
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 10000)))
