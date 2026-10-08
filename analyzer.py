# Analyzer.py - PINBAR 3 MIN + TELEGRAM + SUONO + STORICO
import json
import os
import time
import pandas as pd
import requests
from datetime import datetime, timedelta

# --- TELEGRAM CONFIG ---
TOKEN = os.getenv("TELEGRAM_TOKEN", os.getenv("TOKEN", "")).strip()
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", os.getenv("CHAT_ID", "")).strip()

def send_telegram(msg):
    if not TOKEN or not CHAT_ID:
        print("Telegram non configurato")
        return
    try:
        url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
        requests.get(url, params={"chat_id": CHAT_ID, "text": msg}, timeout=5)
    except Exception as e:
        print(f"Errore Telegram: {e}")

# --- SUONO ---
try:
    import winsound
    def play_sound():
        try: winsound.Beep(900, 500)
        except: print("\a")
except:
    def play_sound(): print("\a [PINBAR]")

class PinBarAnalyzer:
    def __init__(self, storico_file="storico_segnali.json"):
        self.storico_file = storico_file
        self.storico = self.load_storico()
        print(f"Telegram: {'ON' if TOKEN and CHAT_ID else 'OFF'} - {len(self.storico)} storico")

    def load_storico(self):
        if os.path.exists(self.storico_file):
            try:
                with open(self.storico_file, 'r') as f:
                    return json.load(f)
            except: return []
        return []

    def save_storico(self):
        with open(self.storico_file, 'w') as f:
            json.dump(self.storico, f, indent=2)

    def fix_df(self, df):
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        df.columns = [c.lower() for c in df.columns]
        return df

    def is_pinbar(self, o, h, l, c):
        body = abs(c - o)
        upper = h - max(c, o)
        lower = min(c, o) - l
        total = h - l
        if total == 0 or total < 0.00001: return None, 0, 0
        if body == 0: body = total * 0.06
        if body > total * 0.60: return None, 0, 0

        tail_up = upper / body
        tail_down = lower / body

        if lower > body * 1.3 and upper < body * 1.2:
            if c > (l + total * 0.50):
                return "BUY", round((lower/total)*100, 1), round(tail_down, 1)

        if upper > body * 1.3 and lower < body * 1.2:
            if c < (l + total * 0.50):
                return "SELL", round((upper/total)*100, 1), round(tail_up, 1)

        return None, 0, 0

    def analyze(self, df, pair="EUR/USD"):
        df = self.fix_df(df)
        if len(df) < 50: return None

        # ANTI-LAG: candela -2
        last = df.iloc[-2]
        o = float(last['open']); h = float(last['high'])
        l = float(last['low']); c = float(last['close'])

        signal, score, tail = self.is_pinbar(o, h, l, c)
        if not signal or score < 58: return None

        try:
            delta = df['close'].diff()
            gain = delta.where(delta > 0, 0).rolling(14).mean()
            loss = -delta.where(delta < 0, 0).rolling(14).mean()
            rsi = 100 - (100 / (1 + gain/loss))
            rsi_val = float(rsi.iloc[-2])
            if signal == "BUY" and not (10 <= rsi_val <= 80): return None
            if signal == "SELL" and not (20 <= rsi_val <= 90): return None
        except:
            rsi_val = 50

        now = datetime.now()
        expiry = now + timedelta(minutes=3)

        segnale = {
            "pair": pair,
            "symbol": pair,
            "signal": signal,
            "score": score,
            "tail": f"{tail}",
            "rsi": int(rsi_val),
            "prezzo": c,
            "entry": f"{c:.5f}",
            "time": now.timestamp(),
            "timestamp": now.timestamp(),
            "time_str": now.strftime("%d/%m %H:%M:%S"),
            "entry_time": now.strftime("%H:%M:%S"),
            "expiry_time": expiry.strftime("%H:%M:%S"),
            "expiry_timestamp": expiry.timestamp(),
            "scadenza": "3 MIN",
            "status": "ATTIVO"
        }

        # evita doppioni 2 min
        if not any(s['pair'] == pair and abs(s['timestamp'] - segnale['timestamp']) < 120 for s in self.storico[-20:]):
            self.storico.append(segnale)
            self.save_storico()
            play_sound()
            
            # TELEGRAM
            msg = f"🎯 PINBAR {signal} {pair} ⏰3 MIN\nRSI {int(rsi_val)} coda {tail}x score {score}%\nPrezzo {c:.5f}\n{segnale['time_str']} -> {segnale['expiry_time']}"
            send_telegram(msg)
            
            print(f"PINBAR {signal} {pair} {score}% -> Telegram inviato")
            return segnale
        return None

    def check_scadenza(self):
        now_ts = datetime.now().timestamp()
        for s in self.storico:
            if s['status'] == "ATTIVO" and now_ts > s['expiry_timestamp']:
                s['status'] = "SCADUTO"
        self.save_storico()
        attivi = [s for s in self.storico if s['status'] == "ATTIVO" and now_ts - s['timestamp'] < 200]
        return attivi

    def get_pending(self): return self.check_scadenza()
    def get_history(self, limit=50): return self.storico[-limit:]
