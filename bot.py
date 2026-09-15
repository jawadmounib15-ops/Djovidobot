from flask import Flask
import threading
import yfinance as yf
import requests
import time
import os
from datetime import datetime

# --- SITO WEB PER TENERLO SVEGLIO 24/7 ---
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is running! LIVE 24/7 - DjovidoBot"

def run_web():
    app.run(host='0.0.0.0', port=10000)

threading.Thread(target=run_web, daemon=True).start()
# --- FINE SITO WEB ---

TOKEN = os.environ.get("BOT_TOKEN") or os.environ.get("TELEGRAM_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")

PAIRS = ["EURUSD=X", "GBPUSD=X", "USDJPY=X", "AUDUSD=X", "USDCAD=X", "EURJPY=X", "GBPJPY=X", "EURGBP=X"]
NAMES = ["EUR/USD", "GBP/USD", "USD/JPY", "AUD/USD", "USD/CAD", "EUR/JPY", "GBP/JPY", "EUR/GBP"]

def send_signal(pair_name, direction):
    text = f"🔥 SEGNALE {pair_name}\n📈 {direction}\n⏰ {datetime.now().strftime('%H:%M:%S')}\n📊 Pin Bar Strategy"
    try:
        requests.get(f"https://api.telegram.org/bot{TOKEN}/sendMessage?chat_id={CHAT_ID}&text={text}")
    except:
        pass

def check_pair(pair_yf, pair_name):
    try:
        data = yf.download(pair_yf, period="1d", interval="1m", progress=False)
        if len(data) < 5:
            return
        last = data.iloc[-1]
        open_p = last['Open']
        close_p = last['Close']
        high_p = last['High']
        low_p = last['Low']
        body = abs(close_p - open_p)
        upper_wick = high_p - max(open_p, close_p)
        lower_wick = min(open_p, close_p) - low_p

        if lower_wick > body * 2 and close_p > open_p:
            send_signal(pair_name, "BUY ⬆️ CALL")
        elif upper_wick > body * 2 and close_p < open_p:
            send_signal(pair_name, "SELL ⬇️ PUT")
    except Exception as e:
        print(e)

print("Bot started! 24/7 LIVE")
while True:
    for i in range(len(PAIRS)):
        check_pair(PAIRS[i], NAMES[i])
    time.sleep(60)
