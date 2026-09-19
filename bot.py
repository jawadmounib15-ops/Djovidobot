# BOT V22 FIX - PARTE SICURO SU RENDER - NO PANDAS_TA
import yfinance as yf, pandas as pd, requests, time, os
from flask import Flask
from threading import Thread
app = Flask(__name__)

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
PAIRS = {"EURUSD=X":"EUR/USD","GBPUSD=X":"GBP/USD","USDJPY=X":"USD/JPY","EURJPY=X":"EUR/JPY"}

def send(msg):
    try:
        requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage", data={"chat_id":CHAT_ID,"text":msg}, timeout=10)
    except: pass

def get_data(s,i,p):
    try:
        df=yf.download(s,period=p,interval=i,progress=False,auto_adjust=False)
        if df.empty: return pd.DataFrame()
        if isinstance(df.columns,pd.MultiIndex): df.columns=df.columns.get_level_values(0)
        return df
    except: return pd.DataFrame()

def sma(series, n): return series.rolling(n).mean()
def ema(series, n): return series.ewm(span=n, adjust=False).mean()
def rsi(series, n=14):
    delta=series.diff(); gain=delta.where(delta>0,0).rolling(n).mean(); loss=-delta.where(delta<0,0).rolling(n).mean()
    rs=gain/loss; return 100-(100/(1+rs))

def pinbar(df):
    if len(df)<5: return None
    c=df.iloc[-1]; pr=df.iloc[-2]
    body=abs(float(c['Close'])-float(c['Open'])); rng=float(c['High'])-float(c['Low'])
    if rng==0: return None
    up=float(c['High'])-max(float(c['Open']),float(c['Close'])); lo=min(float(c['Open']),float(c['Close']))-float(c['Low'])
    if lo>body*2 and up<body*0.6: return "PINBAR_BUY"
    if up>body*2 and lo<body*0.6: return "PINBAR_SELL"
    if float(c['Close'])>float(c['Open']) and float(pr['Close'])<float(pr['Open']): return "ENGULFING_BUY"
    if float(c['Close'])<float(pr['Open']) and float(pr['Close'])>float(pr['Open']): return "ENGULFING_SELL"
    return None

def check(s,name):
    df_h1=get_data(s,"60m","10d"); df_m5=get_data(s,"5m","5d"); df_m1=get_data(s,"1m","2d")
    if len(df_h1)<60 or len(df_m5)<60 or len(df_m1)<30: return None
    sma50_h1=float(sma(df_h1['Close'],50).iloc[-1]); close_h1=float(df_h1['Close'].iloc[-1])
    ema20_m5=float(ema(df_m5['Close'],20).iloc[-1]); ema50_m5=float(ema(df_m5['Close'],50).iloc[-1])
    rsi_m1=float(rsi(df_m1['Close'],14).iloc[-1])
    ultime=df_h1['Close'].iloc[-8:].tolist()
    down_count=sum(1 for i in range(1,8) if ultime[i]<ultime[i-1])
    sta_scendendo=down_count>=6; sta_salendo=down_count<=2
    trend_h1_up=close_h1>sma50_h1; trend_m5_up=ema20_m5>ema50_m5
    if trend_h1_up!=trend_m5_up: return None
    pattern=pinbar(df_m1)
    if pattern is None: return None
    if sta_scendendo and "BUY" in pattern: return None
    if sta_salendo and "SELL" in pattern: return None
    scadenza="5 MINUTI"
    if trend_h1_up and "BUY" in pattern:
        return f"BUY {name} - H1 sopra SMA50 | Trend 1h UP | M1 {pattern} RSI {rsi_m1:.0f} | PO: 1 MIN | {scadenza}"
    if not trend_h1_up and "SELL" in pattern:
        return f"SELL {name} - H1 sotto SMA50 | Trend 1h DOWN da 1h+ ({down_count}/7) | M1 {pattern} RSI {rsi_m1:.0f} | PO: 1 MIN | {scadenza}"
    return None

def loop():
    send("V22 FIX PARTITO - H1+M5+M1 - Legge trend 1h come tua foto - 5MIN sicuro")
    while True:
        try:
            for c,n in PAIRS.items():
                s=check(c,n)
                if s: send(s); time.sleep(20)
            time.sleep(90)
        except: time.sleep(60)

@app.route('/')
def home(): return "V22 FIX attivo"
Thread(target=loop,daemon=True).start()
if __name__=="__main__": app.run(host="0.0.0.0",port=int(os.environ.get("PORT",10000)))
