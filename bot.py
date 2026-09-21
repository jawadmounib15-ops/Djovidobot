import time, requests, ccxt
import pandas as pd
from datetime import datetime, timedelta

# === INCOLLA I TUOI DATI VERI QUI ===
TELEGRAM_TOKEN = "8833997039:AAHBJ-sBRy2wIaMjiXv1Szk3azvj8aOSc7Y"
TELEGRAM_CHAT_ID = "6723819958"
# ====================================

PAIRS = ["EUR/USD", "GBP/USD", "USD/JPY", "AUD/USD", "EUR/GBP"]
WIN, LOSS, ultimo_id, trades = 0, 0, 0, []

exchange = ccxt.binance()

def send(text, buttons=None):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        data = {"chat_id": TELEGRAM_CHAT_ID, "text": text, "parse_mode": "Markdown"}
        if buttons:
            data["reply_markup"] = {"inline_keyboard": buttons}
        requests.post(url, json=data, timeout=10)
    except Exception as e:
        print(f"Errore send: {e}")

def nuovo_segnale(pair, direz):
    scadenza = datetime.now() + timedelta(minutes=16)
    trades.append({"pair": pair, "dir": direz, "scad": scadenza})
    send(f"🔔 *V64 LARGO {direz} {pair}*\n🕐 Aperto: {datetime.now().strftime('%H:%M')} -> Check: {scadenza.strftime('%H:%M')}\nEMA20 + RSI OK ✅")
    print(f"SEGNALE LARGO {direz} {pair}")

def start():
    global WIN, LOSS, ultimo_id
    print("🚀 V64 LARGO ATTIVO")
    send("🚀 *V64 LARGO ATTIVO*\nCerco segnali ogni 60 sec...")
    
    last_check = 0
    while True:
        # CERCA SEGNALI OGNI 60 SEC
        if time.time() - last_check > 60:
            for pair in PAIRS:
                try:
                    symbol = pair.replace("/", "")
                    bars = exchange.fetch_ohlcv(symbol, "5m", limit=50)
                    df = pd.DataFrame(bars, columns=["t","o","h","l","c","v"])
                    
                    # CALCOLO LARGO SEMPLICE
                    df["ema20"] = df["c"].ewm(span=20).mean()
                    delta = df["c"].diff()
                    gain = (delta.where(delta>0,0)).rolling(14).mean()
                    loss = (-delta.where(delta<0,0)).rolling(14).mean()
                    df["rsi"] = 100 - (100/(1+gain/loss))
                    
                    last = df.iloc[-1]
                    prev = df.iloc[-2]
                    
                    # LARGO VERO - NON STRETTO
                    if last["c"] > last["ema20"] and last["rsi"] > 50 and prev["c"] < prev["ema20"]:
                        nuovo_segnale(pair, "BUY")
                    
                    if last["c"] < last["ema20"] and last["rsi"] < 50 and prev["c"] > prev["ema20"]:
                        nuovo_segnale(pair, "SELL")
                        
                except Exception as e:
                    print(f"Errore {pair}: {e}")
            last_check = time.time()

        # CHECK SCADENZE WIN/LOSS
        for t in trades[:]:
            if datetime.now() >= t["scad"]:
                btns = [[{"text": "✅ WIN", "callback_data": f"WIN|{t['pair']}|{t['dir']}"}, {"text": "❌ LOSS", "callback_data": f"LOSS|{t['pair']}|{t['dir']}"}]]
                send(f"⏰ *Scaduto {t['dir']} {t['pair']}* - Com'è andata?", btns)
                trades.remove(t)

        # LEGGI WIN/LOSS DA TELEGRAM
        try:
            r = requests.get(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getUpdates?offset={ultimo_id+1}", timeout=10).json()
            for u in r.get("result", []):
                ultimo_id = u["update_id"]
                if "callback_query" in u:
                    esito, pair, direz = u["callback_query"]["data"].split("|")
                    if esito == "WIN": WIN += 1
                    else: LOSS += 1
                    wr = WIN/(WIN+LOSS)*100 if (WIN+LOSS)>0 else 0
                    send(f"{'✅' if esito=='WIN' else '❌'} *{esito} {direz} {pair}*\n\n📊 STATS: WIN {WIN} | LOSS {LOSS}\nWinrate: {wr:.1f}%")
        except: pass
        
        time.sleep(3)

start()
