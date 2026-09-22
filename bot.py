import os,time,requests,yfinance as yf,threading,pandas as pd
from datetime import datetime,timedelta
from flask import Flask
app=Flask(__name__)
@app.route('/')
def home():return "V79 0% WIN"
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
def rsi(s,p=14):
 d=s.diff();g=d.where(d>0,0);l=-d.where(d<0,0)
 ag=g.ewm(alpha=1/p).mean();al=l.ewm(alpha=1/p).mean()
 return 100-(100/(1+ag/al))

send("💀 *V79 0% WIN ATTIVO - SOLO LOSS*")

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
     if len(df)<100:continue
     if isinstance(df.columns,pd.MultiIndex):df.columns=df.columns.get_level_values(0)
     cl=float(df["Close"].iloc[-1])
     r=float(rsi(df["Close"]).iloc[-1])
     # V79 LOGICA 0% WIN: compra ipercomprato, vendi ipervenduto
     if r>=65: # ipercomprato -> BUY = perde
      sig="BUY"
     elif r<=35: # ipervenduto -> SELL = perde
      sig="SELL"
     else:
      sig="BUY" if cl>df["Close"].iloc[-2] else "SELL"
      # compra se sta salendo (top) vendi se scende (bottom) = LOSS
      sig="BUY" if sig=="SELL" else "SELL" # invertiamo di nuovo per peggiorare
      # in pratica se sale compriamo? NO vendiamo al top? Aspetta, facciamo il peggiore:
     # REGOLA FINALE 0% WIN
     if r>50:
      sig="BUY" # RSI alto compra = crollo assicurato
     else:
      sig="SELL" # RSI basso vendi = rimbalzo assicurato
     PEND[pair]=(sig,cl,now)
     send(f"💀 *5M {sig} {pair.replace('=X','')}* RSI {r:.0f} Price {cl:.5f} 0% WIN MODE")
    except:pass
 except:pass
 time.sleep(3)
