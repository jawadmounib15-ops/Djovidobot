import os,time,requests,yfinance as yf,threading,pandas as pd
from datetime import datetime,timedelta
from flask import Flask
app=Flask(__name__)
@app.route('/')
def home():return "V102 LOSS 2 FILTRI"
TOKEN=os.environ.get("TELEGRAM_TOKEN")
CHAT=os.environ.get("TELEGRAM_CHAT_ID")
PAIRS=["EURUSD=X","GBPUSD=X","USDJPY=X","AUDUSD=X","USDCAD=X","EURJPY=X"]
WIN=0;LOSS=0;PEND={};CHECK=0;LAST_SIGNAL=0

def send(m):
 try:requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage",json={"chat_id":CHAT,"text":m,"parse_mode":"Markdown"},timeout=10)
 except:pass
def rsi(s,p=14):
 d=s.diff();g=d.where(d>0,0);l=-d.where(d<0,0)
 ag=g.ewm(alpha=1/p).mean();al=l.ewm(alpha=1/p).mean()
 return 100-(100/(1+ag/al))

def bot():
 global WIN,LOSS,CHECK,LAST_SIGNAL
 send("💀 *V102 LOSS 2 FILTRI ONLINE*\nBUY: RSI>65 + BB UP + Trend DOWN\nSELL: RSI<35 + BB DOWN + Trend UP\nSe 20min no signal -> tolgo BB auto")
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
      send(f"{R} *{k.replace('=X','')} {s}* {p:.5f}->{c:.5f} WR {wr:.0f}%\n👉 Pocket fai *{'SELL' if s=='BUY' else 'BUY'}*")
      del PEND[k]
     except:pass

   if time.time()-CHECK>=60:
    CHECK=time.time()
    # Se 20 min senza segnali, toglie BB
    no_bb = time.time() - LAST_SIGNAL > 1200

    for pair in PAIRS:
     try:
      df=yf.download(pair,period="10d",interval="5m",progress=False)
      if len(df)<200:continue
      if isinstance(df.columns,pd.MultiIndex):df.columns=df.columns.get_level_values(0)
      df["EMA50"]=df["Close"].ewm(span=50).mean();df["EMA200"]=df["Close"].ewm(span=200).mean();df["RSI"]=rsi(df["Close"])
      df["BB_MA"]=df["Close"].rolling(20).mean();df["BB_STD"]=df["Close"].rolling(20).std()
      df["BB_UP"]=df["BB_MA"]+2*df["BB_STD"];df["BB_DOWN"]=df["BB_MA"]-2*df["BB_STD"]
      c=float(df["Close"].iloc[-1]);ema50=float(df["EMA50"].iloc[-1]);ema200=float(df["EMA200"].iloc[-1]);r=float(df["RSI"].iloc[-1])
      bb_up=float(df["BB_UP"].iloc[-1]);bb_down=float(df["BB_DOWN"].iloc[-1])
      trend_down=ema50<ema200

      sig=None
      if no_bb:
       # SOLO 2 FILTRI - RSI + TREND CONTRARIO
       if r>=60 and trend_down:sig="BUY"
       elif r<=40 and not trend_down:sig="SELL"
      else:
       # 3 FILTRI - RSI + BB + TREND CONTRARIO
       if r>=65 and c>=bb_up*0.99 and trend_down:sig="BUY"
       elif r<=35 and c<=bb_down*1.01 and not trend_down:sig="SELL"

      if sig and pair not in PEND:
       PEND[pair]=(sig,c,now);LAST_SIGNAL=time.time()
       mode="2 FILTRI" if no_bb else "3 FILTRI"
       send(f"💀 *5M {sig} {pair.replace('=X','')}* {mode} RSI:{r:.0f}\n👉 *POCKET: {'SELL' if sig=='BUY' else 'BUY'}*")
     except:pass
  except:pass
  time.sleep(3)

threading.Thread(target=bot,daemon=True).start()
if __name__=="__main__":
 app.run(host="0.0.0.0",port=int(os.environ.get("PORT",10000)))
