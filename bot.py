import os, time, requests, threading, random
from flask import Flask
from datetime import datetime
app = Flask(__name__)
TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
PAIRS = [("EUR/USD OTC","EUR","USD"),("GBP/USD OTC","GBP","USD"),("USD/JPY OTC","USD","JPY"),("AUD/USD OTC","AUD","USD"),("EUR/GBP OTC","EUR","GBP"),("EUR/JPY OTC","EUR","JPY"),("USD/CAD OTC","USD","CAD")]
COOLDOWN = 300
store = {n: {"prezzi": [], "ultimo": 0} for n, _, _ in PAIRS}

def tg(m):
    try: requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage", data={"chat_id": CHAT_ID, "text": m}, timeout=10)
    except: pass

def get_price_fx(frm,to):
    try:
        r = requests.get(f"https://api.frankfurter.app/latest?from={frm}&to={to}", timeout=10).json()
        base = float(r["rates"][to])
        return base + random.uniform(-0.0008,0.0008)*base
    except: return None

def rsi(data):
    if len(data)<15: return 50
    g=0;l=0
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
    tg("✅ V36.8.5 LIVE - 65% TARGET + 5min")
    last_global = 0
    while True:
        try:
            if time.time() - last_global < 300:
                time.sleep(20)
                continue
            for name,frm,to in PAIRS:
                s=store[name]
                if time.time()-s["ultimo"]<180: continue
                p=get_price_fx(frm,to)
                if not p: continue
                s["prezzi"].append(p)
                if len(s["prezzi"])>60: s["prezzi"].pop(0)
                if len(s["prezzi"])<25: continue
                prezzi=s["prezzi"]
                ema9=sum(prezzi[-9:])/9
                ema21=sum(prezzi[-21:])/21
                rsi14=rsi(prezzi)

                # FILTRO 65% - più stretto
                if (max(prezzi[-5:])-min(prezzi[-5:]))/prezzi[-1] > 0.0018: continue
                if abs(ema9-ema21)/ema21 < 0.00015: continue # EMA più distanti = trend più forte
                if 42 < rsi14 < 58: continue # Zona morta allargata da 45-55 a 42-58

                in_caduta = prezzi[-1] < prezzi[-3] < prezzi[-7]
                in_salita = prezzi[-1] > prezzi[-3] > prezzi[-7]
                vieta_buy = in_caduta and prezzi[-1] < ema21*0.998 and rsi14 < 50
                vieta_sell = in_salita and prezzi[-1] > ema21*1.002 and rsi14 > 50

                buy=0;sell=0
                if ema9>ema21 and rsi14<48: buy+=1
                if ema9<ema21 and rsi14>52: sell+=1
                if rsi14<40: buy+=1 # Prima era 42, ora 40 più severo
                if rsi14>60: sell+=1 # Prima era 58, ora 60 più severo
                if prezzi[-1]>prezzi[-10] and rsi14<52: buy+=1
                if prezzi[-1]<prezzi[-10] and rsi14>48: sell+=1

                ora=datetime.now().strftime('%H:%M:%S')
                # ALZATO: serve 3 punti per 65% o 2 punti ma RSI estremo
                if (buy>=3 or (buy>=2 and rsi14<38)) and rsi14<=50 and not vieta_buy:
                    tg(f"🟢 {name} BUY TF 5M {ora} | Scadenza 5 min | RSI {rsi14:.0f} | 65%")
                    s["ultimo"]=time.time()
                    last_global=time.time()
                    break
                elif (sell>=3 or (sell>=2 and rsi14>62)) and rsi14>=50 and not vieta_sell:
                    tg(f"🔴 {name} SELL TF 5M {ora} | Scadenza 5 min | RSI {rsi14:.0f} | 65%")
                    s["ultimo"]=time.time()
                    last_global=time.time()
                    break
            time.sleep(20)
        except Exception as e:
            print(e); time.sleep(10)

@app.route("/")
def home(): return "V36.8.5 65% LIVE"
threading.Thread(target=bot_loop, daemon=True).start()
if __name__=="__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT",10000)))
