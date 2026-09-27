# bot.py - OTC + REALI - 3MIN + 30MIN COMBO
import os, time, random, requests, yfinance as yf, threading, pandas as pd
from datetime import datetime, timedelta
from flask import Flask
app = Flask(__name__)
@app.route('/')
def home(): return "OTC+REALI 3MIN+30MIN ONLINE"

TOKEN = os.environ.get("TELEGRAM_TOKEN")
CHAT = os.environ.get("TELEGRAM_CHAT_ID")

# STESSI SIMBOLI, 2 ETICHETTE
BASE = ["EURUSD=X","GBPUSD=X","USDJPY=X","AUDUSD=X","EURJPY=X","GBPJPY=X","USDCHF=X","EURGBP=X","AUDJPY=X","CHFJPY=X","EURCAD=X","EURNZD=X"]
LABELS_REALI = ["EUR/USD","GBP/USD","USD/JPY","AUD/USD","EUR/JPY","GBP/JPY","USD/CHF","EUR/GBP","AUD/JPY","CHF/JPY","EUR/CAD","EUR/NZD"]
LABELS_OTC = ["EUR/USD-OTC","GBP/USD-OTC","USD/JPY-OTC","AUD/USD-OTC","EUR/JPY-OTC","GBP/JPY-OTC","USD/CHF-OTC","EUR/GBP-OTC","AUD/JPY-OTC","CHF/JPY-OTC","EUR/CAD-OTC","EUR/NZD-OTC"]

# CREO LISTA DOPPIA: REALI + OTC
ALL_PAIRS = []
for b, r, o in zip(BASE, LABELS_REALI, LABELS_OTC):
    ALL_PAIRS.append((b, r)) # REALI
    ALL_PAIRS.append((b, o)) # OTC

LAST3={}; LAST30={}; CHECK=0; LAST_SIGNAL=0; LAST_AVISO=0

def send(m):
    try: requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage", json={"chat_id":CHAT,"text":m,"parse_mode":"Markdown"},timeout=10)
    except: pass

def get_df(yahoo, tf_list):
    for interval, period in tf_list:
        try:
            df = yf.download(yahoo, period=period, interval=interval, progress=False)
            if len(df)>=80:
                if isinstance(df.columns,pd.MultiIndex): df.columns=df.columns.get_level_values(0)
                return df, interval
        except: pass
    return None, None

def bot_loop():
    global CHECK, LAST_SIGNAL, LAST_AVISO
    send("💎 *OTC+REALI COMBO ONLINE*\n⚡ 3MIN PELO + 🎯 30MIN PERFETTO\n24 coppie REALI+OTC")
    while True:
        try:
            now=datetime.now(); weekday=now.weekday() # 0=lunedi 5=sabato
            is_weekend = weekday >= 5

            if time.time()-CHECK >= 15:
                CHECK=time.time()

                if time.time()-LAST_SIGNAL>=300 and time.time()-LAST_AVISO>=300:
                    tipo = "SOLO OTC (weekend)" if is_weekend else "REALI+OTC"
                    send(f"🔍 {tipo} - Nessun segnale 3m/30m da 5 min - attivo {now.strftime('%H:%M:%S')}")
                    LAST_AVISO=time.time()

                if time.time()-LAST_SIGNAL < 90: continue

                random.shuffle(ALL_PAIRS)

                for yahoo,label in ALL_PAIRS:
                    # WEEKEND: SALTA REALI
                    if is_weekend and "-OTC" not in label: continue
                    # FERIALE: TUTTI
                    key = f"{yahoo}_{label}"

                    # ===== 3 MIN =====
                    if key not in LAST3 or time.time()-LAST3[key]>=240:
                        df, tf = get_df(yahoo, [("1m","2d"), ("5m","5d")])
                        if df is not None:
                            try:
                                df['EMA9']=df['Close'].ewm(span=9).mean()
                                df['EMA21']=df['Close'].ewm(span=21).mean()
                                df['EMA50']=df['Close'].ewm(span=50).mean()
                                delta=df['Close'].diff()
                                gain=delta.where(delta>0,0).ewm(alpha=1/14).mean()
                                loss=-delta.where(delta<0,0).ewm(alpha=1/14).mean()
                                df['RSI']=100-(100/(1+gain/loss))
                                last=df.iloc[-2]
                                c=float(last['Close']); r=float(last['RSI']); ema9=float(last['EMA9']); ema21=float(last['EMA21']); ema50=float(last['EMA50'])
                                if abs(ema9-ema21)/c >= 0.00012:
                                    if not (c>ema50 and ema9<ema21) and not (c<ema50 and ema9>ema21):
                                        cur=now.strftime("%H:%M:%S"); exp3=(now+timedelta(minutes=3)).strftime("%H:%M:%S")
                                        sig=None
                                        if ema9>ema21 and c>ema21 and 48<=r<=68:
                                            sig=f"⚡🟢 *BUY {label} 3MIN*\nRSI {r:.0f} [{tf}]\n⏰ {cur}→{exp3} {c:.5f} 👉 BUY 3M"
                                        elif ema9<ema21 and c<ema21 and 32<=r<=52:
                                            sig=f"⚡🔴 *SELL {label} 3MIN*\nRSI {r:.0f} [{tf}]\n⏰ {cur}→{exp3} {c:.5f} 👉 SELL 3M"
                                        if sig:
                                            send(sig); LAST3[key]=time.time(); LAST_SIGNAL=time.time(); LAST_AVISO=time.time(); break
                            except: pass

                    # ===== 30 MIN =====
                    if key not in LAST30 or time.time()-LAST30[key]>=900:
                        df, tf = get_df(yahoo, [("15m","5d"), ("5m","5d")])
                        if df is not None:
                            try:
                                df['EMA20']=df['Close'].ewm(span=20).mean()
                                df['EMA50']=df['Close'].ewm(span=50).mean()
                                df['EMA100']=df['Close'].ewm(span=100).mean()
                                df['EMA9']=df['Close'].ewm(span=9).mean()
                                delta=df['Close'].diff()
                                gain=delta.where(delta>0,0).ewm(alpha=1/14).mean()
                                loss=-delta.where(delta<0,0).ewm(alpha=1/14).mean()
                                df['RSI']=100-(100/(1+gain/loss))
                                df['MACD']=df['Close'].ewm(span=12).mean()-df['Close'].ewm(span=26).mean()
                                df['SIG']=df['MACD'].ewm(span=9).mean()
                                df['ATR']=(df['High']-df['Low']).ewm(span=14).mean()
                                last=df.iloc[-2]
                                c=float(last['Close']); r=float(last['RSI']); ema20=float(last['EMA20']); ema50=float(last['EMA50']); ema100=float(last['EMA100']); ema9=float(last['EMA9']); macd=float(last['MACD']); sig_m=float(last['SIG']); atr=float(last['ATR'])
                                if atr/c >= 0.0004 and abs(ema20-ema50)/c >= 0.0003:
                                    up = ema20>ema50 and ema50>ema100 and c>ema20
                                    down = ema20<ema50 and ema50<ema100 and c<ema20
                                    cur=now.strftime("%H:%M:%S"); exp30=(now+timedelta(minutes=30)).strftime("%H:%M:%S")
                                    s=None
                                    if up and ema9>ema20 and 52<=r<=69 and macd>sig_m:
                                        s=f"🎯🟢 *BUY {label} 30MIN*\n20>50>100 RSI {r:.0f} [{tf}]\n⏰ {cur}→{exp30} {c:.5f} 👉 BUY 30M"
                                    elif down and ema9<ema20 and 31<=r<=48 and macd<sig_m:
                                        s=f"🎯🔴 *SELL {label} 30MIN*\n20<50<100 RSI {r:.0f} [{tf}]\n⏰ {cur}→{exp30} {c:.5f} 👉 SELL 30M"
                                    if s:
                                        send(s); LAST30[key]=time.time(); LAST_SIGNAL=time.time(); LAST_AVISO=time.time(); break
                            except: pass
        except: pass
        time.sleep(1)

threading.Thread(target=bot_loop,daemon=True).start()
if __name__=="__main__": app.run(host="0.0.0.0",port=int(os.environ.get("PORT",10000)))
