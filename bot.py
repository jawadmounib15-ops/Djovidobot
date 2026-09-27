import os, yfinance as yf, asyncio, threading
from flask import Flask
from telegram import Bot
from datetime import datetime

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
bot = Bot(token=TELEGRAM_TOKEN)

# Flask per tenere vivo Render
app = Flask(__name__)
@app.route('/')
def home():
    return "Bot OTC attivo - 1 msg ogni 5 min"

def run_flask():
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 10000)))

COPPIE = ["EURUSD=X", "GBPUSD=X", "USDJPY=X", "EURJPY=X", "GBPJPY=X"]

def is_weekend():
    return datetime.now().weekday() >= 5

def analizza(pair, tf):
    try:
        df = yf.Ticker(pair).history(period="3d", interval=tf)
        if len(df) < 50: return None
        df.rename(columns={'Open':'open','High':'high','Low':'low','Close':'close'}, inplace=True)
        df['ema9'] = df['close'].ewm(9).mean()
        df['ema21'] = df['close'].ewm(21).mean()
        df['ema50'] = df['close'].ewm(50).mean()
        delta = df['close'].diff()
        gain = delta.where(delta>0,0).rolling(14).mean()
        loss = -delta.where(delta<0,0).rolling(14).mean()
        df['rsi'] = 100 - (100 / (1 + gain/loss))
        last = df.iloc[-1]
        prev = df.iloc[-2]
        call_eng = last['close'] > last['open'] and prev['close'] < prev['open']
        put_eng = last['close'] < last['open'] and prev['close'] > prev['open']
        if last['ema9'] > last['ema21'] > last['ema50'] and call_eng and 38 < last['rsi'] < 62:
            return "CALL", last['rsi']
        if last['ema9'] < last['ema21'] < last['ema50'] and put_eng and 38 < last['rsi'] < 62:
            return "PUT", last['rsi']
        return None
    except:
        return None

async def bot_loop():
    tipo = "OTC 🔶 Weekend" if is_weekend() else "REALI 📊"
    await bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=f"✅ Bot ONLINE - Modalità {tipo}\n1 messaggio ogni 5 minuti - Fase STRETTA")
    while True:
        await asyncio.sleep(300)
        weekend = is_weekend()
        etichetta = "OTC" if weekend else "REAL"
        best = None
        for tf in ["5m","15m"]:
            for coppia in COPPIE:
                res = analizza(coppia, tf)
                if res:
                    direz, rsi = res
                    best = (coppia.replace("=X",""), tf, direz, rsi, etichetta)
                    break
            if best: break
        
        ora = datetime.now().strftime('%H:%M:%S')
        if best:
            nome, tf, direz, rsi, et = best
            emoji = "🟢" if direz=="CALL" else "🔴"
            await bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=f"{emoji} {nome} {tf} {et} - {direz} | RSI {rsi:.1f} | {ora}")
        else:
            await bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=f"⏳ {ora} - Nessun segnale pulito | {etichetta} | Prossimo tra 5 min")

def start_bot():
    asyncio.run(bot_loop())

if __name__ == "__main__":
    threading.Thread(target=run_flask, daemon=True).start()
    start_bot()
