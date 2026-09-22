import os,time,requests,yfinance as yf,threading,pandas as pd
from datetime import datetime,timedelta
from flask import Flask
app=Flask(__name__)
@app.route('/')
def home():return "V74 EMA200 LOSS 5MIN"
def rf():
 app.run(host="0.0.0.0",port=int(os.environ.get("PORT",10000)))
threading.Thread(target=rf,daemon=True).start()

TOKEN=os.environ.get("TELEGRAM_TOKEN")
CHAT=os.environ.get("TELEGRAM_CHAT_ID")
PAIRS=["EURUSD=X","GBPUSD=X","USDJPY=X","AUDUSD=X","USDCAD=X","EURJPY=X","GBPJPY=X","EURGBP=X"]

WIN=0;LOSS=0;PEND={};LAST={};CHECK=0

def send(m):
 try:
  requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage",json={"chat_id":CHAT,"text":m,"parse_mode":"Markdown"},timeout=10)
 except:pass

send("🤡 *V74 ATTIVO* EMA200 INVERTITO | 5M TF | Result 5M")

while True:
 try:
  now=datetime.now()
  # RISULTATO DOPO 5 MIN
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
     send(f"{R} *{k.replace('=X','')} {s}*\n{p:.5f}->{c:.5f}\n📊 WIN {WIN} LOSS {LOSS} WR {wr:.0f}%")
     del PEND[k]
    except:pass

  # SEGNALE OGNI 60 SEC CON COOLDOWN 5 MIN
  if time.time()-CHECK>60:
   CHECK=time.time()
   for pair in PAIRS:
    if pair in LAST and now-LAST[pair]<timedelta(minutes=5):continue
    try:
     df=yf.download(pair,period="5d",interval="5m",progress=False)
     if len(df)<200:continue
     if isinstance(df.columns,pd.MultiIndex):df.columns=df.columns.get_level_values(0)
     e200=df["Close"].ewm(span=200).mean().iloc[-1]
     cl=float(df["Close"].iloc[-1])
     # INVERTITO PER SBAGLIARE
     sig="SELL" if cl>e200 else "BUY"
     PEND[pair]=(sig,cl,now);LAST[pair]=now
     send(f"🔔 *5M {sig} {pair.replace('=X','')}*\nEMA200 {e200:.5f} Price {cl:.5f}\n⏳ Result in 5m (LOSS MODE)")
    except:pass
 except:pass
 time.sleep(3)
