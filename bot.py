import os, time, requests, threading
import yfinance as yf
from ta.momentum import RSIIndicator
from ta.trend import EMAIndicator
from http.server import HTTPServer, BaseHTTPRequestHandler

TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT = os.getenv("CHAT_ID")

def keep_alive():
    class H(BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b'OK')
        def log_message(self, a, *b):
            return
    HTTPServer(('0.0.0.0', int(os.getenv("PORT", 10000))), H).serve_forever()

threading.Thread(target=keep_alive, daemon=True).start()

PAIRS = ["EURUSD=X","GBPUSD=X","USDJPY=X","USDCHF=X","EURJPY=X","GBPJPY=X"]
ultimo = 0

def send(m):
    try:
        requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage", data={"chat_id":CHAT,"text":m,"parse_mode":"Markdown"})
    except:
        pass

print("Bot V9.8 avviato")
send("Bot V9.8 FIXATO - Ora funziona - Senza emoji")

while True:
    try:
        if time.time() - ultimo < 900:
            time.sleep(30)
            continue
        for p in PAIRS:
            df = yf.download(p, period="3d", interval="5m", progress=False, auto_adjust=True)
            if len(df) < 210:
                continue
            c = df['Close']
            rsi = float(RSIIndicator(c, 14).rsi().iloc[-1])
            ema50 = float(EMAIndicator(c, 50).ema_indicator().iloc[-1])
            ema200 = float(EMAIndicator(c, 200).ema_indicator().iloc[-1])
            price = float(c.iloc[-1])
            if 30 <= rsi <= 42 and price > ema50 and ema50 > ema200:
                send(f"BUY FORTE {p} RSI {rsi:.1f} 90% Prezzo {price:.5f}")
                ultimo = time.time()
                break
            if 58 <= rsi <= 70 and price < ema50 and ema50 < ema200:
                send(f"SELL FORTE {p} RSI {rsi:.1f} 90% Prezzo {price:.5f}")
                ultimo = time.time()
                break
            print(f"{p} RSI {rsi:.1f} scartato")
        time.sleep(60)
    except Exception as e:
        print(e)
        time.sleep(60)
