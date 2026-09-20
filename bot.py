import os, time, requests, threading, random
from flask import Flask
from datetime import datetime
app = Flask(__name__)
TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
PAIRS = [("EUR/USD OTC","EUR","USD"),("GBP/USD OTC","GBP","USD"),("USD/JPY OTC","USD","JPY"),("AUD/USD OTC","AUD","USD"),("EUR/GBP OTC","EUR","GBP")]
COOLDOWN=400
store={n:{"prezzi":[],"ultimo":0} for n,_,_ in PAIRS}

def tg(m):
    try: requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage",data={"chat_id":CHAT_ID,"text":m},timeout=10)
    except: pass

def get_price_fx(frm,to):
    try:
        r=requests.get(f"https://api.frankfurter.app/latest?from={frm}&to={to}",timeout=10).json()
        base=float(r["rates"][to])
        noise = random.uniform(-0.0008, 0.0008) * base # allargato pochissimo
        return base + noise
    except: return None

def rsi(data):
    if len(data)<15: return 50
    g=0; l=0
    for i in range(-14,0):
        d=data[i]-data[i-1]
        if d>0: g+=d
        else: l+=-d
    if g==0 and l==0: return 50
    if l==0: return 70
    if g==0: return 30
    rs=(g/14)/(l/14)
    return 100-(100/(1+rs))

def bot_loop():
    tg("✅ V36.6 SEMI-STRETTO TF 5M LIVE")
    while True:
        try:
            for name,frm,to in PAIRS:
                s=store[name]
                if time.time()-s["ultimo"]<COOLDOWN: continue
                p=get_price_fx(frm,to)
                if not p: continue
                s["prezzi"].append(p)
                if len(s["prezzi"])>60: s["prezzi"].pop(0)
                if len(s["prezzi"])<25: continue
                prezzi=s["prezzi"]
                ema9=sum(prezzi[-9:])/9
                ema21=sum(prezzi[-21:])/21
                rsi14=rsi(prezzi)
                if 48 < rsi14 < 52: continue # prima 45-55, ora solo 48-52 stretto
                if abs(ema9-ema21) / ema21 < 0.00008: continue # prima 0.00015, ora 0.00008

                buy=0; sell=0
                if ema9>ema21: buy+=1
                else: sell+=1
                if rsi14<38: buy+=1
                elif rsi14>62: sell+=1
                if prezzi[-1]>prezzi[-10]: buy+=1
                else: sell+=1

                if buy>=2:
                    tg(f"🟢 {name} BUY TF 5M {datetime.now().strftime('%H:%M:%S')} | Scadenza 5 min | RSI {rsi14:.0f}")
                    s["ultimo"]=time.time()
                elif sell>=2:
                    tg(f"🔴 {name} SELL TF 5M {datetime.now().strftime('%H:%M:%S')} | Scadenza 5 min | RSI {rsi14:.0f}")
                    s["ultimo"]=time.time()
            time.sleep(35)
        except Exception as e:
            print(e); time.sleep(10)

@app.route("/")
def home(): return "V36.6 SEMI-STRETTO LIVE"
threading.Thread(target=bot_loop,daemon=True).start()
if __name__=="__main__":
    app.run(host="0.0.0.0",port=int(os.environ.get("PORT",10000)))
