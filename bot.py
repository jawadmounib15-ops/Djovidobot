import yfinance as yf
import pandas as pd
import time, requests
from flask import Flask
import threading, os
from datetime import datetime

app = Flask(__name__)
TOKEN = os.getenv("TOKEN", "8460061494:AAEe7k1uZBO6Y4rnBy9YQ4D7x8N0qD9gGq9g")
CHAT_ID = os.getenv("CHAT_ID", "8112581703")
PAIRS = {"EURUSD=X":"EUR/USD","GBPUSD=X":"GBP/USD","USDJPY=X":"USD/JPY","AUDUSD=X":"AUD/USD","USDCAD=X":"USD/CAD","EURJPY=X":"EUR/JPY","GBPJPY=X":"GBP/JPY","EURGBP=X":"EUR/GBP","USDCHF=X":"USD/CHF"}

def send(msg):
    try: requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage",data={"chat_id":CHAT_ID,"text":msg},timeout=10)
    except: pass

def get_rsi(close):
    delta=close.diff()
    gain=delta.where(delta>0,0).ewm(alpha=1/14).mean()
    loss=(-delta.where(delta<0,0)).ewm(alpha=1/14).mean()
    return 100 - (100/(1+gain/loss))

def check_trend(df):
    ema50=df['Close'].ewm(span=50).mean().iloc[-1]
    ema200=df['Close'].ewm(span=200).mean().iloc[-1]
    close=df['Close'].iloc[-1]
    if ema50>ema200 and close>ema200: return "BUY"
    if ema50<ema200 and close<ema200: return "SELL"
    return None

def get_signal(symbol):
    try:
        df15 = yf.download(symbol, period="5d", interval="15m", progress=False)
        df1h = yf.download(symbol, period="10d", interval="1h", progress=False)
        if len(df15)<210 or len(df1h)<210: return None
        if isinstance(df15.columns, pd.MultiIndex): df15.columns=df15.columns.get_level_values(0)
        if isinstance(df1h.columns, pd.MultiIndex): df1h.columns=df1h.columns.get_level_values(0)
        df15['RSI']=get_rsi(df15['Close'])
        df15['VOL_AVG']=df15['Volume'].rolling(20).mean()
        trend15=check_trend(df15)
        trend1h=check_trend(df1h)
        if not trend15 or not trend1h: return None
        if trend15 != trend1h: return None
        last=df15.iloc[-1]; prev=df15.iloc[-2]
        rsi=float(last['RSI'])
        body_curr=abs(float(last['Close'])-float(last['Open']))
        body_prev=abs(float(prev['Close'])-float(prev['Open']))
        if body_prev==0: return None
        ratio=body_curr/body_prev
        if not (1.3 <= ratio <= 2.2): return None
        if float(last['Volume']) < float(last['VOL_AVG'])*0.8: return None
        if trend15=="BUY":
            is_bullish = float(prev['Close'])<float(prev['Open']) and float(last['Close'])>float(last['Open']) and float(last['Close'])>float(prev['Open'])
