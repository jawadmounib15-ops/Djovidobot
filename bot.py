import os, yfinance as yf, asyncio, threading
from flask import Flask
from telegram import Bot
from datetime import datetime

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
bot = Bot(token=TELEGRAM_TOKEN)

app = Flask(__name__)
@app.route('/')
def home(): return "Bot ULTRA LARGO OTC ON"
def run_flask(): app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 10000)))

COPPIE = ["AUDCAD=X","AUDCHF=X","AUDUSD=X","CADCHF=X","CADJPY=X","CHFJPY=X","EURCHF=X","GBPUSD=X","AUDJPY=X","AUDNZD=X","EURGBP=X","GBPJPY=X","EURJPY=X","NZDUSD=X"]

def analizza_ultra(pair, tf):
    try:
        df = yf.Ticker(pair).history(period="7d", interval=tf)
        if len(df) < 10: return None
        df.rename(columns={'Open':'open','High':'high','Low':'low','Close':'close'}, inplace=True)
        delta = df['close'].diff()
        gain = delta.where(delta>0,0).rolling(14).mean()
        loss = -delta.where(delta<0,0).rolling(14).mean()
        df['rsi'] = 100 - (100 / (1 + gain/loss))
        last = df.iloc[-1]; prev = df.iloc[-2]
        body = abs(last['close']-last['open'])
        upper = last['high'] - max(last['close'], last['open'])
        lower = min(last['close'], last['open']) - last['low']
        range_c = last['high']-last['low']
        if range_c == 0: return None
        
        # 1. ENGULFING ULTRA LARGO - senza trend
        eng_call = last['close'] > last['open'] and prev['close'] < prev['open'] and last['close'] > prev['open'] and last['open'] < prev['close']
        eng_put = last['close'] < last['open'] and prev['close'] > prev['open'] and last['close'] < prev['open'] and last['open'] > prev['close']
        
        # 2. PINBAR ULTRA LARGO
        pin_call = lower > body * 1.5 and body < range_c * 0.5 if body>0 else False
        pin_put = upper > body * 1.5 and body < range_c * 0.5 if body>0 else False
        
        rsi_ok = 35 <= last['rsi'] <= 65
        
        if rsi_ok and eng_call: return "CALL", last['rsi'], "ENGULFING ULTRA"
        if rsi_ok and eng_put: return "PUT", last['rsi'], "ENGULFING ULTRA"
        if rsi_ok and pin_call: return "CALL", last['rsi'], f"PINBAR {lower/body:.1f}x"
        if rsi_ok and pin_put: return "PUT", last['rsi'], f"PINBAR {upper/body:.1f}x"
        return None
    except: return None

async def bot_loop():
    await bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=f"🔧 Bot ULTRA LARGO ON\n14 REALI | RSI 35-65 | Solo Engulf/Pin\nOTC Domenica | 1 msg/2min")
    while True:
        await asyncio.sleep(120) # ogni 2 min ora
        best = None
        for tf in ["5m","15m","1h"]:
            for coppia in COPPIE:
                res = analizza_ultra(coppia, tf)
                if res:
                    direz, rsi, tipo_sig = res
                    best = (coppia.replace("=X",""), tf, direz, rsi, tipo_sig); break
            if best: break
        ora = datetime.now().strftime('%H:%M:%S')
        if best:
            nome, tf, direz, rsi, tipo_sig = best
            emoji = "🟢" if direz=="CALL" else "🔴"
            await bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=f"{emoji} {nome} {tf} OTC - {direz}\n{tipo_sig} | RSI {rsi:.1f} | {ora}")
        else:
            await bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=f"🔍 {ora} - Scan 14 coppie 5m/15m/1h - nessun pattern al momento")

def start_bot(): asyncio.run(bot_loop())
if __name__ == "__main__":
    threading.Thread(target=run_flask, daemon=True).start()
    start_bot()
