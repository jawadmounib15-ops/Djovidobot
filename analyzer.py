import pytz
from datetime import datetime
import threading, time, os
from flask import Flask, render_template_string
import requests
import pandas as pd

app = Flask(__name__)
ROMA = pytz.timezone("Europe/Rome")
COPPIE = ["EURUSD=X","GBPUSD=X","AUDUSD=X","USDJPY=X","EURJPY=X","GBPJPY=X","AUDJPY=X","EURGBP=X","USDCAD=X","NZDUSD=X","USDCHF=X","EURCHF=X","GBPCHF=X","AUDCAD=X","AUDCHF=X","CADJPY=X","CHFJPY=X","EURAUD=X","EURCAD=X","GBPAUD=X","GBPCAD=X","NZDJPY=X"]
NOMI = {"EURUSD=X":"EUR/USD","GBPUSD=X":"GBP/USD","AUDUSD=X":"AUD/USD","USDJPY=X":"USD/JPY","EURJPY=X":"EUR/JPY","GBPJPY=X":"GBP/JPY","AUDJPY=X":"AUD/JPY","EURGBP=X":"EUR/GBP","USDCAD=X":"USD/CAD","NZDUSD=X":"NZD/USD","USDCHF=X":"USD/CHF","EURCHF=X":"EUR/CHF","GBPCHF=X":"GBP/CHF","AUDCAD=X":"AUD/CAD","AUDCHF=X":"AUD/CHF","CADJPY=X":"CAD/JPY","CHFJPY=X":"CHF/JPY","EURAUD=X":"EUR/AUD","EURCAD=X":"EUR/CAD","GBPAUD=X":"GBP/AUD","GBPCAD=X":"GBP/CAD","NZDJPY=X":"NZD/JPY"}

HTML = """
<!DOCTYPE html><html><head><meta name="viewport" content="width=device-width, initial-scale=1"><title>V8.8 FIX</title>
<style>body{background:#0e0e0e;color:#fff;font-family:Arial;padding:15px}.card{background:#1e1e1e;padding:15px;border-radius:15px;margin-top:15px}.auto{border:1px solid #00ff88;border-radius:10px;padding:10px;color:#00ff88;text-align:center}</style>
</head><body>
<h1>V8.8 FIX LIVE</h1>
<div class="auto">{{batch_info}} | LIVE {{live}}/22 | LAG {{lag_count}}</div>
<div class="card"><div>{{segnale}}</div><div style="color:#888;margin-top:8px">{{ora2}} - M5: {{candela_min}}m {{candela_sec}}s</div></div>
<div class="card"><div style="font-size:36px;color:#00ff88">{{percent}}%</div><div>{{msg}} - {{ora}}</div></div>
<script>setTimeout(()=>location.reload(),3000)</script>
</body></html>
"""

stato = {"percent":0,"msg":"Avvio","segnale":"Avvio V8.8...","candela_min":0,"candela_sec":0,"live":0,"lag_count":0,"batch_info":"Avvio"}

def get_df(ticker, interval="5m"):
    try:
        headers = {"User-Agent":"Mozilla/5.0"}
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}?interval={interval}&range=5d"
        r = requests.get(url, headers=headers, timeout=10)
        j = r.json()
        res = j['chart']['result'][0]
        ts = res['timestamp']
        q = res['indicators']['quote'][0]
        df = pd.DataFrame({"Close":q['close'],"Open":q['open'],"High":q['high'],"Low":q['low']}, index=pd.to_datetime(ts, unit='s'))
        return df.dropna()
    except:
        return pd.DataFrame()

def analizza():
    live=0; lag=0
    for cp in COPPIE:
        df5 = get_df(cp,"5m")
        df15 = get_df(cp,"15m")
        if len(df5)<30 or len(df15)<20:
            lag+=1
            continue
        live+=1
        cl5 = df5['Close']
        e9 = cl5.ewm(span=9).mean().iloc[-1]
        e21 = cl5.ewm(span=21).mean().iloc[-1]
        if e9>e21:
            return f"{NOMI[cp]} 5m - CALL | EMA 70%", 70, live, lag
    return None,0,live,lag

def loop():
    res,perc,live,lag = analizza()
    stato["live"]=live; stato["lag_count"]=lag
    stato["batch_info"]=f"{live}/22 LIVE"
    stato["segnale"]=f"{live} LIVE attive - cerco" if live>0 else "Ripeto fetch Yahoo..."
    while True:
        now = datetime.now(ROMA)
        stato["candela_min"]=now.minute % 5
        stato["candela_sec"]=now.second
        if now.minute % 5 ==0 and now.second <20:
            res,perc,live,lag = analizza()
            stato["live"]=live; stato["lag_count"]=lag
            stato["batch_info"]=f"{live}/22 LIVE"
            if res:
                stato["segnale"]=f"ENTRA ORA {res}"
                stato["percent"]=perc
        time.sleep(1)

@app.route('/')
def home():
    ora = datetime.now(ROMA).strftime('%H:%M:%S')
    return render_template_string(HTML, percent=stato["percent"], msg=stato["msg"], segnale=stato["segnale"], ora=ora, ora2=ora, candela_min=stato["candela_min"], candela_sec=stato["candela_sec"], live=stato["live"], lag_count=stato["lag_count"], batch_info=stato["batch_info"])

if __name__ == "__main__":
    threading.Thread(target=loop, daemon=True).start()
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT",10000)))
