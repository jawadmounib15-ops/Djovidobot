import os, yfinance as yf, asyncio, threading
from flask import Flask
from telegram import Bot
from datetime import datetime

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
bot = Bot(token=TELEGRAM_TOKEN)

app = Flask(__name__)
@app.route('/')
def home(): return "Bot REALI LARGO ON"
def run_flask(): app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 10000)))

COPPIE = [
"AUDCAD=X","AUDCHF=X","AUDUSD=X","CADCHF=X","CADJPY=X",
"CHFJPY=X","EURCHF=X","GBPUSD=X","AUDJPY=X","AUDNZD=X",
"EURGBP=X","GBPJPY=X","EURJPY=X","NZDUSD=X"
]

def is_weekend(): return datetime.now().weekday() >= 5

def analizza_engulfing(pair, tf):
    try:
        df = yf.Ticker(pair).history(period="5d", interval=tf)
        if len(df) < 100: return None
        df.rename(columns={'Open':'open','High':'high','Low':'low','Close':'close'}, inplace=True)
        df['ema9'] = df['close'].ewm(9).mean()
        df['ema21'] = df['close'].ewm(21).mean()
        df['ema50'] = df['close'].ewm(50).mean()
        delta = df['close'].diff()
        gain = delta.where(delta>0,0).rolling(14).mean()
        loss = -delta.where(delta<0,0).rolling(14).mean()
        df['rsi'] = 100 - (100 / (1 + gain/loss))
        df['atr'] = (df['high']-df['low']).rolling(14).mean()
        last = df.iloc[-1]; prev = df.iloc[-2]; prev2 = df.iloc[-3]
        trend_call = last['ema9'] > last['ema21'] > last['ema50']
        trend_put = last['ema9'] < last['ema21'] < last['ema50']
        rsi_ok = 45 <= last['rsi'] <= 57
        body = abs(last['close']-last['open']); range_c = last['high']-last['low']
        body_big = body > range_c * 0.5 if range_c>0 else False
        call_eng = last['close'] > last['open'] and prev['close'] < prev['open'] and last['close'] > prev['open'] and body_big
        put_eng = last['close'] < last['open'] and prev['close'] > prev['open'] and last['close'] < prev['open'] and body_big
        momentum_call = prev['close'] >= prev2['close']*0.999
        momentum_put = prev['close'] <= prev2['close']*1.001
        dist = abs(last['close'] - last['ema50']) / last['atr'] if last['atr']>0 else 10
        if trend_call and rsi_ok and call_eng and momentum_call and dist < 2.2: return "CALL", last['rsi'], "ENGULFING"
        if trend_put and rsi_ok and put_eng and momentum_put and dist < 2.2: return "PUT", last['rsi'], "ENGULFING"
        return None
    except: return None

def analizza_pinbar(pair, tf):
    try:
        df = yf.Ticker(pair).history(period="5d", interval=tf)
        if len(df) < 100: return None
        df.rename(columns={'Open':'open','High':'high','Low':'low','Close':'close'}, inplace=True)
        df['ema21'] = df['close'].ewm(21).mean()
        df['ema50'] = df['close'].ewm(50).mean()
        delta = df['close'].diff()
        gain = delta.where(delta>0,0).rolling(14).mean()
        loss = -delta.where(delta<0,0).rolling(14).mean()
        df['rsi'] = 100 - (100 / (1 + gain/loss))
        last = df.iloc[-1]
        body = abs(last['close']-last['open'])
        upper_wick = last['high'] - max(last['close'], last['open'])
        lower_wick = min(last['close'], last['open']) - last['low']
        range_c = last['high']-last['low']
        if range_c == 0 or body == 0: return None
        corpo_piccolo = body < range_c * 0.4
        is_pinbar_call = lower_wick > body * 2.0 and upper_wick < body * 0.8 and corpo_piccolo
        is_pinbar_put = upper_wick > body * 2.0 and lower_wick < body * 0.8 and corpo_piccolo
        rsi_ok = 42 <= last['rsi'] <= 58
        near_ema = abs(last['close'] - last['ema21']) < (range_c * 2.5)
        if is_pinbar_call and rsi_ok and near_ema and last['ema21'] > last['ema50']:
            return "CALL", last['rsi'], f"PINBAR {lower_wick/body:.1f}x"
        if is_pinbar_put and rsi_ok and near_ema and last['ema21'] < last['ema50']:
            return "PUT", last['rsi'], f"PINBAR {upper_wick/body:.1f}x"
        return None
    except: return None

async def bot_loop():
    tipo = "OTC 🔶" if is_weekend() else "REALI 📊"
    await bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=f"🔧 Bot LARGO ON\n14 REALI | Engulfing 50% + Pinbar 2.0x\nRSI 42-58 | Modalità {tipo} | 1 msg/5min")
    while True:
        await asyncio.sleep(300)
        etichetta = "OTC" if is_weekend() else "REAL"
        best = None
        for tf in ["5m","15m"]:
            for coppia in COPPIE:
                res = analizza_engulfing(coppia, tf)
                if res:
                    direz, rsi, tipo_sig = res
                    best = (coppia.replace("=X",""), tf, direz, rsi, tipo_sig, etichetta); break
            if best: break
        if not best:
            for tf in ["5m","15m"]:
                for coppia in COPPIE:
                    res = analizza_pinbar(coppia, tf)
                    if res:
                        direz, rsi, tipo_sig = res
                        best = (coppia.replace("=X",""), tf, direz, rsi, tipo_sig, etichetta); break
                if best: break
        ora = datetime.now().strftime('%H:%M:%S')
        if best:
            nome, tf, direz, rsi, tipo_sig, et = best
            emoji = "🟢" if direz=="CALL" else "🔴"
            await bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=f"{emoji} {nome} {tf} {et} - {direz}\n{tipo_sig} | RSI {rsi:.1f} | {ora}")
        else:
            await bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=f"🔍 {ora} - Scansione ok | {etichetta} | 14 coppie")

def start_bot(): asyncio.run(bot_loop())
if __name__ == "__main__":
    threading.Thread(target=run_flask, daemon=True).start()
    start_bot()
