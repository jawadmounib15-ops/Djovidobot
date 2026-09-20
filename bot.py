import os, time, requests, threading, random
from flask import Flask
from datetime import datetime

app = Flask(__name__)

TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

PAIRS = [
    ("EUR/USD OTC","EUR","USD"),
    ("GBP/USD OTC","GBP","USD"),
    ("USD/JPY OTC","USD","JPY"),
    ("AUD/USD OTC","AUD","USD"),
    ("EUR/GBP OTC","EUR","GBP"),
    ("EUR/JPY OTC","EUR","JPY"),
    ("USD/CAD OTC","USD","CAD")
]

store = {n: {"prezzi": [], "ultimo": 0} for n, _, _ in PAIRS}

def tg(m):
    try:
        requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage", data={"chat_id": CHAT_ID, "text": m}, timeout=10)
    except:
        pass

def get_price_fx(frm,to):
    try:
        r = requests.get(f"https://api.frankfurter.app/latest?from={frm}&to={to}", timeout=10).json()
        base = float(r["rates"][to])
        return base + random.uniform(-0.0008,0.0008)*base
    except:
        return None

def rsi(data):
    if len(data)<15:
        return 50
    g=0
    l=0
    for i in range(-14,0):
        d=data[i]-data[i-1]
        if d>0:
            g+=d
        else:
            l+=-d
    if g==0 and l==0:
        return 50
    if l==0:
        return 70
    if g==0:
        return 30
    rs=(g/14)/(l/14)
    return 100-(100/(1+rs))

def bot_loop():
    tg("✅ V36.8.4 PELO LIVE - alzato un pelo + 5 min")
    last_global = 0
    while True:
        try:
            if time.time() - last_global < 300:
                time.sleep(20)
                continue
            for name,frm,to in PAIRS:
                s=store[name]
                if time.time()-s["ultimo"]<180:
                    continue
                p=get_price_fx(frm,to)
                if not p:
                    continue
                s["prezzi"].append(p)
                if len(s["prezzi"])>60:
                    s["prezzi"].pop(0)
                if len(s["prezzi"])<25:
                    continue
                prezzi=s["prezzi"]
                ema9=sum(prezzi[-9:])/9
                ema21=sum(prezzi[-21:])/21
                rsi14=rsi(prezzi)

                if (max(prezzi[-5:])-min(prezzi[-5:]))/prezzi[-1] > 0.0020:
                    continue
                if abs(ema9-ema21)/ema21<0
