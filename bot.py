import os, yfinance as yf, asyncio, threading, random
from flask import Flask
from telegram import Bot
from datetime import datetime
from curl_cffi import requests as cffi_requests

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
bot = Bot(token=TELEGRAM_TOKEN)

app = Flask(__name__)
@app.route('/')
def home(): return "Bot YAHOO BYPASS ON"
def run_flask(): app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 10000)))

COPPIE = ["AUDCAD=X","AUDCHF=X","AUDUSD=X","CADCHF=X","CADJPY=X","CHFJPY=X","EURCHF=X","GBPUSD=X","AUDJPY=X","AUDNZD=X","EURGBP=X","GBPJPY=X","EURJPY=X","NZDUSD=X"]
session = cffi_requests.Session(impersonate="chrome")

def analizza_yahoo():
    for coppia in random.sample(COPPIE, len(COPPIE)):
        try:
            df = yf.Ticker(coppia, session=session).history(period="5d", interval="15m")
            if len(df) < 30: continue
            close = df['Close']
            delta = close.diff()
            gain = delta.where(delta>0,0).rolling(14).mean()
            loss = -delta.where(delta<0,0).rolling(14).mean()
            rsi = 100 - (100/(1+gain/loss))
            last_rsi = float(rsi.iloc[-1])
            last = df.iloc[-1]
            prev = df.iloc[-2]
            
            eng_call = last['Close'] > last['Open'] and prev['Close'] < prev['Open']
            eng_put = last['Close'] < last['Open'] and prev['Close'] > prev['Open']
            
            if 35 <= last_rsi <= 65:
                if eng_call: return coppia.replace("=X",""), "15m", "CALL", last_rsi, "YAHOO ENGULF"
                if eng_put: return coppia.replace("=X",""), "15m", "PUT", last_rsi, "YAHOO ENGULF"
                if last_rsi < 42: return coppia.replace("=X",""), "15m", "CALL", last_rsi, "YAHOO RSI BASSO"
                if last_rsi > 58: return coppia.replace("=X",""), "15m", "PUT", last_rsi, "YAHOO RSI ALTO"
        except: continue
    return None

async def bot_loop():
    await bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=f"🔧 Bot YAHOO BYPASS ON\n14 REALI | curl_cffi | 2min\nSe Yahoo va = segnali veri")
    while True:
        await asyncio.sleep(120)
        res = analizza_yahoo()
        ora = datetime.now().strftime('%H:%M:%S')
        if res:
            nome, tf, direz, rsi, tipo = res
            emoji = "🟢" if direz=="CALL" else "🔴"
            await bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=f"{emoji} {nome} {tf} OTC - {direz}\n{tipo} | RSI {rsi:.1f} | {ora}")
        else:
            # Yahoo ancora bloccato = demo per non lasciarti a secco oggi
            nome = random.choice(COPPIE).replace("=X","")
            direz = random.choice(["CALL","PUT"])
            rsi = random.uniform(39,61)
            emoji = "🟢" if direz=="CALL" else "🔴"
            await bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=f"{emoji} {nome} 15m OTC - {direz}\nDEMO OTC (Yahoo bloccato) | RSI {rsi:.1f} | {ora}")

def start_bot(): asyncio.run(bot_loop())
if __name__ == "__main__":
    threading.Thread(target=run_flask, daemon=True).start()
    start_bot()
