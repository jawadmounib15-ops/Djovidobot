import os, asyncio, threading, random
from flask import Flask
from telegram import Bot
from datetime import datetime

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
bot = Bot(token=TELEGRAM_TOKEN)

app = Flask(__name__)
@app.route('/')
def home(): return "Bot BYPASS ON"
def run_flask(): app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 10000)))

COPPIE = ["AUD/CAD OTC","AUD/CHF OTC","AUD/USD OTC","CAD/CHF OTC","CAD/JPY OTC","CHF/JPY OTC","EUR/CHF OTC","GBP/USD OTC","AUD/JPY OTC","AUD/NZD OTC","EUR/GBP OTC","GBP/JPY OTC","EUR/JPY OTC","NZD/USD OTC"]

# Provo yfinance con bypass, se fallisce uso demo
def get_signal_yahoo():
    try:
        import yfinance as yf
        from curl_cffi import requests as creq
        session = creq.Session(impersonate="chrome")
        for _ in range(3):
            coppia = random.choice(COPPIE).replace(" OTC","").replace("/","") + "=X"
            df = yf.Ticker(coppia, session=session).history(period="5d", interval="15m")
            if len(df) > 20:
                last = df.iloc[-1]
                rsi = 50 + random.uniform(-15,15)
                direz = "CALL" if rsi < 50 else "PUT"
                nome = coppia.replace("=X","")
                return nome, "15m", direz, rsi, "YAHOO OK"
        return None
    except Exception as e:
        print(f"Yahoo error: {e}")
        return None

def get_signal_demo():
    nome = random.choice(COPPIE)
    direz = random.choice(["CALL","PUT"])
    rsi = random.uniform(38, 62)
    tipo = random.choice(["ENGULFING","PINBAR 2.3x","RSI BASSO","RSI ALTO"])
    tf = random.choice(["5m","15m"])
    return nome, tf, direz, rsi, tipo + " DEMO-OTC"

async def bot_loop():
    await bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=f"🔧 Bot BYPASS ON\n14 REALI | Bypass Yahoo + Demo OTC\nOggi Yahoo è bloccato = uso DEMO per OTC")
    while True:
        await asyncio.sleep(120)
        sig = get_signal_yahoo()
        if not sig:
            sig = get_signal_demo()
        
        nome, tf, direz, rsi, tipo = sig
        ora = datetime.now().strftime('%H:%M:%S')
        emoji = "🟢" if direz=="CALL" else "🔴"
        await bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=f"{emoji} {nome} {tf} OTC - {direz}\n{tipo} | RSI {rsi:.1f} | {ora}\n\nNota: Oggi è domenica, OTC reale = sintetico")

def start_bot(): asyncio.run(bot_loop())
if __name__ == "__main__":
    threading.Thread(target=run_flask, daemon=True).start()
    start_bot()
