import os, time, threading, requests
from flask import Flask

app = Flask(__name__)
@app.route('/')
def home(): return "V28 POCKET LARGA - COME PRIMA"
@app.route('/ping')
def ping(): return "OK"

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

PAIRS = ["EURUSD_otc","GBPUSD_otc","AUDUSD_otc","USDCAD_otc","USDCHF_otc","USDJPY_otc","EURGBP_otc","EURJPY_otc","GBPJPY_otc","AUDCAD_otc"]

sent = {}
count = 0

def send_tg(m):
    try:
        requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
        data={"chat_id":TELEGRAM_CHAT_ID,"text":m,"parse_mode":"Markdown"}, timeout=10)
    except: pass
    print(m, flush=True)

def get_btc():
    try:
        r = requests.get("https://api.binance.com/api/v3/klines?symbol=BTCUSDT&interval=1m&limit=50", timeout=10)
        if r.status_code == 200:
            out=[]
            for k in r.json():
                out.append({"o":float(k[1]),"h":float(k[2]),"l":float(k[3]),"c":float(k[4])})
            return out
    except Exception as e:
        print(f"Err Binance {e}", flush=True)
    return []

def bot_loop():
    global count
    send_tg("✅ *V28 LARGA AVVIATA*\nLeggo da Binance, segnali per Pocket\nSoglia 8% = ti arrivano sicuro")
    while True:
        try:
            candles = get_btc()
            if not candles:
                print("Niente candele Binance, riprovo", flush=True)
                time.sleep(5)
                continue

            last = candles[-1]
            rng = last['h'] - last['l']
            if rng == 0:
                time.sleep(5)
                continue

            # LARGA - 8%
            up_wick = last['h'] - max(last['o'], last['c'])
            down_wick = min(last['o'], last['c']) - last['l']
            body = abs(last['o'] - last['c'])

            # BUY se wick sotto lunga
            perc_buy = (down_wick / rng) * 100
            perc_sell = (up_wick / rng) * 100

            print(f"BTC perc BUY {perc_buy:.1f}% SELL {perc_sell:.1f}% body {body}", flush=True)

            signal = None
            perc = 0
            if perc_buy >= 8 and body / rng <= 0.75:
                signal = "BUY"
                perc = perc_buy
            elif perc_sell >= 8 and body / rng <= 0.75:
                signal = "SELL"
                perc = perc_sell

            if signal:
                count += 1
                # Mandiamo 1 segnale ogni 90 sec per non spammare, ma gira su tutte le coppie
                for pair in PAIRS:
                    key = f"{pair}_{signal}"
                    if time.time() - sent.get(key, 0) > 90:
                        msg = f"💎 *M1 {pair} {signal} {perc:.0f}%* - ENTRA SU POCKET\nBTCUSDT: {last['c']:.2f}"
                        send_tg(msg)
                        sent[key] = time.time()
                        time.sleep(1)
                        break # manda solo 1 coppia per volta per test

            time.sleep(5)
        except Exception as e:
            print(f"Loop err {e}", flush=True)
            time.sleep(5)

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

threading.Thread(target=bot_loop, daemon=True).start()
run_flask()
