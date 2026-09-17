import os, time, requests, threading
import yfinance as yf
from datetime import datetime
from ta.momentum import RSIIndicator
from ta.trend import EMAIndicator
from http.server import HTTPServer, BaseHTTPRequestHandler

TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT = os.getenv("CHAT_ID")

def keep_alive():
    class H(BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200); self.end_headers(); self.wfile.write(b'Bot OK')
    HTTPServer(('0.0.0.0', int(os.getenv("PORT", 10000))), H).serve_forever()
threading.Thread(target=keep_alive, daemon=True).start()

PAIRS=["EURUSD=X","GBPUSD=X","USDJPY=X","USDCHF=X","EURJPY=X","GBPJPY=X"]
ultimo=0
def send(m):
    requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage", data={"chat_id":CHAT,"text":m,"parse_mode":"Markdown"})

print("Bot V9.7 FIX avviato")
send("✅ *Bot V9.7 FIXATO - Ora non si blocca più!*")

while True:
    try:
        if time.time()-ultimo < 900: time.sleep(30); continue
        for p in PAIRS:
            df=yf.download(p, period="3d", interval="5m", progress=False, auto_adjust=True)
            if len(df)<210: continue
            c=df['Close']; rsi=float(RSIIndicator(c,14).rsi().iloc[-1])
            ema50=float(EMAIndicator(c,50).ema_indicator().iloc[-1])
            ema200=float(EMAIndicator(c,200).ema_indicator().iloc[-1])
            price=float(c.iloc[-1])
            forte=False; txt=""
            if 30<=rsi<=42 and price>ema50 and ema50>ema200:
                forte=True; txt=f"🟢 *BUY ULTRA FORTE {p}*\nRSI {rsi:.1f} | 90%\nPrezzo {price:.5f}"
            elif 58<=rsi<=70 and price<ema50 and ema50<ema200:
                forte=True; txt=f"🔴 *SELL ULTRA FORTE {p}*\nRSI {rsi:.1f} | 90%\nPrezzo {price:.5f}"
            if forte:
                send(txt); print(txt); ultimo=time.time(); break
            else: print(f"{p} RSI {rsi:.1f} scartato")
        time.sleep(60)
    except Exception as e: print(e); time.sleep(60)
