import os, time, requests, threading, random
from flask import Flask
from datetime import datetime

app = Flask(__name__)

TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

PAIRS = [("EUR/USD OTC","EUR","USD"),("GBP/USD OTC","GBP","USD"),("USD/JPY OTC","USD","JPY"),("AUD/USD OTC","AUD","USD"),("EUR/GBP OTC","EUR","GBP"),("EUR/JPY OTC","EUR","JPY"),("USD/CAD OTC","USD","CAD")]
store = {n: {"prezzi": [], "ultimo": 0} for n, _, _ in PAIRS}

def tg(m):
    try:
        if TOKEN and CHAT_ID:
            requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage", data={"chat_id": CHAT_ID, "text": m}, timeout=10)
    except: pass

def get_price_fx(frm,to):
    try:
        r = requests.get(f"https://api.frankfurter.app/latest?from={frm}&to={to}", timeout=8).json()
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
    time.sleep(5)
    tg("✅ V36.8.4 7 LAVORI PELO LIVE")
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
                sma50=sum(prezzi[-20:])/20
                max20=max(prezzi[-20:])
                min20=min(prezzi[-20:])
                std=(sum((x-sma50)**2 for x in prezzi[-20:])/20)**0.5
                bb_up=sma50+2*std
                bb_low=sma50-2*std

                if (max(prezzi[-5:])-min(prezzi[-5:]))/prezzi[-1] > 0.0020: continue
                if abs(ema9-ema21)/ema21<0.00010: continue
                if 45<rsi14<55: continue

                in_caduta = prezzi[-1] < prezzi[-3] < prezzi[-7]
                in_salita = prezzi[-1] > prezzi[-3] > prezzi[-7]
                vieta_buy = in_caduta and rsi14 < 48
                vieta_sell = in_salita and rsi14 > 52

                buy=0; sell=0; motivi=[]
                if ema9>ema21 and rsi14<50: buy+=1; motivi.append("L1")
                if ema9<ema21 and rsi14>50: sell+=1; motivi.append("L1")
                if prezzi[-1] < bb_low and rsi14<40: buy+=1; motivi.append("L2")
                if prezzi[-1] > bb_up and rsi14>60: sell+=1; motivi.append("L2")
                if prezzi[-1] >= max20*0.9995: buy+=1; motivi.append("L3")
                if prezzi[-1] <= min20*1.0005: sell+=1; motivi.append("L3")
                if abs(prezzi[-2]-sma50)/sma50<0.0005 and prezzi[-1]>sma50 and ema9>ema21: buy+=1; motivi.append("L4")
                if abs(prezzi[-2]-sma50)/sma50<0.0005 and prezzi[-1]<sma50 and ema9<ema21: sell+=1; motivi.append("L4")
                if rsi14<40: buy+=1; motivi.append("L5")
                if rsi14>60: sell+=1; motivi.append("L5")
                if prezzi[-2]<ema9 and prezzi[-1]>ema9: buy+=1; motivi.append("L6")
                if prezzi[-2]>ema9 and prezzi[-1]<ema9: sell+=1; motivi.append("L6")
                if prezzi[-1]>prezzi[-10] and rsi14<53: buy+=1; motivi.append("L7")
                if prezzi[-1]<prezzi[-10] and rsi14>47: sell+=1; motivi.append("L7")

                ora=datetime.now().strftime('%H:%M:%S')
                if buy>=2 and rsi14<=53 and not vieta_buy:
                    tg(f"🟢 {name} BUY TF 5M {ora} | {'+'.join(motivi)} | RSI {rsi14:.0f}")
                    s["ultimo"]=time.time(); last_global=time.time(); break
                elif sell>=2 and rsi14>=47 and not vieta_sell:
                    tg(f"🔴 {name} SELL TF 5M {ora} | {'+'.join(motivi)} | RSI {rsi14:.0f}")
                    s["ultimo"]=time.time(); last_global=time.time(); break
            time.sleep(20)
        except Exception as e:
            print(f"ERR: {e}"); time.sleep(10)

@app.route("/")
def home(): return "V36.8.4 7 LAVORI PELO LIVE"
threading.Thread(target=bot_loop, daemon=True).start()

if __name__=="__main__":
    port = int(os.environ.get("PORT",10000))
    app.run(host="0.0.0.0", port=port)
