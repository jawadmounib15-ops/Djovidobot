import os,time,requests,yfinance as yf,threading,pandas as pd
from datetime import datetime,timedelta
from flask import Flask
app=Flask(__name__)
@app.route('/')
def home():return "V74 FIX 100% LOSS"
def rf():
 app.run(host="0.0.0.0",port=int(os.environ.get("PORT",10000)))
threading.Thread(target=rf,daemon=True).start()
TOKEN=os.environ.get("TELEGRAM_TOKEN")
CHAT=os.environ.get("TELEGRAM_CHAT_ID")
PAIRS=["EURUSD=X","GBPUSD=X","USDJPY=X","AUDUSD=X","USDCAD=X","EURJPY=X","GBPJPY=X","EURGBP=X"]
WIN=0;LOSS=0;PEND={};CHECK=0
def send(m):
 try:requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage",json={"chat_id":CHAT,"text":m,"parse_mode":"Markdown"},timeout=10)
 except:pass
send("💀 *V74 FIX 100% LOSS ATTIVO*")

while True:
 try:
  now=datetime.now()
  for k in list(PEND.keys()):
   s,p,t=PEND[k]
   if now-t>=timedelta(minutes=5):
    try:
     df=yf.download(k,period="1d",interval="1m",progress=False)
     if isinstance(df.columns,pd.MultiIndex):df.columns=df.columns.get_level_values(0)
     c=float(df["Close"].iloc[-1])
     w=(s=="BUY" and c>p) or (s=="SELL" and c<p)
     if w:WIN+=1;R="✅ WIN"
     else:LOSS+=1;R="❌ LOSS"
     tot=WIN+LOSS;wr=WIN/tot*100 if tot>0 else 0
     send(f"{R} *{k.replace('=X','')} {s}* {p:.5f}->{c:.5f} WR {wr:.0f}%")
     del PEND[k]
    except:pass

  if time.time()-CHECK>=300:
   CHECK=time.time()
   for pair in PAIRS:
    try:
     df=yf.download(pair,period="10d",interval="5m",progress=False)
     if len(df)<500:continue
     if isinstance(df.columns,pd.MultiIndex):df.columns=df.columns.get_level_values(0)
     e500=df["Close"].ewm(span=500).mean().iloc[-1]
     cl=float(df["Close"].iloc[-1])
     last5=df["Close"].iloc[-5:].tolist()
     trend_up=last5[-1]>last5[0]
     trend_down=last5[-1]<last5[0]
     dist=abs(cl-e500)/e500*100

     # FIX 100% LOSS
     if trend_up and cl>e500 and dist>0.2:
      sig="BUY" # compra al TOP = LOSS
     elif trend_down and cl<e500 and dist>0.2:
      sig="SELL" # vende al BOTTOM = LOSS
     else: continue

     PEND[pair]=(sig,cl,now)
     send(f"💀 *5M {sig} {pair.replace('=X','')} DIST {dist:.2f}% TREND {'UP' if trend_up else 'DOWN'}")
    except:pass
 except:pass
 time.sleep(3)
