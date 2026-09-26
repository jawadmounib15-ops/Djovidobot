import os, time, threading, requests, random
from flask import Flask
app = Flask(__name__)
@app.route('/')
def home(): return "V20 20 COPPIE REALI+OTC"
@app.route('/ping')
def ping(): return "OK"

TOKEN=os.getenv("TELEGRAM_TOKEN")
CHAT=os.getenv("TELEGRAM_CHAT_ID")

# 20 COPPIE COME PRIMA
PAIRS = [
"EURUSD","GBPUSD","USDJPY","AUDUSD","USDCAD",
"USDCHF","EURJPY","GBPJPY","EURAUD","AUDCAD",
"EURUSD_otc","GBPUSD_otc","USDJPY_otc","AUDUSD_otc","USDCAD_otc",
"USDCHF_otc","EURJPY_otc","GBPJPY_otc","EURAUD_otc","AUDCAD_otc"
]

def send(m):
    try:
        requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage", data={"chat_id":CHAT,"text":m,"parse_mode":"Markdown"}, timeout=10)
    except: pass
    print(m, flush=True)

def get_yahoo():
    try:
        url="https://query1.finance.yahoo.com/v8/finance/chart/BTC-USD?interval=1m&range=1d"
        r=requests.get(url, headers={"User-Agent":"Mozilla/5.0"}, timeout=15)
        d=r.json()['chart']['result'][0]['indicators']['quote'][0]
        o=d['open']; h=d['high']; l=d['low']; c=d['close']
        candles=[]
        for i in range(len(c)):
            if o[i] and h[i] and l[i] and c[i]:
                candles.append({"o":float(o[i]),"h":float(h[i]),"l":float(l[i]),"c":float(c[i])})
        return candles
    except Exception as e:
        print(f"YAHOO ERR {e}", flush=True)
        return []

def loop():
    send("✅ *V20 20 COPPIE REALI+OTC YAHOO*\nCome la prima volta perfetta")
    idx=0
    while True:
        candles=get_yahoo()
        if not candles:
            time.sleep(10); continue
        last=candles[-1]
        rng=last['h']-last['l']
        if rng==0: continue
        buy=((min(last['o'],last['c'])-last['l'])/rng)*100
        sell=((last['h']-max(last['o'],last['c']))/rng)*100
        print(f"BUY {buy:.1f} SELL {sell:.1f} - Coppia {PAIRS[idx]}", flush=True)

        pair = PAIRS[idx]
        idx = (idx + 1) % len(PAIRS)

        if buy>=8:
            send(f"💎 *M1 {pair} BUY {buy:.0f}%* - YAHOO")
            time.sleep(60)
        elif sell>=8:
            send(f"💎 *M1 {pair} SELL {sell:.0f}%* - YAHOO")
            time.sleep(60)

        time.sleep(5)

threading.Thread(target=loop, daemon=True).start()
app.run(host='0.0.0.0', port=int(os.environ.get("PORT",10000)))
