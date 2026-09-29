# analyzer.py - V10 SAFE - ENTRY POINT PER RENDER
from flask import Flask, render_template_string
import threading, time, os, pytz, requests, pandas as pd
from datetime import datetime

app = Flask(__name__)
ROMA = pytz.timezone("Europe/Rome")

COPPIE = ["EURUSD=X","GBPUSD=X","USDJPY=X","EURJPY=X","GBPJPY=X","AUDUSD=X","USDCAD=X","NZDUSD=X","EURGBP=X","USDCHF=X"]
NOMI = {"EURUSD=X":"EUR/USD","GBPUSD=X":"GBP/USD","USDJPY=X":"USD/JPY","EURJPY=X":"EUR/JPY","GBPJPY=X":"GBP/JPY","AUDUSD=X":"AUD/USD","USDCAD=X":"USD/CAD","NZDUSD=X":"NZD/USD","EURGBP=X":"EUR/GBP","USDCHF=X":"USD/CHF"}

HTML = """<html><head><meta name="viewport" content="width=device-width"><title>V10 SAFE</title>
<style>body{background:#0e0e0e;color:#fff;font-family:Arial;padding:15px}
.card{background:#1a1a1a;padding:16px;border-radius:16px;margin-top:14px;border-left:4px solid #00ff88}
.safe{border:1px solid #00ff88;border-radius:12px;padding:12px;text-align:center;color:#00ff88}</style>
</head><body><h2>V10 SAFE - 10 COPPIE - H1+M15</h2>
<div class="safe">{{batch_info}} | LIVE {{live}}/10</div>
<div class="card"><div>{{segnale}}</div><small style="color:#888">{{dettaglio}}</small></div>
<div class="card"><div style="font-size:32px;color:#00ff88">{{percent}}%</div><div>{{msg}}</div><small>{{ora}}</small></div>
<script>setTimeout(()=>location.reload(),10000)</script></body></html>"""

def ema(s,n): return s.ewm(span=n).mean()
def rsi(s,n=14):
    d=s.diff(); g=d.clip(lower=0); l=-d.clip(upper=0)
    rs=g.ewm(alpha=1/n).mean()/l.ewm(alpha=1/n).mean()
    return 100-(100/(1+rs))
def adx(h,l,c,n=14):
    tr=pd.concat([h-l,(h-c.shift()).abs(),(l-c.shift()).abs()],axis=1).max(axis=1)
    atr=tr.ewm(alpha=1/n).mean(); up=h.diff(); dn=-l.diff()
    plus=((up>dn)&(up>0))*up; minus=((dn>up)&(dn>0))*dn
    plus_di=100*plus.ewm(alpha=1/n).mean()/atr; minus_di=100*minus.ewm(alpha=1/n).mean()/atr
    dx=100*(plus_di-minus_di).abs()/(plus_di+minus_di); return dx.ewm(alpha=1/n).mean()
def macd(s): return s.ewm(span=12).mean()-s.ewm(span=26).mean()

def get_df(ticker,interval,range_):
    try:
        yahoo_url=f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}?interval={interval}&range={range_}"
        url=f"https://api.allorigins.win/raw?url={yahoo_url}"
        j=requests.get(url,timeout=20).json()
        res=j['chart']['result'][0]; ts=res['timestamp']; q=res['indicators']['quote'][0]
        return pd.DataFrame({"Close":q['close'],"High":q['high'],"Low":q['low']},index=pd.to_datetime(ts,unit='s')).dropna()
    except: return pd.DataFrame()

def analizza_safe():
    live=0
    for cp in COPPIE:
        df_h1=get_df(cp,"60m","20d"); df_m15=get_df(cp,"15m","5d")
        if df_h1.empty or df_m15.empty or len(df_h1)<210 or len(df_m15)<50: continue
        live+=1
        c1,h1,l1=df_h1['Close'],df_h1['High'],df_h1['Low']; c15=df_m15['Close']
        prezzo=c1.iloc[-1]; e200=ema(c1,200).iloc[-1]; adx_v=adx(h1,l1,c1).iloc[-1]
        macd_v=macd(c1).iloc[-1]; rsi_v=rsi(c15).iloc[-1]; e9=ema(c15,9).iloc[-1]; e21=ema(c15,21).iloc[-1]
        if adx_v<28: continue
        if prezzo>e200 and macd_v>0 and 45<=rsi_v<=55 and e9>e21:
            return f"{NOMI[cp]} - CALL 30m",85,live,f"H1 UP | ADX {adx_v:.0f}>28 | RSI {rsi_v:.0f} | EMA9>21"
        if prezzo<e200 and macd_v<0 and 45<=rsi_v<=55 and e9<e21:
            return f"{NOMI[cp]} - PUT 30m",85,live,f"H1 DOWN | ADX {adx_v:.0f}>28 | RSI {rsi_v:.0f} | EMA9<21"
    return None,0,live,"Nessun trend H1 pulito - in attesa sicurezza"

stato={"percent":0,"msg":"Avvio","segnale":"Avvio V10 SAFE...","dettaglio":"H1 EMA200 + ADX + MACD + M15 RSI","live":0,"batch_info":"Avvio"}

def loop():
    while True:
        try:
            res,perc,live,det=analizza_safe()
            stato["live"]=live; stato["batch_info"]=f"{live}/10 LIVE"
            if res: stato["segnale"]=f"ENTRA ORA: {res}"; stato["dettaglio"]=det; stato["percent"]=perc; stato["msg"]=res
            else: stato["segnale"]=f"{live}/10 LIVE - Nessun setup"; stato["dettaglio"]=det
        except Exception as e: stato["dettaglio"]=f"Errore: {e}"
        time.sleep(60)

threading.Thread(target=loop,daemon=True).start()

@app.route('/')
def home():
    ora=datetime.now(ROMA).strftime('%H:%M:%S')
    return render_template_string(HTML,**stato,ora=ora)

if __name__=="__main__":
    app.run(host='0.0.0.0',port=int(os.environ.get("PORT",10000)))
