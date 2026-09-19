# V29 ULTIMATE - 7 LAVORI - TUTTE LE REGOLE PRO
import yfinance as yf, pandas as pd, requests, time, os
from flask import Flask
from threading import Thread
app = Flask(__name__)
TOKEN=os.getenv("TELEGRAM_TOKEN"); CHAT=os.getenv("TELEGRAM_CHAT_ID")
PAIRS={"EURUSD=X":"EUR/USD","GBPUSD=X":"GBP/USD","USDJPY=X":"USD/JPY","EURJPY=X":"EUR/JPY","GBPJPY=X":"GBP/JPY","AUDUSD=X":"AUD/USD"}

def send(m):
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
    if len(df_m15)<60 or len(df_m1)<35: return []
    res=[]
    c1=float(df_m1['Close'].iloc[-1]); o1=float(df_m1['Open'].iloc[-1]); l1=float(df_m1['Low'].iloc[-1]); h1=float(df_m1['High'].iloc[-1])
    c_prev=float(df_m1['Close'].iloc[-2]); o_prev=float(df_m1['Open'].iloc[-2])
    rsi1=float(rsi(df_m1['Close']).iloc[-1]); rsi_prev=float(rsi(df_m1['Close']).iloc[-2])
    e5_15=float(ema(df_m15['Close'],5).iloc[-1]); e20_15=float(ema(df_m15['Close'],20).iloc[-1]); e50_15=float(ema(df_m15['Close'],50).iloc[-1])
    s50=float(sma(df_m15['Close'],50).iloc[-1])
    down_h1=sum(1 for i in range(1,8) if float(df_h1['Close'].iloc[-i])<float(df_h1['Close'].iloc[-i-1])) if len(df_h1)>10 else 0
    
    body=abs(c1-o1); lo=min(o1,c1)-l1; up=h1-max(o1,c1)
    pin_buy=lo>body*1.5 and c1>o1; pin_sell=up>body*1.5 and c1<o1
    eng_buy=c1>o1 and c_prev<o_prev and c1>o_prev; eng_sell=c1<o1 and c_prev>o_prev and c1<o_prev
    upper=float((sma(df_m1['Close'],20)+2*df_m1['Close'].rolling(20).std()).iloc[-1]); lower=float((sma(df_m1['Close'],20)-2*df_m1['Close'].rolling(20).std()).iloc[-1])
    vol_now=float(df_m1['Volume'].iloc[-1]) if 'Volume' in df_m1 and pd.notna(df_m1['Volume'].iloc[-1]) else 0
    vol_avg=float(df_m1['Volume'].rolling(20).mean().iloc[-1]) if 'Volume' in df_m1 else 1
    high20=float(df_m5['High'].rolling(20).max().iloc[-2]); low20=float(df_m5['Low'].rolling(20).min().iloc[-2])
    daily_high=float(df_h1['High'].rolling(24).max().iloc[-1]); daily_low=float(df_h1['Low'].rolling(24).min().iloc[-1])

    # L1 TREND
    if e5_15>e20_15>e50_15 and pin_buy and down_h1<6: res.append(f"🟢 L1 TREND {name} | 3EMA UP + PIN\n👉 BUY 5M")
    if e5_15<e20_15<e50_15 and pin_sell and down_h1>=4: res.append(f"🔴 L1 TREND {name} | 3EMA DOWN + PIN\n👉 SELL 5M")
    # L2 RIMBALZO
    if rsi_prev<30 and rsi1>30 and l1<=lower*1.002: res.append(f"🟢 L2 RIMBALZO {name} | RSI 30→ + BOLL\n👉 BUY 5M")
    if rsi_prev>70 and rsi1<70 and h1>=upper*0.998: res.append(f"🔴 L2 RIMBALZO {name} | RSI 70→ + BOLL\n👉 SELL 5M")
    # L3 BREAKOUT
    if c1>high20 and vol_now>vol_avg*1.2: res.append(f"🟢 L3 BREAKOUT {name} | Break MAX + Vol\n👉 BUY 5M")
    if c1<low20 and vol_now>vol_avg*1.2: res.append(f"🔴 L3 BREAKOUT {name} | Break MIN + Vol\n👉 SELL 5M")
    # L4 PULLBACK
    if abs(c1-s50)/c1<0.002 and eng_buy and e5_15>e20_15: res.append(f"🟢 L4 PULLBACK {name} | SMA50 + ENG\n👉 BUY 5M")
    if abs(c1-s50)/c1<0.002 and eng_sell and e5_15<e20_15: res.append(f"🔴 L4 PULLBACK {name} | SMA50 + ENG\n👉 SELL 5M")
    # L5 DOPPIO
    low_ago=float(df_m1['Low'].rolling(10).min().iloc[-11]); high_ago=float(df_m1['High'].rolling(10).max().iloc[-11])
    if abs(low_ago-l1)/l1<0.0008 and rsi1>rsi_prev and c1>o1: res.append(f"🟢 L5 DOPPIO MIN {name} | Doppio min + RSI div\n👉 BUY 5M")
    if abs(high_ago-h1)/h1<0.0008 and rsi1<rsi_prev and c1<o1: res.append(f"🔴 L5 DOPPIO MAX {name} | Doppio max + RSI div\n👉 SELL 5M")
    # L6 ADX FORTE + MA CROSS
    adx_strong = abs(e5_15-e50_15)/e50_15>0.0015
    cross_up = float(ema(df_m1['Close'],5).iloc[-1])>float(ema(df_m1['Close'],20).iloc[-1]) and float(ema(df_m1['Close'],5).iloc[-2])<float(ema(df_m1['Close'],20).iloc[-2])
    cross_down = float(ema(df_m1['Close'],5).iloc[-1])<float(ema(df_m1['Close'],20).iloc[-1]) and float(ema(df_m1['Close'],5).iloc[-2])>float(ema(df_m1['Close'],20).iloc[-2])
    if adx_strong and cross_up and rsi1>45: res.append(f"🟢 L6 ADX+Cross {name} | ADX forte + MA cross UP\n👉 BUY 5M")
    if adx_strong and cross_down and rsi1<55: res.append(f"🔴 L6 ADX+Cross {name} | ADX forte + MA cross DOWN\n👉 SELL 5M")
    # L7 SUPPORTO GIORNALIERO + MORNING STAR
    near_daily_low = abs(c1-daily_low)/c1<0.001; near_daily_high = abs(c1-daily_high)/c1<0.001
    if near_daily_low and (pin_buy or eng_buy): res.append(f"🟢 L7 SUPPORTO {name} | Supporto giornaliero {daily_low:.5f} + rifiuto\n👉 BUY 5M")
    if near_daily_high and (pin_sell or eng_sell): res.append(f"🔴 L7 RESISTENZA {name} | Resistenza giornaliera {daily_high:.5f} + rifiuto\n👉 SELL 5M")

    return res

def loop():
    send("✅ V29 ULTIMATE PARTITO - 7 LAVORI TUTTE LE REGOLE: 1-TREND 2-RIMBALZO 3-BREAKOUT 4-PULLBACK 5-DOPPIO 6-ADX+CROSS 7-SUPPORTO GIORN | 5MIN PRO FINALE")
    while True:
        try:
            for k,v in PAIRS.items():
                for s in check(k,v): send(s); time.sleep(20)
            time.sleep(75)
        except: time.sleep(60)

@app.route('/')
def home(): return "V29 7 LAVORI ULTIMATE"
Thread(target=loop,daemon=True).start()
if __name__=="__main__": app.run(host="0.0.0.0",port=int(os.environ.get("PORT",10000)))
