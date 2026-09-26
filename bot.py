import os, time, threading, requests
from flask import Flask
app = Flask(__name__)
@app.route('/')
def home(): return "V28 YAHOO COME PRIMA"
@app.route('/ping')
def ping(): return "OK"

TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT = os.getenv("TELEGRAM_CHAT_ID")

def send(m):
    try:
        requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage", data={"chat_id":CHAT,"text":m,"parse_mode":"Markdown"}, timeout=10)
    except: pass
    print(m, flush=True)

def get_yahoo():
    try:
        # Yahoo BTC come prima
        url = "https://query1.finance.yahoo.com/v8/finance/chart/BTC-USD?interval=1m&range=1d"
        headers = {"User-Agent": "Mozilla/5.0"}
        r = requests.get(url, headers=headers, timeout=10)
        j = r.json()
        result = j['chart']['result'][0]
        o = result['indicators']['quote'][0]['open']
        h = result['indicators']['quote'][0]['high']
        l = result['indicators']['quote'][0]['low']
        c = result['indicators']['quote'][0]['close']
        candles = []
        for i in range(len(c)):
            if o[i] and h[i] and l[i] and c[i]:
                candles.append({"o":float(o[i]),"h":float(h[i]),"l":float(l[i]),"c":float(c[i])})
        print(f"Yahoo OK {len(candles)} candele", flush=True)
        return candles[-50:]
    except Exception as e:
        print(f"Yahoo err {e}", flush=True)
        return []

def loop():
    send("✅ *V28 YAHOO COME PRIMA AVVIATA*\nLeggo da Yahoo come quando funzionava")
    while True:
        try:
            candles = get_yahoo()
            if not candles:
                print("Yahoo niente, riprovo", flush=True)
                time.sleep(10)
                continue

            last = candles[-1]
            rng = last['h']-last['l']
            if rng == 0:
                time.sleep(5); continue

            buy = ((min(last['o'],last['c'])-last['l'])/rng)*100
            sell = ((last['h']-max(last['o'],last['c']))/rng)*100
            print(f"YAHOO BUY {buy:.1f}% SELL {sell:.1f}% BTC {last['c']:.0f}", flush=True)

            if buy >= 8:
                send(f"💎 *M1 EURUSD_otc BUY {buy:.0f}%* - YAHOO - ENTRA POCKET")
                time.sleep(60)
            elif sell >= 8:
                send(f"💎 *M1 EURUSD_otc SELL {sell:.0f}%* - YAHOO - ENTRA POCKET")
                time.sleep(60)

            time.sleep(5)
        except Exception as e:
            print(f"Loop err {e}", flush=True)
            time.sleep(5)

threading.Thread(target=loop, daemon=True).start()
app.run(host='0.0.0.0', port=int(os.environ.get("PORT",10000)))
