# V36.8.9 SNIPER CORRETTO FINALE - FIX DEFINITIVO
import os, time, threading, requests
import yfinance as yf
from flask import Flask
from datetime import datetime

app = Flask(__name__)
@app.route('/')
def home(): return "V36.8.9 SNIPER CORRETTO LIVE - VIP"
def run_flask():
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 10000)))

BOT_TOKEN = os.environ.get("TELEGRAM_TOKEN") or os.environ.get("BOT_TOKEN") or os.environ.get("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID") or os.environ.get("TELEGRAM_CHAT_ID")

def send_tg(msg):
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        requests.post(url, data={"chat_id": CHAT_ID, "text": msg, "parse_mode": "Markdown"}, timeout=15)
        print(f"TG OK: {msg[:50]}")
    except Exception as e:
        print(f"Err TG: {e}")

def calc_rsi(close, period=14):
    delta = close.diff()
    gain = delta.where(delta > 0, 0).rolling(window=period).mean()
    loss = -delta.where(delta < 0, 0).rolling(window=period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

COPPIE = {"EURUSD=X": "EUR/USD", "GBPUSD=X": "GBP/USD", "EURGBP=X": "EUR/GBP"}

def bot_loop():
    time.sleep(4)
    send_tg("✅ *V36.8.9 SNIPER CORRETTO LIVE*\n🟢 Fixato - Ora gira perfetto\n🔍 Scansione ogni 2 min\n💎 Filtro L2+L5+L6 + RSI 35/65")

    while True:
        try:
            for sym, nome in COPPIE.items():
                df = yf.download(sym, period="2d", interval="15m", progress=False, auto_adjust=True)
                if df is None or len(df) < 50: continue
                close = df['Close']
                # Fix pandas
                try:
                    if close.ndim > 1: close = close.squeeze()
                except: pass
                
                rsi = float(calc_rsi(close).iloc[-1])
                prezzo = float(close.iloc[-1])
                ema20 = float(close.ewm(span=20).mean().iloc[-1])
                ema50 = float(close.ewm(span=50).mean().iloc[-1])

                # L6 fixato - senza bug
                c1, c2, c3 = float(close.iloc[-1]), float(close.iloc[-2]), float(close.iloc[-3])
                crollo = (c1 < c2 and c2 < c3 and (c1-c3)/c3 < -0.005)

                print(f"[{datetime.now().strftime('%H:%M:%S')}] {nome} RSI {rsi:.1f} TrendBuy {ema20>ema50} Crollo {crollo}")

                if ema20 > ema50 and not crollo and rsi <= 35:
                    send_tg(f"✅✅ V.I.P BUY {nome}\n📉 RSI {rsi:.1f}\n💰 {prezzo:.5f}\n✅ L2+L5+L6")
                if ema20 < ema50 and not crollo and rsi >= 65:
                    send_tg(f"🔻 V.I.P SELL {nome}\n📈 RSI {rsi:.1f}\n💰 {prezzo:.5f}\n✅ L2+L5+L6")

            time.sleep(120)
        except Exception as e:
            print(f"Err loop: {e}")
            time.sleep(30)

if __name__ == "__main__":
    threading.Thread(target=run_flask, daemon=True).start()
    bot_loop()
