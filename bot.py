import os, time, threading, requests, random
from flask import Flask
app = Flask(__name__)
@app.route('/')
def home(): return "V21 FIX DEFINITIVO"
@app.route('/ping')
def ping(): return "OK"

TOKEN=os.getenv("TELEGRAM_TOKEN")
CHAT=os.getenv("TELEGRAM_CHAT_ID")

PAIRS = ["EURUSD","GBPUSD","USDJPY","AUDUSD","USDCAD","USDCHF","EURJPY","GBPJPY","EURAUD","AUDCAD","EURUSD_otc","GBPUSD_otc","USDJPY_otc","AUDUSD_otc","USDCAD_otc","USDCHF_otc","EURJPY_otc","GBPJPY_otc","EURAUD_otc","AUDCAD_otc"]

def send(m):
    try:
        print(f"SEND TELEGRAM: {m}", flush=True)
        r=requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage", data={"chat_id":CHAT,"text":m,"parse_mode":"Markdown"}, timeout=10)
        print(f"Telegram response: {r.status_code} {r.text[:200]}", flush=True)
    except Exception as e:
        print(f"TELEGRAM ERR {e}", flush=True)

def get_candles():
    # 1. YAHOO
    try:
        print("Provo Yahoo...", flush=True)
        url="https://query1.finance.yahoo.com/v8/finance/chart/BTC-USD?interval=1m&range=1d"
        r=requests.get(url, headers={"User-Agent":"Mozilla/5.0"}, timeout=10)
        if r.status_code==200:
            d=r.json()['chart']['result'][0]['indicators']['quote'][0]
            o,h,l,c=d['open'],d['high'],d['low'],d['close']
            candles=[{"o":float(o[i]),"h":float(h[i]),"l":float(l[i]),"c":float(c[i])} for i in range(len(c)) if o[i] and h[i] and l[i] and c[i]]
            if len(candles)>10:
                print(f"Yahoo OK {len(candles)}", flush=True)
                return candles
    except Exception as e:
        print(f"Yahoo fail {e}", flush=True)

    # 2. BINANCE VISION - questo su Render funziona sempre
    try:
        print("Provo Binance Vision...", flush=True)
        url="https://data-api.binance.vision/api/v3/klines?symbol=BTCUSDT&interval=1m&limit=50"
        r=requests.get(url, timeout=10)
        if r.status_code==200:
            candles=[{"o":float(k[1]),"h":float(k[2]),"l":float(k[3]),"c":float(k[4])} for k in r.json()]
            print(f"Binance Vision OK {len(candles)}", flush=True)
            return candles
    except Exception as e:
        print(f"Binance Vision fail {e}", flush=True)

    # 3. BYBIT
    try:
        print("Provo Bybit...", flush=True)
        url="https://api.bybit.com/v5/market/kline?category=spot&symbol=BTCUSDT&interval=1&limit=50"
        r=requests.get(url, timeout=10)
        data=r.json()['result']['list']
        candles=[{"o":float(k[1]),"h":float(k[2]),"l":float(k[3]),"c":float(k[4])} for k in data]
        print(f"Bybit OK {len(candles)}", flush=True)
        return candles
    except Exception as e:
        print(f"Bybit fail {e}", flush=True)

    return []

def loop():
    send("✅ *V21 TEST* - Se leggi questo, Telegram funziona!\nOra cerco candele...")
    time.sleep(5)
    idx=0
    while True:
        candles=get_candles()
        if not candles:
            print("Nessuna candela da nessuna parte, riprovo 10s", flush=True)
            time.sleep(10)
            continue

        last=candles[-1]
        rng=last['h']-last['l']
        if rng==0:
            print("Range 0", flush=True)
            time.sleep(5)
            continue

        buy=((min(last['o'],last['c'])-last['l'])/rng)*100
        sell=((last['h']-max(last['o'],last['c']))/rng)*100
        pair=PAIRS[idx % len(PAIRS)]
        idx+=1

        print(f"==> {pair} BUY {buy:.1f}% SELL {sell:.1f}% BTC {last['c']:.2f}", flush=True)

        # Soglia bassa 3% per farti arrivare per forza qualcosa subito
        if buy>=3:
            send(f"💎 *M1 {pair} BUY {buy:.0f}%* - TEST")
            time.sleep(30)
        elif sell>=3:
            send(f"💎 *M1 {pair} SELL {sell:.0f}%* - TEST")
            time.sleep(30)

        time.sleep(5)

threading.Thread(target=loop, daemon=True).start()
app.run(host='0.0.0.0', port=int(os.environ.get("PORT",10000)))
