import os, time, requests, threading
from flask import Flask
from datetime import datetime

app = Flask(__name__)

TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
PAIR = "EUR/USD OTC"
COOLDOWN = 300 # 5 min = TF 5M

ultimo = 0
prezzi = []

def tg(m):
    try:
        url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
        requests.post(url, data={"chat_id": CHAT_ID, "text": m}, timeout=10)
        print(m)
    except:
        pass

def get_price():
    try:
        r = requests.get("https://api.frankfurter.app/latest?from=EUR&to=USD", timeout=10).json()
        return float(r["rates"]["USD"])
    except:
        return None

def rsi(data):
    if len(data) < 15: return 50
    g=0; l=0
    for i in range(-14,0):
        d=data[i]-data[i-1]
        if d>0: g+=d
        else: l+=-d
    if l==0: return 100
    rs=(g/14)/(l/14)
    return 100-(100/(1+rs))

def bot_loop():
    global ultimo, prezzi
    tg("✅ V36.2 TF 5M LIVE - AVVIATO")
    print("BOT LOOP AVVIATO TF 5M")
    while True:
        try:
            if time.time() - ultimo < COOLDOWN:
                time.sleep(5)
                continue
            p = get_price()
            if not p:
                time.sleep(10)
                continue
            prezzi.append(p)
            if len(prezzi) > 50: prezzi.pop(0)
            if len(prezzi) < 20:
                print(f"Raccolgo {len(prezzi)}/20 {p}")
                time.sleep(30)
                continue
            ema9 = sum(prezzi[-9:])/9
            ema21 = sum(prezzi[-21:])/21
            rsi14 = rsi(prezzi)
            buy=0; sell=0
            if ema9 > ema21: buy+=1
            else: sell+=1
            if rsi14 < 35: buy+=1
            elif rsi14 > 65: sell+=1
            if prezzi[-1] > prezzi[-5]: buy+=1
            else: sell+=1
            if buy >= 2:
                tg(f"🟢 {PAIR} BUY TF 5M {datetime.now().strftime('%H:%M:%S')} | Scadenza 5 min | EMA {ema9:.5f} RSI {rsi14:.0f}")
                ultimo=time.time()
            elif sell >= 2:
                tg(f"🔴 {PAIR} SELL TF 5M {datetime.now().strftime('%H:%M:%S')} | Scadenza 5 min | EMA {ema9:.5f} RSI {rsi14:.0f}")
                ultimo=time.time()
            time.sleep(30)
        except Exception as e:
            print(e)
            time.sleep(10)

@app.route("/")
def home():
    return "V36.2 TF 5M LIVE - BOT RUNNING"

threading.Thread(target=bot_loop, daemon=True).start()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
