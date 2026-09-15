import yfinance as yf, requests, time, os
from datetime import datetime
from flask import Flask
import threading

# Prende token da Render - accetta sia TOKEN che BOT_TOKEN
TOKEN = os.environ.get("BOT_TOKEN") or os.environ.get("TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")

# Finto sito web per tenere acceso Render FREE
app = Flask(__name__)
@app.route('/')
def home():
    return "Bot attivo!"

def run_web():
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 10000)))

threading.Thread(target=run_web, daemon=True).start()

COPPIE = [("EURUSD=X","EUR/USD"),("GBPUSD=X","GBP/USD"),("USDJPY=X","USD/JPY")]

def send(m):
    try:
        requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage?chat_id={CHAT_ID}&text={m}")
    except:
        pass

send("✅ BOT PRE-AVVISO ATTIVO! Ti avviso 60sec prima!")

while True:
    for ticker, nome in COPPIE:
        try:
            df = yf.download(ticker, period="1d", interval="1m")
            if len(df) < 10:
                continue
            u5 = df.tail(5)
            o = float(u5.iloc[0]['Open'])
            c = float(u5.iloc[-1]['Close'])
            h = float(u5['High'].max())
            l = float(u5['Low'].min())
            corpo = abs(c-o)
            if corpo == 0:
                corpo = 0.00001
            sotto = min(o,c) - l
            sopra = h - max(o,c)
            pin = sotto > corpo*2.0 and sopra < corpo*0.8
            minuto = datetime.now().minute % 5
            sec = datetime.now().second
            if pin and minuto == 4 and sec >= 10:
                send(f"⚠️ PRE-AVVISO {nome} - Pin bar!")
        except:
            pass
    time.sleep(10)
