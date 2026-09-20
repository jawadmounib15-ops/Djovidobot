import os, requests, time, yfinance as yf, pandas as pd
from flask import Flask
from threading import Thread
from datetime import datetime, timedelta

app = Flask(__name__)
TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT = os.getenv("TELEGRAM_CHAT_ID")

PAIRS_REAL = {
    "EURUSD=X": "EUR/USD",
    "GBPUSD=X": "GBP/USD",
    "USDJPY=X": "USD/JPY",
    "EURJPY=X": "EUR/JPY",
    "GBPJPY=X": "GBP/JPY"
}

PAIRS_OTC = {
    "BTC-USD": ("EUR/USD OTC", 1.0850),
    "ETH-USD": ("GBP/USD OTC", 1.2700),
    "SOL-USD": ("USD/JPY OTC", 155.50),
    "BNB-USD": ("EUR/JPY OTC", 168.80),
    "XRP-USD": ("GBP/JPY OTC", 197.20)
}

LAST = {}

def send(m):
    try:
        if TOKEN and CHAT:
            requests.post("https://api.telegram.org/bot"+TOKEN+"/sendMessage", data={"chat_id": CHAT, "text": m}, timeout=10)
    except: pass

def get_data(sym, interval, period):
    try:
        df = yf.download(sym, interval=interval, period=period, progress=False, auto_adjust=False)
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
        return df
    except: return pd.DataFrame()

def ema(s,n): return s.ewm(span=n, adjust=False).mean()
def sma(s,n): return s.rolling(n).mean()
def rsi_calc(s,n=14):
    d=s.diff(); g=d.where(d>0,0).rolling(n).mean(); l=-d.where(d<0,0).rolling(n).mean()
    return 100-(100/(1+g/l))

def make_msg(tipo,coppia,lavoro,motivo,prezzo):
    now=datetime.now(); exp=now+timedelta(minutes=5)
    return f"{tipo} - {coppia}\nPrezzo: {round(prezzo,5)}\nScadenza: 5 MINUTI\nEntrata: {now.strftime('%H:%M:%S')}\nScade alle: {exp.strftime('%H:%M:%S')}\nLavoro: {lavoro}\nMotivo: {motivo}\nAzione: Entra subito {tipo}"

def can_send(coppia,lavoro,is_otc=False):
    key=coppia+"_"+lavoro; now=time.time()
    cooldown = 3600 if is_otc else 1800 # OTC 1 ora di pausa, reali 30 min
    if key in LAST and now-LAST[key]<cooldown: return False
    LAST[key]=now; return True

def check(sym,name,base_price=None,is_otc=False):
    df_h1=get_data(sym,"60m","10d"); df_m15=get_data(sym,"15m","5d"); df_m5=get_data(sym,"5m","3d"); df_m1=get_data(sym,"1m","2d")
    if len(df_m15)<50 or len(df_m1)<30: return []

    c1_raw=float(df_m1["Close"].iloc[-1])
    if is_otc and base_price:
        try:
            c1_60_ago = float(df_m1["Close"].iloc[-60])
            var_pct = (c1_raw - c1_60_ago) / c1_60_ago
            c1 = base_price * (1 + var_pct * 0.1)
        except: c1 = base_price
    else: c1 = c1_raw

    res=[]; o1=float(df_m1["Open"].iloc[-1]); l1=float(df_m1["Low"].iloc[-1]); h1=float(df_m1["High"].iloc[-1]); c_prev=float(df_m1["Close"].iloc[-2]); o_prev=float(df_m1["Open"].iloc[-2]); r1=float(rsi_calc(df_m1["Close"]).iloc[-1]); r_prev=float(rsi_calc(df_m1["Close"]).iloc[-2]); e5_15=float(ema(df_m15["Close"],5).iloc[-1]); e20_15=float(ema(df_m15["Close"],20).iloc[-1]); e50_15=float(ema(df_m15["Close"],50).iloc[-1]); s50_15=float(sma(df_m15["Close"],50).iloc[-1]); e5_1=float(ema(df_m1["Close"],5).iloc[-1]); e20_1=float(ema(df_m1["Close"],20).iloc[-1]); e5_1_prev=float(ema(df_m1["Close"],5).iloc[-2]); e20_1_prev=float(ema(df_m1["Close"],20).iloc[-2]); body=abs(c1_raw-o1); lo=min(o1,c1_raw)-l1; up=h1-max(o1,c1_raw); pin_buy=lo>body*2.0; pin_sell=up>body*2.0; eng_buy=c1_raw>o1 and c_prev<o_prev and abs(c1_raw-o1) > abs(c_prev-o_prev); eng_sell=c1_raw<o1 and c_prev>o_prev and abs(c1_raw-o1) > abs(c_prev-o_prev); ma20=sma(df_m1["Close"],20); std20=df_m1["Close"].rolling(20).std(); upper=float((ma20+2*std20).iloc[-1]); lower=float((ma20-2*std20).iloc[-1]); high20=float(df_m5["High"].rolling(20).max().iloc[-2]); low20=float(df_m5["Low"].rolling(20).min().iloc[-2]); daily_low=float(df_h1["Low"].rolling(24).min().iloc[-1]); daily_high=float(df_h1["High"].rolling(24).max().iloc[-1]); low_ago=float(df_m1["Low"].rolling(10).min().iloc[-11]); high_ago=float(df_m1["High"].rolling(10).max().iloc[-11])

    # --- LOGICA REALI: V34 ORIGINALE CON 7 LAVORI ---
    if not is_otc:
        if e5_15>e20_15 and e20_15>e50_15 and pin_buy and can_send(name,"L1"): res.append(make_msg("BUY",name,"L1 TREND","3 EMA UP + Pinbar",c1))
        if e5_15<e20_15 and e20_15<e50_15 and pin_sell and can_send(name,"L1"): res.append(make_msg("SELL",name,"L1 TREND","3 EMA DOWN + Pinbar",c1))
        if r_prev<30 and r1>30 and l1<=lower*1.002 and can_send(name,"L2"): res.append(make_msg("BUY",name,"L2 RIMBALZO","RSI 30 + Bollinger basso",c1))
        if r_prev>70 and r1<70 and h1>=upper*0.998 and can_send(name,"L2"): res.append(make_msg("SELL",name,"L2 RIMBALZO","RSI 70 + Bollinger alto",c1))
        if c1_raw>high20 and can_send(name,"L3"): res.append(make_msg("BUY",name,"L3 BREAKOUT","Rottura MAX 20",c1))
        if c1_raw<low20 and can_send(name,"L3"): res.append(make_msg("SELL",name,"L3 BREAKOUT","Rottura MIN 20",c1))
        if abs(c1_raw-s50_15)/c1_raw<0.002 and eng_buy and e5_15>e20
