import yfinance as yf, requests, time, os
from datetime import datetime

TOKEN = os.environ.get("TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")

COPPIE = [("EURUSD=X","EUR/USD"),("GBPUSD=X","GBP/USD"),("USDJPY=X","USD/JPY"),("GBPJPY=X","GBP/JPY"),("EURJPY=X","EUR/JPY"),("AUDUSD=X","AUD/USD")]

def send(m):
    try:
        requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage", data={"chat_id":CHAT_ID,"text":m,"parse_mode":"Markdown"})
    except: pass

send("✅ BOT PRE-AVVISO ATTIVO! Ti avviso 60sec prima!")

while True:
    for ticker, nome in COPPIE:
        try:
            df = yf.download(ticker, period="1d", interval="1m", progress=False, auto_adjust=True)
            if len(df) < 10: continue
            u5 = df.tail(5)
            o = float(u5.iloc[0]['Open']); c = float(u5.iloc[-1]['Close']); h = float(u5['High'].max()); l = float(u5['Low'].min())
            corpo = abs(c-o)
            if corpo == 0: corpo = 0.00001
            sotto = min(o,c) - l
            sopra = h - max(o,c)
            pin = sotto > corpo*2.0 and sopra < corpo*0.8 and c > o
            minuto = datetime.now().minute % 5
            sec = datetime.now().second
            if pin and minuto == 4 and sec >= 10:
                send(f"⚠️ PRE-AV
