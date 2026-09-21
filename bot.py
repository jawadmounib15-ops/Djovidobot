import time, requests, ccxt
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

TELEGRAM_TOKEN = "8833997039:AAHBJ-sBRy2wIaMjiXv1Szk3azvj8aOSc7Y"
TELEGRAM_CHAT_ID = "6723819958"

PAIRS = ["GBP/USD", "EUR/USD", "USD/JPY"]
WIN, LOSS, ultimo_id, trades = 0,0,0,[]

exchange = ccxt.binance()

def ema(series, n):
    return series.ewm(span=n, adjust=False).mean()

def rsi(series, n=14):
    delta = series.diff()
    gain = (delta.where(delta>0,0)).rolling(n).mean()
    loss = (-delta.where(delta<0,0)).rolling(n).mean()
    rs = gain/loss
    return 100 - (100/(1+rs))

def send(text, buttons=None):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    data = {"chat_id": TELEGRAM_CHAT_ID, "text": text, "parse_mode": "Markdown"}
    if buttons:
        data["reply_markup"] = {"inline_keyboard": buttons}
    requests.post(url, json=data)

def nuovo_segnale(pair, direz):
    scadenza = datetime.now() + timedelta(minutes=16)
    trades.append({"pair": pair, "dir": direz, "scad": scadenza})
    send(f"🔔 *V64 {direz} {pair}*\nAperto {datetime.now().strftime('%H:%M')} -> check {scadenza.strftime('%H:%M')}")
    print(f"SEGNALE {direz} {pair}")

def start():
    global WIN, LOSS, ultimo_id
    print("🚀 V64 ATTIVO SENZA PANDAS_TA")
    send("🚀 *V64 MOLTO LARGO ATTIVO*")

    last_check = 0
    while True:
        if time.time() - last_check > 60:
            for pair in PAIRS:
                try:
                    symbol = pair.replace("/","")
                    bars = exchange.fetch_ohlcv(symbol, "5m", limit=100)
                    df = pd.DataFrame(bars, columns=["t","o","h","l","c","v"])
                    df["ema20"] = ema(df["c"],20)
                    df["ema50"] = ema(df["c"],50)
                    df["rsi"] = rsi(df["c"],14)
                    last = df.iloc[-1]
                    prev = df.iloc[-2]
                    if last["c"] > last["ema20"] > last["ema50"] and last["rsi"]>55 and prev["c"]<prev["ema20"]:
                        nuovo_segnale(pair,"BUY")
                    if last["c"] < last["ema20"] < last["ema50"] and last["rsi"]<45 and prev["c"]>prev["ema20"]:
                        nuovo_segnale(pair,"SELL")
                except Exception as e:
                    print(e)
            last_check = time.time()

        for t in trades[:]:
            if datetime.now() >= t["scad"]:
                btns = [[{"text":"✅ WIN","callback_data":f"WIN|{t['pair']}|{t['dir']}"},{"text":"❌ LOSS","callback_data":f"LOSS|{t['pair']}|{t['dir']}"}]]
                send(f"⏰ *Scaduto {t['dir']} {t['pair']}* - Com'è andato?", btns)
                trades.remove(t)

        try:
            r = requests.get(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getUpdates?offset={ultimo_id+1}").json()
            for u in r.get("result",[]):
                ultimo_id = u["update_id"]
                if "callback_query" in u:
                    esito,pair,direz = u["callback_query"]["data"].split("|")
                    if esito=="WIN": WIN+=1
                    else: LOSS+=1
                    wr = WIN/(WIN+LOSS)*100 if WIN+LOSS>0 else 0
                    send(f"{'✅' if esito=='WIN' else '❌'} *{esito} {direz} {pair}*\n\n📊 WIN: {WIN} | LOSS: {LOSS}\nWR: {wr:.1f}%")
        except: pass
        time.sleep(3)

start()
