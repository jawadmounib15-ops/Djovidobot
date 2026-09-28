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
def home(): return "Bot POCKET 5m V2 ON"
def run_flask(): app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 10000)))

YAHOO_MAP = {
 "EURUSD=X":"EUR/USD","GBPUSD=X":"GBP/USD","AUDUSD=X":"AUD/USD",
 "USDJPY=X":"USD/JPY","EURJPY=X":"EUR/JPY","GBPJPY=X":"GBP/JPY",
 "AUDJPY=X":"AUD/JPY","EURGBP=X":"EUR/GBP","AUDCAD=X":"AUD/CAD","AUDCHF=X":"AUD/CHF"
}
COPPIE = list(YAHOO_MAP.keys())
session = cffi_requests.Session(impersonate="chrome")
ROMA = pytz.timezone("Europe/Rome")

# Anti spam: ricorda ultimo segnale per coppia
ultimo_segnali = {}

def is_pinbar_filtrata(o,h,l,c, ema9, ema21, ema50, rsi):
    body = abs(c - o)
    rng = h - l
    if rng==0: return None
    up = h - max(o,c)
    low = min(o,c) - l

    # FIX 1: corpo non troppo piccolo (evita 43.4x)
    if body < rng * 0.10: return None # min 10% - scarta doji
    if body > rng * 0.28: return None # max 28%

    # FIX 2: ratio massimo 8x (prima era infinito, per questo 43x)
    if low >= body*2.6:
        ratio = low/body
        if ratio > 8.0: return None # scarta 43.4x
        if up > rng*0.25: return None
        if not (ema9 > ema21 and c > ema50): return None
        if not (40 <= rsi <= 60): return None # più stretto da 38-62 a 40-60
        return "CALL", round(ratio,1)

    if up >= body*2.6:
        ratio = up/body
        if ratio > 8.0: return None
        if low > rng*0.25: return None
        if not (ema9 < ema21 and c < ema50): return None
        if not (40 <= rsi <= 60): return None
        return "PUT", round(ratio,1)
    return None

def analizza():
    now_ts = datetime.now().timestamp()
    for coppia in random.sample(COPPIE, len(COPPIE)):
        # FIX 3: cooldown 15 min per coppia
        if coppia in ultimo_segnali:
            if now_ts - ultimo_segnali[coppia] < 900: # 15 min
                continue

        try:
            df = yf.Ticker(coppia, session=session).history(period="5d", interval="5m")
            if len(df) < 60: continue
            cl = df['Close']
            ema9 = cl.ewm(span=9).mean().iloc[-1]
            ema21 = cl.ewm(span=21).mean().iloc[-1]
            ema50 = cl.ewm(span=50).mean().iloc[-1]
            delta = cl.diff()
            gain = delta.where(delta>0,0).rolling(14).mean()
            loss = -delta.where(delta<0,0).rolling(14).mean()
            rsi = 100 - (100/(1+gain/loss))
            last_rsi = float(rsi.iloc[-1])
            row = df.iloc[-1]

            # Filtro volatilità
            avg_rng = (df['High'] - df['Low']).rolling(20).mean().iloc[-1]
            if (row['High'] - row['Low']) < avg_rng * 0.75: continue

            res = is_pinbar_filtrata(row['Open'],row['High'],row['Low'],row['Close'], ema9, ema21, ema50, last_rsi)
            if res:
                d, ratio = res
                ultimo_segnali[coppia] = now_ts
                return YAHOO_MAP[coppia], d, last_rsi, ratio
        except: continue
    return None

async def bot_loop():
    ora = datetime.now(ROMA).strftime('%H:%M:%S')
    await bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=f"✅ POCKET 5m V2 FIXATO\nFix 43.4x | Body 10-28% | Ratio max 8x\nCooldown 15min | RSI 40-60 | {ora} IT")
    while True:
        await asyncio.sleep(90)
        res = analizza()
        ora = datetime.now(ROMA).strftime('%H:%M:%S')
        if res:
            nome, direz, rsi, ratio = res
            emoji = "🟢" if direz=="CALL" else "🔴"
            await bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=f"{emoji} {nome} 5m - {direz}\nREAL: {nome} | OTC: {nome} OTC\nV2 {ratio}x | RSI {rsi:.0f} | No spam 15m | {ora} IT")

def start_bot(): asyncio.run(bot_loop())
if __name__ == "__main__":
    threading.Thread(target=run_flask, daemon=True).start()
    start_bot()
