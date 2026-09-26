import os, time, threading, requests, json
from flask import Flask
from datetime import datetime

app = Flask(__name__)
@app.route('/')
def home(): return "V22 AUTO POCKET - 15% - FINAL"
@app.route('/ping')
def ping(): return "OK"

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
POCKET_SSID = os.getenv("POCKET_SSID")

PAIRS = ["EURUSD_otc","GBPUSD_otc","EURJPY_otc","GBPJPY_otc","AUDCAD_otc","EURGBP_otc"]
sent = {}

def send_tg(m):
    try:
        requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage", data={"chat_id":TELEGRAM_CHAT_ID,"text":m,"parse_mode":"Markdown"}, timeout=10)
        print(m)
    except Exception as e:
        print(e)

def get_pocket_candles_auto(pair, period=300):
    # METODO 1: API web di Pocket (non bloccata)
    try:
        asset = pair.replace("_otc","").upper()
        # Endpoint che usa il sito ufficiale
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/122.0.0.0",
            "Origin": "https://pocketoption.com",
            "Referer": "https://pocketoption.com/",
            "Cookie": f"session={POCKET_SSID}"
        }
        # Proviamo l'API history del sito
        url = f"https://pocketoption.com/api/candles?asset={asset}&period={period}&count=50"
        r = requests.get(url, headers=headers, timeout=15)
        if r.status_code == 200:
            data = r.json()
            if isinstance(data, list) and len(data) > 10:
                candles = []
                for c in data:
                    if isinstance(c, dict):
                        candles.append(c)
                    elif isinstance(c, list) and len(c) >= 4:
                        candles.append({"open":float(c[1]),"close":float(c[2]),"high":float(c[3]),"low":float(c[4])})
                if len(candles) > 10:
                    return candles
    except Exception as e:
        print(f"API WEB FAIL {e}")

    # METODO 2: Fallback Binance (sempre funzionante)
    try:
        bin_map = {"EURUSD_otc":"EURUSDT","GBPUSD_otc":"GBPUSDT","EURJPY_otc":"EURJPY","GBPJPY_otc":"GBPJPY","AUDCAD_otc":"AUDCAD","EURGBP_otc":"EURGBP"}
        sym = bin_map.get(pair, "EURUSDT")
        url = f"https://api.binance.com/api/v3/klines?symbol={sym}&interval=5m&limit=50"
        r = requests.get(url, timeout=10).json()
        candles = []
        for x in r:
            candles.append({"open":float(x[1]),"high":float(x[2]),"low":float(x[3]),"close":float(x[4])})
        return candles
    except:
        return []

def check_15_percent(pair):
    candles = get_pocket_candles_auto(pair, 300)
    if len(candles) < 20:
        return

    last = candles[-2]
    o = float(last.get('open',0)); c = float(last.get('close',0))
    h = float(last.get('high',0)); l = float(last.get('low',0))
    total = h-l
    if total == 0: return
    body = abs(c-o); upper = h-max(o,c); lower = min(o,c)-l

    signal = None
    if lower/total >= 0.15 and body/total <= 0.70:
        signal = "BUY"
        perc = lower/total*100
    elif upper/total >= 0.15 and body/total <= 0.70:
        signal = "SELL"
        perc = upper/total*100
    else:
        return

    key = f"{pair}_M5_{signal}"
    if key in sent and time.time() - sent[key] < 240:
        return

    emoji = "🟢" if signal == "BUY" else "🔴"
    send_tg(f"💎 *M5 {emoji} {pair} {signal}*\n⚡ TURBO {perc:.0f}% Body {body/total*100:.0f}%\n📊 Auto da Pocket\n⏰ {datetime.now().strftime('%H:%M:%S')}")
    sent[key] = time.time()

def bot_loop():
    send_tg("✅ *V22 FINAL ONLINE*\n🔥 Legge candele auto da Pocket\n💥 Strategia 15% attiva - Basta prove")
    while True:
        for p in PAIRS:
            try: check_15_percent(p)
            except Exception as e: print(e)
            time.sleep(2)
        time.sleep(15)

def run_flask():
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT",10000)))

if __name__ == "__main__":
    threading.Thread(target=run_flask, daemon=True).start()
    bot_loop()
