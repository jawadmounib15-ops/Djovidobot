# V36.8.9 SNIPER COMPLETO FINALE - TELEGRAM_TOKEN + TELEGRAM_CHAT_ID
import os, time, threading, requests
import yfinance as yf
from flask import Flask
from datetime import datetime

app = Flask(__name__)

@app.route('/')
def home():
    return "V36.8.9 SNIPER VIP LIVE - COMPLETO"

def run_flask():
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 10000)))

# --- NOMI GIUSTI TUOI ---
BOT_TOKEN = os.environ.get("TELEGRAM_TOKEN")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

print(f"AVVIO - TOKEN: {bool(BOT_TOKEN)} CHAT_ID: {bool(CHAT_ID)}")

def send_tg(msg):
    try:
        if not BOT_TOKEN or not CHAT_ID:
            print("TOKEN MANCANTI!")
            return
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        r = requests.post(url, data={"chat_id": CHAT_ID, "text": msg, "parse_mode": "Markdown"}, timeout=15)
        print(f"TG INVIATO: {r.status_code} {msg[:60]}")
    except Exception as e:
        print(f"Errore TG: {e}")

def calc_rsi(close, period=14):
    delta = close.diff()
    gain = delta.where(delta > 0, 0).rolling(window=period).mean()
    loss = -delta.where(delta < 0, 0).rolling(window=period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

COPPIE = {
    "EURUSD=X": "EUR/USD",
    "GBPUSD=X": "GBP/USD", 
    "EURGBP=X": "EUR/GBP"
}

def bot_loop():
    time.sleep(4)
    send_tg("✅✅ *V36.8.9 SNIPER COMPLETO LIVE* ✅✅\n\n🟢 Bot VIP avviato con TELEGRAM_TOKEN\n🔍 Scansione ogni 2 min\n💎 Filtro: L2+L5+L6 + RSI 35/65\n🚫 Anti-crollo attivo")

    while True:
        try:
            for symbol, nome in COPPIE.items():
                df = yf.download(symbol, period="2d", interval="15m", progress=False, auto_adjust=True)
                if df is None or len(df) < 50:
                    print(f"{nome} dati insufficienti")
                    continue

                close = df['Close']
                rsi = float(calc_rsi(close).iloc[-1])
                prezzo = float(close.iloc[-1])
                ema20 = float(close.ewm(span=20).mean().iloc[-1])
                ema50 = float(close.ewm(span=50).mean().iloc[-1])

                c1 = float(close.iloc[-1])
                c2 = float(close.iloc[-2])
                c3 = float(close.iloc[-3])
                crollo = (c1 < c2 and c2 < c3 and (c1 - c3) / c3 < -0.005)

                print(f"[{datetime.now().strftime('%H:%M:%S')}] {nome} RSI:{rsi:.1f} P:{prezzo:.5f} Buy:{ema20>ema50} Crollo:{crollo}")

                # BUY VIP
                if ema20 > ema50 and not crollo and rsi <= 35:
                    send_tg(f"✅✅✅ *V.I.P BUY {nome}* ✅✅✅\n💎 SNIPER TOP\n📉 RSI: {rsi:.1f} (ipervenduto)\n💰 Prezzo: {prezzo:.5f}\n✅ L2+L5+L6 confermati\n⏰ {datetime.now().strftime('%H:%M:%S')}")

                # SELL VIP
                if ema20 < ema50 and not crollo and rsi >= 65:
                    send_tg(f"✅✅✅ *V.I.P SELL {nome}* ✅✅✅\n🔻 SNIPER TOP\n📈 RSI: {rsi:.1f} (ipercomprato)\n💰 Prezzo: {prezzo:.5f}\n✅ L2+L5+L6 confermati\n⏰ {datetime.now().strftime('%H:%M:%S')}")

            print(f"--- Scansione finita {datetime.now().strftime('%H:%M:%S')} attendo 2 min ---")
            time.sleep(120)

        except Exception as e:
            print(f"Errore loop: {e}")
            import traceback
            traceback.print_exc()
            time.sleep(30)

if __name__ == "__main__":
    threading.Thread(target=run_flask, daemon=True).start()
    bot_loop()
