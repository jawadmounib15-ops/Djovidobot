import os,time,requests,yfinance as yf,threading,pandas as pd
from datetime import datetime,timedelta
from flask import Flask
app=Flask(__name__)
@app.route('/')
def home():return "V82 ULTRA 0% - 1MIN ANALISI 5M TF"
def rf():app.run(host="0.0.0.0",port=int(os.environ.get("PORT",10000)))
threading.Thread(target=rf,daemon=True).start()

TOKEN=os.environ.get("TELEGRAM_TOKEN")
CHAT=os.environ.get("TELEGRAM_CHAT_ID")
PAIRS=["EURUSD=X","GBPUSD=X","USDJPY=X","AUDUSD=X","USDCAD=X","EURJPY=X","GBPJPY=X","EURGBP=X"]

WIN=0;LOSS=0;PEND={};CHECK=0

def send(m):
 try:
  requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage",json={"chat_id":CHAT,"text":m,"parse_mode":"Markdown"},timeout=10)
 except:pass

def rsi(s,p=14):
 d=s.diff();g=d.where(d>0,0);l=-d.where(d<0,0)
 ag=g.ewm(alpha=1/p).mean();al=l.ewm(alpha=1/p).mean()
 return 100-(100/(1+ag/al))

send("💀 *V82 ULTRA 0% ATTIVO*\nAnalisi 1 MIN | TF 5M | RSI 80/20")

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
     send(f"{R} *{k.replace('=X','')} {s}*\n{p:.5f}->{c:.5f} WR {wr:.0f}% ({WIN}W/{LOSS}L)")
     del PEND[k]
    except:pass

  if time.time()-CHECK>=60:
   CHECK=time.time()
   for pair in PAIRS:
    try:
     df=yf.download(pair,period="10d",interval="5m",progress=False)
     if len(df)<250:continue
     if isinstance(df.columns,pd.MultiIndex):df.columns=df.columns.get_level_values(0)
     df["EMA50"]=df["Close"].ewm(span=50).mean()
     df["EMA200"]=df["Close"].ewm(span=200).mean()
     df["RSI"]=rsi(df["Close"])
     df["BB_MA"]=df["Close"].rolling(20).mean()
     df["BB_STD"]=df["Close"].rolling(20).std()
     df["BB_UP"]=df["BB_MA"]+2*df["BB_STD"]
     df["BB_DOWN"]=df["BB_MA"]-2*df["BB_STD"]
     df["VAVG"]=df["Volume"].rolling(20).mean()

     c=float(df["Close"].iloc[-1]);ema50=float(df["EMA50"].iloc[-1]);ema200=float(df["EMA200"].iloc[-1])
     r=float(df["RSI"].iloc[-1])
     bb_up=float(df["BB_UP"].iloc[-1]);bb_down=float(df["BB_DOWN"].iloc[-1])
     vol=float(df["Volume"].iloc[-1]);vavg=float(df["VAVG"].iloc[-1])
     high=float(df["High"].iloc[-1]);low=float(df["Low"].iloc[-1])
     body=abs(c-float(df["Open"].iloc[-1]));wick_up=high-max(c,float(df["Open"].iloc[-1]));wick_down=min(c,float(df["Open"].iloc[-1]))-low
     wick_no=wick_up<body*0.5 and wick_down<body*0.5
     bb_pos="UP" if c>bb_up*0.99 else "DOWN" if c<bb_down*1.01 else "MID"

     df1h=yf.download(pair,period="20d",interval="1h",progress=False)
     if isinstance(df1h.columns,pd.MultiIndex):df1h.columns=df1h.columns.get_level_values(0)
     df1h["EMA50"]=df1h["Close"].ewm(span=50).mean();df1h["EMA200"]=df1h["Close"].ewm(span=200).mean()
     h1_down=float(df1h["EMA50"].iloc[-1])<float(df1h["EMA200"].iloc[-1])

     df1d=yf.download(pair,period="200d",interval="1d",progress=False)
     if isinstance(df1d.columns,pd.MultiIndex):df1d.columns=df1d.columns.get_level_values(0)
     df1d["EMA50"]=df1d["Close"].ewm(span=50).mean();df1d["EMA200"]=df1d["Close"].ewm(span=200).mean()
     d1_down=float(df1d["EMA50"].iloc[-1])<float(df1d["EMA200"].iloc[-1])

     sig=None
     if r>=80 and bb_pos=="UP" and wick_no and vol<vavg and c>ema200 and h1_down and d1_down:
      if "JPY" in pair and c>ema50:continue
      sig="BUY"
     elif r<=20 and bb_pos=="DOWN" and wick_no and vol<vavg and c<ema200 and not h1_down and not d1_down:
      if "JPY" in pair and c<ema50:continue
      sig="SELL"

     if sig and pair not in PEND:
      PEND[pair]=(sig,c,now)
      send(f"💀 *5M {sig} {pair.replace('=X','')}* BB:{bb_pos} RSI:{r:.0f} Vol:LOW Price {c:.5f}")
    except:pass
 except:pass
 time.sleep(3)
