import time, requests, ccxt
import pandas as pd
import pandas_ta as ta
from datetime import datetime, timedelta

# === INCOLLA QUI I TUOI DATI ===
TELEGRAM_TOKEN = "TELEGRAM_TOKEN"
TELEGRAM_CHAT_ID = "TELEGRAM_CHAT_ID"
# ===============================

PAIRS = ["GBP/USD", "EUR/USD", "USD/JPY", "AUD/USD"]
TIMEFRAME = "5m"
WIN, LOSS, ultimo_id, trades = 0, 0, 0, []

exchange = ccxt.binance()

def send(text, buttons=None):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    data = {"chat_id": TELEGRAM_CHAT_ID, "text": text, "parse_mode": "Markdown"}
    if buttons:
        data["reply_markup"] = {"inline_keyboard": buttons}
    try:
        requests.post(url, json=data, timeout=10)
    except: pass

def check_segnali():
    for pair in PAIRS:
        try:
            symbol = pair.replace("/", "")
            bars = exchange.fetch_ohlcv(f"{symbol}", TIMEFRAME, limit=100)
            df = pd.DataFrame(bars, columns=["time","open","high","low","close","vol"])
            
            # MOLTO LARGO LOGIC V64
            df["ema20"] = ta.ema(df["close"], 20)
            df["ema50"] = ta.ema(df["close"], 50)
            df["rsi"] = ta.rsi(df["close"], 14)
            df["vol_sma"] = ta.sma(df["vol"], 20)
            
            last = df.iloc[-1]
            prev = df.iloc[-2]
            
            # CONDIZIONE LARGO
            long_cond = last["close"] > last["ema20"] > last["ema50"] and last["rsi"] > 55 and last["vol"] > last["vol_sma"]
            short_cond = last["close"] < last["ema20"] < last["ema50"] and last["rsi"] < 45 and last["vol"] > last["vol_sma"]
            
            if long_cond and prev["close"] < prev["ema20"]:
                nuovo_segnale(pair, "BUY")
            elif short_cond and prev["close"] > prev["ema20"]:
                nuovo_segnale(pair, "SELL")
                
        except Exception as e:
            print(f"Errore {pair}: {e}")

def nuovo_segnale(pair, direz):
    scadenza = datetime.now() + timedelta(minutes=16)
    trades.append({"pair": pair, "dir": direz, "scad": scadenza})
    send(f"🔔 *V64 SEGNALE {direz} {pair}*\nAperto {datetime.now().strftime('%H:%M')} -> check {scadenza.strftime('%H:%M')}\nRSI + EMA + VOLUME OK ✅")
    print(f"SEGNALE {direz} {pair}")

def start():
    global WIN, LOSS, ultimo_id
    print("🚀 V64 MOLTO LARGO COMPLETO ATTIVO")
    send("🚀 *V64 MOLTO LARGO COMPLETO ATTIVO*\nCerco segnali ogni 1 min...")
    
    last_check = 0
    while True:
        # 1. Cerca segnali ogni 60 sec
        if time.time() - last_check > 60:
            check_segnali()
            last_check = time.time()
        
        # 2. Controlla scadenze
        for t in trades[:]:
            if datetime.now() >= t["scad"]:
                btns = [[{"text": "✅ WIN", "callback_data": f"WIN|{t['pair']}|{t['dir']}"}, {"text": "❌ LOSS", "callback_data": f"LOSS|{t['pair']}|{t['dir']}"}]]
                send(f"⏰ *Scaduto {t['dir']} {t['pair']}* - Com'è andato?", btns)
                trades.remove(t)
        
        # 3. Leggi click
        try:
            r = requests.get(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getUpdates?offset={ultimo_id+1}", timeout=10).json()
            for u in r.get("result", []):
                ultimo_id = u["update_id"]
                if "callback_query" in u:
                    d = u["callback_query"]["data"]
                    esito, pair, direz = d.split("|")
                    if esito == "WIN": WIN += 1
                    else: LOSS += 1
                    wr = WIN/(WIN+LOSS)*100 if (WIN+LOSS)>0 else 0
                    send(f"{'✅' if esito=='WIN' else '❌'} *{esito} {direz} {pair}*\n\n📊 WIN: {WIN} | LOSS: {LOSS}\nWinrate: {wr:.1f}%")
        except: pass
        
        time.sleep(3)

start()
