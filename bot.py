import os, asyncio, threading, random
from flask import Flask
from telegram import Bot
from datetime import datetime
import pytz
import yfinance as yf
from curl_cffi import requests as cffi_requests

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
bot = Bot(token=TELEGRAM_TOKEN)

app = Flask(__name__)
@app.route('/')
def home(): return "Bot POCKET REAL+OTC ON"
def run_flask(): app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 10000)))

YAHOO_MAP = {
 "EURUSD=X":"EUR/USD",
 "GBPUSD=X":"GBP/USD",
 "AUDUSD=X":"AUD/USD",
 "USDJPY=X":"USD/JPY",
 "EURJPY=X":"EUR/JPY",
 "GBPJPY=X":"GBP/JPY",
 "AUDJPY=X":"AUD/JPY",
 "EURGBP=X":"EUR/GBP",
 "AUDCAD=X":"AUD/CAD",
 "AUDCHF=X":"AUD/CHF"
}
COPPIE = list(YAHOO_MAP.keys())
session = cffi_requests.Session(impersonate="chrome")
ROMA = pytz.timezone("Europe/Rome")

def is_pinbar_pro(o,h,l,c, ema9, ema21, rsi):
    body = abs(c - o)
    rng = h - l
    if rng==0: return None
    up = h - max(o,c)
    low = min(o,c) - l
    if body > rng*0.35: return None
    if max(up,low) < rng*0.55: return None
    if low >= body*2.2 and up <= rng*0.35:
        if not (ema9 > ema21): return None
        if not (35 <= rsi <= 68): return None
        return "CALL", round(low/body,1)
    if up >= body*2.2 and low <= rng*0.35:
        if not (ema9 < ema21): return None
        if not (32 <= rsi <= 70): return None
        return "PUT", round(up/body,1)
    return None

def analizza():
    for coppia in random.sample(COPPIE, len(COPPIE)):
        try:
            df = yf.Ticker(coppia, session=session).history(period="5d", interval="5m")
            if len(df) < 30: continue
            cl = df['Close']
            ema9 = cl.ewm(span=9).mean().iloc[-1]
            ema21 = cl.ewm(span=21).mean().iloc[-1]
            delta = cl.diff()
            gain = delta.where(delta>0,0).rolling(14).mean()
            loss = -delta.where(delta<0,0).rolling(14).mean()
            rsi = 100 - (100/(1+gain/loss))
            last_rsi = float(rsi.iloc[-1])
            row = df.iloc[-1]
            res = is_pinbar_pro(row['Open'],row['High'],row['Low'],row['Close'], ema9, ema21, last_rsi)
            if res:
                d, ratio = res
                return YAHOO_MAP[coppia], d, last_rsi, ratio
        except: continue
    return None

async def bot_loop():
    ora = datetime.now(ROMA).strftime('%H:%M:%S')
    await bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=f"🔥 POCKET REAL+OTC PRO ON\nPinbar 2.2x | EMA9/21 | RSI 32-70\n{ora} IT - Ogni 90 sec")
    while True:
        await asyncio.sleep(90)
        res = analizza()
        ora = datetime.now(ROMA).strftime('%H:%M:%S')
        if res:
            nome, direz, rsi, ratio = res
            emoji = "🟢" if direz=="CALL" else "🔴"
            # Manda sia REAL che OTC
            await bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=f"{emoji} {nome} 5m - {direz}\nREAL: {nome} | OTC: {nome} OTC\nPinbar {ratio}x | RSI {rsi:.0f} | {ora} IT\nPocket: cerca {nome} o {nome} OTC")
        else:
            # Se Yahoo non dà nulla, manda comunque OTC per opportunità
            nome = random.choice(list(YAHOO_MAP.values()))
            direz = random.choice(["CALL","PUT"])
            # Solo domenica: manda OTC
            if datetime.now(ROMA).weekday() >= 5:
                emoji = "🟢" if direz=="CALL" else "🔴"
                await bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=f"{emoji} {nome} OTC 5m - {direz}\nOTC DEMO (Yahoo chiuso) | {ora} IT")

def start_bot(): asyncio.run(bot_loop())
if __name__ == "__main__":
    threading.Thread(target=run_flask, daemon=True).start()
    start_bot()
