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
def home(): return "Bot POCKET 5m V2 STRETTO ON"
def run_flask(): app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 10000)))

YAHOO_MAP = {
 "EURUSD=X":"EUR/USD","GBPUSD=X":"GBP/USD","AUDUSD=X":"AUD/USD",
 "USDJPY=X":"USD/JPY","EURJPY=X":"EUR/JPY","GBPJPY=X":"GBP/JPY",
 "AUDJPY=X":"AUD/JPY","EURGBP=X":"EUR/GBP","AUDCAD=X":"AUD/CAD","AUDCHF=X":"AUD/CHF"
}
COPPIE = list(YAHOO_MAP.keys())
session = cffi_requests.Session(impersonate="chrome")
ROMA = pytz.timezone("Europe/Rome")

# === STRINGI QUI ===
BODY_MIN = 0.15 # prima 0.10 -> più stretto
BODY_MAX = 0.25 # prima 0.28 -> più stretto
RATIO_MIN = 3.0 # prima 2.6 -> vuole naso più lungo
RATIO_MAX = 6.0 # prima 8.0 -> toglie 43x e anche 7x
WICK_MAX = 0.22 # prima 0.25 -> wick opposto più piccolo
RSI_MIN = 42 # prima 40
RSI_MAX = 58 # prima 60
COOLDOWN = 1200 # 20 min prima 15 min
VOL_MULT = 0.85 # prima 0.75 -> vuole candele più volatili
EMA_GAP = 0.0005 # 0.05% di distanza tra EMA9 e 21

ultimo_segnali = {}

def is_pinbar_filtrata(o,h,l,c, ema9, ema21, ema50, rsi):
    body = abs(c - o)
    rng = h - l
    if rng==0: return None
    up = h - max(o,c)
    low = min(o,c) - l

    # STRETTO: body 15-25%
    if body < rng * BODY_MIN: return None
    if body > rng * BODY_MAX: return None

    if low >= body*RATIO_MIN:
        ratio = low/body
        if ratio > RATIO_MAX or ratio < RATIO_MIN: return None
        if up > rng*WICK_MAX: return None
        # STRETTO: gap EMA
        if not (ema9 > ema21 * (1+EMA_GAP) and c > ema50): return None
        if not (RSI_MIN <= rsi <= RSI_MAX): return None
        return "CALL", round(ratio,1)

    if up >= body*RATIO_MIN:
        ratio = up/body
        if ratio > RATIO_MAX or ratio < RATIO_MIN: return None
        if low > rng*WICK_MAX: return None
        if not (ema9 < ema21 * (1-EMA_GAP) and c < ema50): return None
        if not (RSI_MIN <= rsi <= RSI_MAX): return None
        return "PUT", round(ratio,1)
    return None

def analizza():
    now_ts = datetime.now().timestamp()
    for coppia in random.sample(COPPIE, len(COPPIE)):
        if coppia in ultimo_segnali:
            if now_ts - ultimo_segnali[coppia] < COOLDOWN:
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
            avg_rng = (df['High'] - df['Low']).rolling(20).mean().iloc[-1]
            if (row['High'] - row['Low']) < avg_rng * VOL_MULT: continue

            res = is_pinbar_filtrata(row['Open'],row['High'],row['Low'],row['Close'], ema9, ema21, ema50, last_rsi)
            if res:
                d, ratio = res
                ultimo_segnali[coppia] = now_ts
                return YAHOO_MAP[coppia], d, last_rsi, ratio
        except: continue
    return None

async def bot_loop():
    ora = datetime.now(ROMA).strftime('%H:%M:%S')
    await bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=f"✅ POCKET 5m V2 STRETTO\nBody {int(BODY_MIN*100)}-{int(BODY_MAX*100)}% | Ratio {RATIO_MIN}-{RATIO_MAX}x | RSI {RSI_MIN}-{RSI_MAX} | CD {COOLDOWN//60}m | {ora} IT")
    while True:
        await asyncio.sleep(90)
        res = analizza()
        ora = datetime.now(ROMA).strftime('%H:%M:%S')
        if res:
            nome, direz, rsi, ratio = res
            emoji = "🟢" if direz=="CALL" else "🔴"
            await bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=f"{emoji} {nome} 5m - {direz}\nV2 {ratio}x | RSI {rsi:.0f} | Body {int(BODY_MIN*100)}-{int(BODY_MAX*100)}% | {ora} IT")

def start_bot(): asyncio.run(bot_loop())
if __name__ == "__main__":
    threading.Thread(target=run_flask, daemon=True).start()
    start_bot()
