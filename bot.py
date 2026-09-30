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
def home(): return "Bot POCKET V1 LARGO + DOPPIA CONFERMA ON"
def run_flask(): app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 10000)))

REAL_MAP = {
 "EURUSD=X":"EUR/USD","GBPUSD=X":"GBP/USD","AUDUSD=X":"AUD/USD",
 "USDJPY=X":"USD/JPY","EURJPY=X":"EUR/JPY","GBPJPY=X":"GBP/JPY",
 "AUDJPY=X":"AUD/JPY","EURGBP=X":"EUR/GBP","AUDCAD=X":"AUD/CAD","AUDCHF=X":"AUD/CHF"
}
OTC_MAP = {k: v+" OTC" for k,v in REAL_MAP.items()}
REAL_LIST, OTC_LIST = list(REAL_MAP.keys()), list(REAL_MAP.keys())
session = cffi_requests.Session(impersonate="chrome")
ROMA = pytz.timezone("Europe/Rome")

BODY_MIN, BODY_MAX = 0.07, 0.38
RATIO_MIN, RATIO_MAX = 2.0, 10.0
WICK_MAX = 0.40
RSI_MIN, RSI_MAX = 25, 75
COOLDOWN = 300
VOL_MULT = 0.50

ultimo_segnali = {}

def is_pinbar_doppia_conferma(o,h,l,c, ema9, ema21, ema50, ema200, rsi, prev, prev2):
    body = abs(c - o); rng = h - l
    if rng==0: return None
    up = h - max(o,c); low = min(o,c) - l
    if body < rng * BODY_MIN or body > rng * BODY_MAX: return None
    close_pos = (c - l) / rng
    dist_ema200 = abs(c - ema200)/ema200 if ema200 else 0

    # prev data
    prev_body = abs(prev['Close']-prev['Open'])
    prev_rng = prev['High']-prev['Low']
    prev_close_pos = (prev['Close']-prev['Low'])/prev_rng if prev_rng>0 else 0.5

    if low >= body*RATIO_MIN: # CALL
        ratio = low/body
        if not (RATIO_MIN <= ratio <= RATIO_MAX): return None
        if up > rng*WICK_MAX: return None
        if not (ema9 > ema21 and c > ema50): return None
        if not (RSI_MIN <= rsi <= RSI_MAX): return None
        if close_pos < 0.60: return None
        if dist_ema200 > 0.008: return None

        # === DOPPIA CONFERMA CALL ===
        # 1) prev deve essere rossa o con wick basso (rimbalzo)
        # 2) RSI deve stare risalendo (rsi > rsi prev)
        # 3) close attuale > open prev (ripresa)
        cond1 = prev['Close'] < prev['Open'] or (prev['Low'] < prev2['Low'] and prev_close_pos > 0.5)
        cond2 = c > prev['Open'] # engulf parziale
        cond3 = low > prev_rng * 0.3 # wick deve essere più lungo della prev
        if not (cond1 and cond2): return None
        if not cond3: return None
        return "CALL", round(ratio,1), int(close_pos*100)

    if up >= body*RATIO_MIN: # PUT
        ratio = up/body
        if not (RATIO_MIN <= ratio <= RATIO_MAX): return None
        if low > rng*WICK_MAX: return None
        if not (ema9 < ema21 and c < ema50): return None
        if not (RSI_MIN <= rsi <= RSI_MAX): return None
        if close_pos > 0.40: return None
        if dist_ema200 > 0.008: return None

        # === DOPPIA CONFERMA PUT ===
        cond1 = prev['Close'] > prev['Open'] or (prev['High'] > prev2['High'] and prev_close_pos < 0.5)
        cond2 = c < prev['Open']
        cond3 = up > prev_rng * 0.3
        if not (cond1 and cond2): return None
        if not cond3: return None
        return "PUT", round(ratio,1), int(close_pos*100)
    return None

def analizza():
    now_ts = datetime.now().timestamp()
    pool = [(t,"REAL",REAL_MAP[t]) for t in REAL_LIST] + [(t,"OTC",OTC_MAP[t]) for t in OTC_LIST]
    random.shuffle(pool)
    for ticker, tipo, nome in pool:
        key = f"{ticker}_{tipo}"
        if key in ultimo_segnali and now_ts - ultimo_segnali[key] < COOLDOWN: continue
        try:
            df = yf.Ticker(ticker, session=session).history(period="5d", interval="5m")
            if len(df) < 210: continue
            cl = df['Close']
            ema9, ema21, ema50, ema200 = cl.ewm(span=9).mean().iloc[-1], cl.ewm(span=21).mean().iloc[-1], cl.ewm(span=50).mean().iloc[-1], cl.ewm(span=200).mean().iloc[-1]
            delta = cl.diff()
            gain = delta.where(delta>0,0).rolling(14).mean()
            loss = -delta.where(delta<0,0).rolling(14).mean()
            rsi = 100 - (100/(1+gain/loss))
            last_rsi = float(rsi.iloc[-1])
            row, prev, prev2 = df.iloc[-1], df.iloc[-2], df.iloc[-3]
            avg_rng = (df['High'] - df['Low']).rolling(20).mean().iloc[-1]
            if (row['High'] - row['Low']) < avg_rng * VOL_MULT: continue
            res = is_pinbar_doppia_conferma(row['Open'],row['High'],row['Low'],row['Close'], ema9, ema21, ema50, ema200, last_rsi, prev, prev2)
            if res:
                d, ratio, close_pos = res
                ultimo_segnali[key] = now_ts
                return nome, tipo, d, last_rsi, ratio, close_pos
        except: continue
    return None

async def bot_loop():
    ora = datetime.now(ROMA).strftime('%H:%M:%S')
    await bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=f"✅ POCKET V1 LARGO + DOPPIA CONFERMA\nPinbar + Prev Engulf | {ora} IT")
    while True:
        await asyncio.sleep(60)
        res = analizza()
        ora = datetime.now(ROMA).strftime('%H:%M:%S')
        if res:
            nome, tipo, direz, rsi, ratio, close_pos = res
            emoji = "🟢" if direz=="CALL" else "🔴"
            tag = "🏦 REAL" if tipo=="REAL" else "🔶 OTC"
            await bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=f"{emoji} {nome} 5m - {direz} {tag}\n✅ Doppia conferma | {ratio}x | Close {close_pos}% | RSI {rsi:.0f} | {ora} IT")

def start_bot(): asyncio.run(bot_loop())
if __name__ == "__main__":
    threading.Thread(target=run_flask, daemon=True).start()
    start_bot()
