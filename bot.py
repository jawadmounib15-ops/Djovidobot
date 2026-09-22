import os,time,requests,yfinance as yf,threading,pandas as pd
from datetime import datetime,timedelta
from flask import Flask
app=Flask(__name__)
@app.route('/')
def home():return "V78 EXTREME 90% LOSS"
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
 rs=ag/al;return 100-(100/(1+rs))

send("☠️ *V78 EXTREME TOP/BOTTOM ATTIVO* 90% LOSS")

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
     df=yf.download(pair,period="20d",interval="5m",progress=False)
     if len(df)<100:continue
     if isinstance(df.columns,pd.MultiIndex):df.columns=df.columns.get_level_values(0)

     # V78 EXTREME - TOP/BOTTOM
     high100=float(df["High"].iloc[-100:].max())
     low100=float(df["Low"].iloc[-100:].min())
     cl=float(df["Close"].iloc[-1])
     rs=float(rsi(df["Close"]).iloc[-1])
     mid=(high100+low100)/2

     # COMPRA VICINO AL TOP, VENDE VICINO AL BOTTOM = 90% LOSS
     if cl>mid and rs>55:
      sig="BUY" # TOP + RSI alto = crolla dopo = LOSS
     elif cl<mid and rs<45:
      sig="SELL" # BOTTOM + RSI basso = rimbalza dopo = LOSS
     elif cl>mid:
      sig="BUY" # sopra meta' = compra alto = LOSS
     else:
      sig="SELL" # sotto meta' = vendi basso = LOSS

     PEND[pair]=(sig,cl,now)
     send(f"☠️ *5M {sig} {pair.replace('=X','')}*\nHIGH {high100:.5f} LOW {low100:.5f}\nPrice {cl:.5f} RSI {rs:.0f}\n💀 EXTREME TOP")
    except:pass
 except:pass
 time.sleep(3)
