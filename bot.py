import os,time,requests,yfinance as yf,threading,pandas as pd
from datetime import datetime,timedelta
from flask import Flask
app=Flask(__name__)
@app.route('/')
def home():return "V100 3+3 REGOLE"
def rf():app.run(host="0.0.0.0",port=int(os.environ.get("PORT",10000)))
threading.Thread(target=rf,daemon=True).start()
TOKEN=os.environ.get("TELEGRAM_TOKEN");CHAT=os.environ.get("TELEGRAM_CHAT_ID")
PAIRS=["EURUSD=X","GBPUSD=X","USDJPY=X","AUDUSD=X","USDCAD=X","EURJPY=X","GBPJPY=X","EURGBP=X"]
WIN=0;LOSS=0;PEND={};CHECK=0
def send(m):
 try:requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage",json={"chat_id":CHAT,"text":m,"parse_mode":"Markdown"},timeout=10)
 except:pass
def rsi(s,p=14):
 d=s.diff();g=d.where(d>0,0);l=-d.where(d<0,0)
 return 100-(100/(1+g.ewm(alpha=1/p).mean()/(-d.where(d<0,0)).ewm(alpha=1/p).mean()))

send("✅ *V100 3 REGOLE BUY + 3 REGOLE SELL ATTIVO*")

while True:
 try:
  now=datetime.now()
  for k in list(PEND.keys()):
   s,p,t=PEND[k]
   if now-t>=timedelta(minutes=5):
    try:
     df=yf.download(k,period="1d",interval="1m",progress=False)
     if isinstance(df.columns,pd.MultiIndex):df.columns=df.columns.get_level_values(0)
     c=float(df["Close"].iloc[-1]);w=(s=="BUY" and c>p) or (s=="SELL" and c<p)
     if w:WIN+=1;R="✅ WIN"
     else:LOSS+=1;R="❌ LOSS"
     tot=WIN+LOSS;wr=WIN/tot*100 if tot>0 else 0
     send(f"{R} *{k.replace('=X','')} {s}* WR {wr:.0f}%")
     del PEND[k]
    except:pass
  if time.time()-CHECK>=300:
   CHECK=time.time()
   for pair in PAIRS:
    try:
     df=yf.download(pair,period="10d",interval="5m",progress=False)
     if len(df)<250:continue
     if isinstance(df.columns,pd.MultiIndex):df.columns=df.columns.get_level_values(0)
     df["EMA50"]=df["Close"].ewm(span=50).mean();df["EMA200"]=df["Close"].ewm(span=200).mean()
     df["RSI"]=rsi(df["Close"]);df["RES"]=df["High"].rolling(20).max();df["SUP"]=df["Low"].rolling(20).min()
     df["VAVG"]=df["Volume"].rolling(20).mean()

     c=float(df["Close"].iloc[-1]);ema50=float(df["EMA50"].iloc[-1]);ema200=float(df["EMA200"].iloc[-1])
     e50p=float(df["EMA50"].iloc[-2]);e200p=float(df["EMA200"].iloc[-2])
     r=float(df["RSI"].iloc[-1]);rp=float(df["RSI"].iloc[-2])
     res=float(df["RES"].iloc[-2]);sup=float(df["SUP"].iloc[-2])
     vol=float(df["Volume"].iloc[-1]);vavg=float(df["VAVG"].iloc[-1])

     sig=None
     # ================= BUY 3 REGOLE =================
     # 1. EMA50 incrocia sopra EMA200
     cond1_buy = e50p<=e200p and ema50>ema200
     # 2. RSI >50 che viene da >30 (uscito da ipervenduto)
     cond2_buy = r>50 and rp>30 and rp<60
     # 3. Breakout resistenza con volumi
     cond3_buy = c>res and vol>vavg

     if cond1_buy and cond2_buy and cond3_buy:
      sig="BUY"

     # ================= SELL 3 REGOLE =================
     # 1. EMA50 incrocia sotto EMA200
     cond1_sell = e50p>=e200p and ema50<ema200
     # 2. RSI scende sotto 70 o rompe sotto 50
     cond2_sell = r<70 or r<50
     # 3. Breakdown supporto con volumi
     cond3_sell = c<sup and vol>vavg

     if cond1_sell and cond2_sell and cond3_sell:
      sig="SELL"

     if sig and pair not in PEND:
      PEND[pair]=(sig,c,now)
      send(f"✅ *5M {sig} {pair.replace('=X','')}*\n1) EMA50 {'↗️ sopra' if ema50>ema200 else '↘️ sotto'} EMA200\n2) RSI {r:.0f}\n3) {'Rottura RES' if sig=='BUY' else 'Rottura SUP'} {res if sig=='BUY' else sup:.5f}\nPrice {c:.5f}")
    except:pass
 except:pass
 time.sleep(3)
