import os, yfinance as yf, asyncio, threading
from flask import Flask
from telegram import Bot
from datetime import datetime

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
bot = Bot(token=TELEGRAM_TOKEN)

app = Flask(__name__)
@app.route('/')
def home(): return "Bot FALLBACK ON"
def run_flask(): app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 10000)))

COPPIE = ["AUDCAD=X","AUDCHF=X","AUDUSD=X","CADCHF=X","CADJPY=X","CHFJPY=X","EURCHF=X","GBPUSD=X","AUDJPY=X","AUDNZD=X","EURGBP=X","GBPJPY=X","EURJPY=X","NZDUSD=X"]

def analizza(pair):
    try:
        for tf in ["15m","5m","1h"]:
            df = yf.Ticker(pair).history(period="10d", interval=tf)
            if len(df) < 20: continue
            df.rename(columns={'Open':'open','High':'high','Low':'low','Close':'close'}, inplace=True)
            delta = df['close'].diff()
            gain = delta.where(delta>0,0).rolling(14).mean()
            loss = -delta.where(delta<0,0).rolling(14).mean()
            df['rsi'] = 100 - (100 / (1 + gain/loss))
            last = df.iloc[-1]; prev = df.iloc[-2]

            body = abs(last['close']-last['open'])
            lower = min(last['close'], last['open']) - last['low']
            upper = last['high'] - max(last['close'], last['open'])
            rng = last['high']-last['low']
            if rng==0 or body==0: continue

            # 1. ENGULFING
            if last['close'] > last['open'] and prev['close'] < prev['open'] and last['close'] > prev['open']:
                if 30 <= last['rsi'] <= 70: return tf, "CALL", last['rsi'], "ENGULF"
            if last['close'] < last['open'] and prev['close'] > prev['open'] and last['close'] < prev['open']:
                if 30 <= last['rsi'] <= 70: return tf, "PUT", last['rsi'], "ENGULF"
            # 2. PINBAR
            if lower > body*1.2:
                if last['rsi'] < 60: return tf, "CALL", last['rsi'], f"PIN {lower/body:.1f}x"
            if upper > body*1.2:
                if last['rsi'] > 40: return tf, "PUT", last['rsi'], f"PIN {upper/body:.1f}x"
        # 3. FALLBACK RSI PURO - garantisce segnale
        df = yf.Ticker(pair).history(period="10d", interval="15m")
        if len(df) > 20:
            df.rename(columns={'Open':'open','High':'high','Low':'low','Close':'close'}, inplace=True)
            delta = df['close'].diff()
            gain = delta.where(delta>0,0).rolling(14).mean()
            loss = -delta.where(delta<0,0).rolling(14).mean()
            df['rsi'] = 100 - (100 / (1 + gain/loss))
            last = df.iloc[-1]
            if last['rsi'] < 42: return "15m", "CALL", last['rsi'], "RSI BASSO"
            if last['rsi'] > 58: return "15m", "PUT", last['rsi'], "RSI ALTO"
        return None
    except: return None

async def bot_loop():
    await bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=f"🔧 Bot FALLBACK ON\n14 REALI | Garanzia segnale | 2min")
    while True:
        await asyncio.sleep(120)
        best = None
        candidati = []
        for coppia in COPPIE:
            res = analizza(coppia)
            if res:
                tf, direz, rsi, tipo = res
                candidati.append((coppia, tf, direz, rsi, tipo))
                # prendi il più estremo
                if "ENGULF" in tipo or "PIN" in tipo:
                    best = (coppia.replace("=X",""), tf, direz, rsi, tipo)
                    break
        if not best and candidati:
            # se solo RSI, prendi il più estremo
            candidati.sort(key=lambda x: abs(x[3]-50), reverse=True)
            c = candidati[0]
            best = (c[0].replace("=X",""), c[1], c[2], c[3], c[4])

        ora = datetime.now().strftime('%H:%M:%S')
        if best:
            nome, tf, direz, rsi, tipo = best
            emoji = "🟢" if direz=="CALL" else "🔴"
            await bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=f"{emoji} {nome} {tf} OTC - {direz}\n{tipo} | RSI {rsi:.1f} | {ora}")
        else:
            await bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=f"🔍 {ora} - yfinance vuoto, riprovo")

def start_bot(): asyncio.run(bot_loop())
if __name__ == "__main__":
    threading.Thread(target=run_flask, daemon=True).start()
    start_bot()
