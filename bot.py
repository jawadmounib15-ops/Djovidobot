import os,time,requests,yfinance as yf,threading,pandas as pd
from datetime import datetime,timedelta
from flask import Flask
app=Flask(__name__)
@app.route('/')
def home():return "V82 DIAG"
def rf():app.run(host="0.0.0.0",port=int(os.environ.get("PORT",10000)))
threading.Thread(target=rf,daemon=True).start()

TOKEN=os.environ.get("TELEGRAM_TOKEN")
CHAT=os.environ.get("TELEGRAM_CHAT_ID")
PAIRS=["EURUSD=X","GBPUSD=X","USDJPY=X"]
WIN=0;LOSS=0;PEND={};CHECK=0

def send(m):
 try:requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage",json={"chat_id":CHAT,"text":m,"parse_mode":"Markdown"},timeout=10)
 except:pass
def rsi(s,p=14):
 d=s.diff();g=d.where(d>0,0);l=-d.where(d<0,0)
 ag=g.ewm(alpha=1/p).mean();al=l.ewm(alpha=1/p).mean()
 return 100-(100/(1+ag/al))

send("🔍 *DIAGNOSTICO ON - ti mando RSI ogni 1 min*")

while True:
 try:
  now=datetime.now()
  if time.time()-CHECK>=60:
   CHECK=time.time()
   for pair in PAIRS:
    try:
     df=yf.download(pair,period="10d",interval="5m",progress=False)
     if len(df)<100:send(f"⚠️ {pair} poche candele {len(df)}");continue
     if isinstance(df.columns,pd.MultiIndex):df.columns=df.columns.get_level_values(0)
     df["EMA50"]=df["Close"].ewm(span=50).mean();df["EMA200"]=df["Close"].ewm(span=200).mean();df["RSI"]=rsi(df["Close"])
     df["BB_MA"]=df["Close"].rolling(20).mean();df["BB_STD"]=df["Close"].rolling(20).std()
     df["BB_UP"]=df["BB_MA"]+2*df["BB_STD"];df["BB_DOWN"]=df["BB_MA"]-2*df["BB_STD"]
     c=float(df["Close"].iloc[-1]);ema50=float(df["EMA50"].iloc[-1]);r=float(df["RSI"].iloc[-1])
     bb_up=float(df["BB_UP"].iloc[-1]);bb_down=float(df["BB_DOWN"].iloc[-1])
     df1h=yf.download(pair,period="20d",interval="1h",progress=False)
     if isinstance(df1h.columns,pd.MultiIndex):df1h.columns=df1h.columns.get_level_values(0)
     df1h["EMA50"]=df1h["Close"].ewm(span=50).mean();df1h["EMA200"]=df1h["Close"].ewm(span=200).mean()
     h1_down=float(df1h["EMA50"].iloc[-1])<float(df1h["EMA200"].iloc[-1])
     
     # Manda diagnosi
     send(f"📈 *{pair.replace('=X','')}* RSI:{r:.0f} | Price:{c:.5f} EMA50:{ema50:.5f} | BB:{bb_up:.5f}/{bb_down:.5f} | 1H:{'DOWN' if h1_down else 'UP'}")
     
     sig=None
     if r>=68 and c>bb_up*0.99 and c>ema50 and h1_down:sig="BUY"
     elif r<=32 and c<bb_down*1.01 and c<ema50 and not h1_down:sig="SELL"
     if sig:
      send(f"💀 *SIGNAL {sig} {pair.replace('=X','')}* RSI:{r:.0f}")
    except Exception as e:
     send(f"❌ Err {pair}: {e}")
 except:pass
 time.slee p(3)
