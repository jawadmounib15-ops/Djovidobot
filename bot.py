# V29 FINAL FIX - TELEGRAM VARS FIX
import yfinance as yf, pandas as pd, requests, time, os
from flask import Flask
from threading import Thread
app = Flask(__name__)

# LEGGE ENTRAMBI I NOMI - COSI NON FALLISCE PIU
TOKEN=os.getenv("TELEGRAM_TOKEN") or os.getenv("TOKEN")
CHAT=os.getenv("TELEGRAM_CHAT_ID") or os.getenv("CHAT_ID")

PAIRS={"EURUSD=X":"EUR/USD","GBPUSD=X":"GBP/USD","USDJPY=X":"USD/JPY","EURJPY=X":"EUR/JPY","GBPJPY=X":"GBP/JPY"}

def send(m):
    if not TOKEN or not CHAT: return
    try: requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage",data={"chat_id":CHAT,"text":m},timeout=10)
    except: pass
def get(s,i,p):
    try:
        df=yf.download(s,period=p,interval=i,progress=False,auto_adjust=False)
        if isinstance(df.columns,pd.MultiIndex): df.columns=df.columns.get_level_values(0)
        return df
    except: return pd.DataFrame()
def ema(s,n): return s.ewm(span=n,adjust=False).mean()
def sma(s,n): return s.rolling(n).mean()
def rsi(s,n=14):
    d=s.diff(); g=d.where(d>0,0).rolling(n).mean(); l=-d.where(d<0,0).rolling(n).mean(); return 100-(100/(1+g/l))

def check(s,name):
    df_h1=get(s,"60m","10d"); df_m15=get(s,"15m","5d"); df_m5=get(s,"5m","3d"); df_m1=get(s,"1m","2d")
    if len(df_m15)<50 or len(df_m1)<30: return []
    res=[]; c1=float(df_m1['Close'].iloc[-1]); o1=float(df_m1['Open'].iloc[-1]); l1=float(df_m1['Low'].iloc[-1]); h1=float(df_m1['High'].iloc[-1])
    c_prev=float(df_m1['Close'].iloc[-2]); o_prev=float(df_m1['Open'].iloc[-2])
    r1=float(rsi(df_m1['Close']).iloc[-1]); r_prev=float(rsi(df_m1['Close']).iloc[-2])
    e5=float(ema(df_m15['Close'],5).iloc[-1]); e20=float(ema(df_m15['Close'],20).iloc[-1]); e50=float(ema(df_m15['Close'],50).iloc[-1])
    s50=float(sma(df_m15['Close'],50).iloc[-1])
    body=abs(c1-o1); lo=min(o1,c1)-l1; up=h1-max(o1,c1)
    pin_buy=lo>body*1.5; pin_sell=up>body*1.5; eng_buy=c1>o1 and c_prev<o_prev; eng_sell=c1<o1 and c_prev>o_prev
    ma=sma(df_m1['Close'],20); std=df_m1['Close'].rolling(20).std()
    upper=float((ma+2*std).iloc[-1]); lower=float((ma-2*std).iloc[-1])
    high20=float(df_m5['High'].rolling(20).max().iloc[-2]); low20=float(df_m5['Low'].rolling(20).min().iloc[-2])
    daily_low=float(df_h1['Low'].rolling(24).min().iloc[-1]); daily_high=float(df_h1['High'].rolling(24).max().iloc[-1])
    if e5>e20>e50 and pin_buy: res.append(f"🟢 L1 TREND {name} BUY 5M")
    if e5<e20<e50 and pin_sell: res.append(f"🔴 L1 TREND {name} SELL 5M")
    if r_prev<30 and r1>30 and l1<=lower*1.002: res.append(f"🟢 L2 RIMBALZO {name} BUY 5M")
    if r_prev>70 and r1<70 and h1>=upper*0.998: res.append(f"🔴 L2 RIMBALZO {name} SELL 5M")
    if c1>high20: res.append(f"🟢 L3 BREAK {name} BUY 5M")
    if c1<low20: res.append(f"🔴 L3 BREAK {name} SELL 5M")
    if abs(c1-s50)/c1<0.002 and eng_buy: res.append(f"🟢 L4 PULL {name} BUY 5M")
    if abs(c1-s50)/c1<0.002 and eng_sell: res.append(f"🔴 L4 PULL {name} SELL 5M")
    if abs(df_m1['Low'].rolling(10).min().iloc[-11]-l1)/l1<0.001 and c1>o1: res.append(f"🟢 L5 DOPPIO {name} BUY 5M")
    if abs(df_m1['High'].rolling(10).max().iloc[-11]-h1)/h1<0.001 and c1<o1: res.append(f"🔴 L5 DOPPIO {name} SELL 5M")
    if e5>e20 and float(ema(df_m1['Close'],5).iloc[-2])<float(ema(df_m1['Close'],20).iloc[-2]): res.append(f"🟢 L6 CROSS {name} BUY 5M")
    if e5<e20 and float(ema(df_m1['Close'],5).iloc[-2])>float(ema(df_m1['Close'],20).iloc[-2]): res.append(f"🔴 L6 CROSS {name} SELL 5M")
    if abs(c1-daily_low)/c1<0.001 and pin_buy: res.append(f"🟢 L7 SUP {name} BUY 5M")
    if abs(c1-daily_high)/c1<0.001 and pin_sell: res.append(f"🔴 L7 RES {name} SELL 5M")
    return res

def loop():
    send("✅ V29 ULTIMATE LIVE - 7 LAVORI - TELEGRAM OK")
    while True:
        try:
            for k,v in PAIRS.items():
                for s in check(k,v): send(s); time.sleep(15)
            time.sleep(80)
        except: time.sleep(60)

@app.route('/')
def home(): return "V29 LIVE 7 LAVORI"
Thread(target=loop,daemon=True).start()
if __name__=="__main__": app.run(host="0.0.0.0",port=int(os.environ.get("PORT",10 000)))
