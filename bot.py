import os, asyncio, threading, random
from flask import Flask
from telegram import Bot
from datetime import datetime

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
bot = Bot(token=TELEGRAM_TOKEN)

app = Flask(__name__)
@app.route('/')
def home(): return "Bot DOMENICA DEMO ON"
def run_flask(): app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 10000)))

COPPIE = ["AUD/CAD OTC","AUD/CHF OTC","AUD/USD OTC","CAD/CHF OTC","CAD/JPY OTC","CHF/JPY OTC","EUR/CHF OTC","GBP/USD OTC","AUD/JPY OTC","AUD/NZD OTC","EUR/GBP","GBP/JPY","EUR/JPY","NZD/USD"]

async def bot_loop():
    await bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=f"🔧 Bot DOMENICA DEMO ON\n14 COPPIE | Segnali ogni 2min | Oggi DEMO perchè Yahoo chiuso")
    while True:
        await asyncio.sleep(120)
        nome = random.choice(COPPIE)
        direz = random.choice(["CALL","PUT"])
        rsi = random.uniform(40, 60)
        tipo = random.choice(["ENGULFING","PINBAR 2.5x"])
        tf = random.choice(["5m","15m"])
        ora = datetime.now().strftime('%H:%M:%S')
        emoji = "🟢" if direz=="CALL" else "🔴"
        await bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=f"{emoji} {nome} {tf} - {direz}\n{tipo} DEMO-OTC | RSI {rsi:.1f} | {ora}")

def start_bot(): asyncio.run(bot_loop())
if __name__ == "__main__":
    threading.Thread(target=run_flask, daemon=True).start()
    start_bot()
