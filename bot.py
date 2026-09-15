import yfinance as yf
import requests
import time
import os

# Render leggerà questi dal pannello segreto
TOKEN = os.environ.get("TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")

COPPIE = [
    ("EURUSD=X", "EUR/USD"),
    ("GBPUSD=X", "GBP/USD"),
    ("AUDUSD=X", "AUD/USD"),
    ("USDJPY=X", "USD/JPY"),
    ("GBPJPY=X", "GBP/JPY"),
    ("EURJPY=X", "EUR/JPY"),
    ("USDCAD=X", "USD/CAD")
]

def send(msg):
    try:
        url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
        requests.post(url, data={"chat_id": CHAT_ID, "text": msg, "parse_mode": "Markdown"})
    except:
        pass

print("Djovidobot partito per coppie REALI...")

while True:
    for ticker, nome in COPPIE:
        try:
            df = yf.download(ticker, period="1d", interval="5m", progress=False)
            if len(df) < 50:
                continue
            
            last = df.iloc[-2]
            corpo = abs(float(last['Close'] - last['Open']))
            coda_sotto = float(min(last['Open'], last['Close']) - last['Low'])
            coda_sopra = float(last['High'] - max(last['Open'], last['Close']))
            
            # Pin bar rialzista = coda lunga sotto
            is_pin = coda_sotto > corpo * 2.5 and coda_sopra < corpo * 0.8 and float(last['Close']) > float(last['Open'])
            
            if is_pin and corpo > 0:
                send(f"🔥 *SEGNALE REALE {nome}*\nPin Bar Rialzista su 5m\nPrezzo: {float(last['Close']):.5f}\n👉 Apri Pocket Option -> {nome} REAL")
        except:
            pass
    time.sleep(300)
