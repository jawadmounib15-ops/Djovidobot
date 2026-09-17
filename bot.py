import os, time, requests, threading
import yfinance as yf
from ta.trend import EMAIndicator
from ta.momentum import RSIIndicator
from http.server import HTTPServer, BaseHTTPRequestHandler

TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT = os.getenv("TELEGRAM_CHAT_ID")

def keep_alive():
    class H(BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b'OK')
        def log_message(self, a, *b):
            return
    HTTPServer(('0.0.0.0', int(os.getenv("PORT", "10000"))), H).serve_forever()
threading.Thread(target=keep_alive, daemon=True).start()

PAIRS = ["EURUSD=X","GBPUSD=X","USDJPY=X","USDCHF=X","EURJPY=X","GBPJPY=X"]

def send(m):
    try:
        requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage", data={"chat_id": CHAT, "text": m})
    except:
        pass

send("Bot V11.1 LIVE - 15 MINUTI - Regole allargate piano!")

while True:
    try:
        for p in PAIRS:
            df = yf.download(p, period="5d", interval="15m", progress=False, auto_adjust=True)
            if len(df) < 100:
                continue
            c = df['Close']
            ema50 = float(EMAIndicator(c, 50).ema_indicator().iloc[-1])
            ema200 = float(EMAIndicator(c, 200).ema_indicator().iloc[-1])
            rsi = float(RSIIndicator(c, 14).rsi().iloc[-1])
            price = float(c.iloc[-1])

            signal = None
            if price > ema50 and ema50 > ema200 and 30 < rsi < 68:
                signal = f"BUY FORTE 15MIN {p} RSI {rsi:.0f} - Entra 15min"
            elif price < ema50 and ema50 < ema200 and 32 < rsi < 70:
                signal = f"SELL FORTE 15MIN {p} RSI {rsi:.0f} - Entra 15min"

            if signal:
                send(signal)
            time.sleep(3)
        time.sleep(900)
    except:
        time.sleep(60)
