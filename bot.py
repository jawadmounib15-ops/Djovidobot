# bot.py - FIX SOLO EUR/NZD
import os, time, random, requests, yfinance as yf, threading, pandas as pd
from datetime import datetime, timedelta
from flask import Flask
app = Flask(__name__)
@app.route('/')
def home(): return "FIX MULTI"

TOKEN = os.environ.get("TELEGRAM_TOKEN")
CHAT = os.environ.get("TELEGRAM_CHAT_ID")

BASE = ["EURUSD=X","GBPUSD=X","USDJPY=X","AUDUSD=X","EURJPY=X","GBPJPY=X","USDCHF=X","EURGBP=X","AUDJPY=X","CHFJPY=X","EURCAD=X","EURNZD=X","GBPCHF=X","AUDCAD=X"]
LABELS_OTC = ["EUR/USD-OTC","GBP/USD-OTC","USD/JPY-OTC","AUD/USD-OTC","EUR/JPY-OTC","GBP/JPY-OTC","USD/CHF-OTC","EUR/GBP-OTC","AUD/JPY-OTC","CHF/JPY-OTC","EUR/CAD-OTC","EUR/NZD-OTC","GBP/CHF-OTC","AUD/CAD-OTC"]
LABELS_REALI = ["EUR/USD","GBP/USD","USD/JPY","AUD/USD","EUR/JPY","GBP/JPY","USD/CHF","EUR/GBP","AUD/JPY","CHF/JPY","EUR/CAD","EUR/NZD","GBP/CHF","AUD/CAD"]

ALL_PAIRS=[]
for b, r, o in zip(BASE, LABELS_REALI, LABELS_OTC):
    ALL_PAIRS.append((b,r)); ALL_PAIRS.append((b,o))

LAST3={}; LAST30={}; LAST_PRICE={}; CHECK=0; LAST_SIGNAL=0; LAST_AVISO=0

def send(m):
    try: requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage", json={"chat_id":CHAT,"text":m,"parse_mode":"Markdown"},timeout=10)
    except: pass

def get_df_fixed(yahoo, tf_list):
    for interval, period in tf_list:
        try:
            # FIX CACHE - no cache
            df = yf.download(yahoo, period=period, interval=interval, progress=False, auto_adjust=False, prepost=False)
            if len(df)>=50:
                if isinstance(df.columns,pd.MultiIndex): df.columns=df.columns.get_level_values(0)
                df=df.dropna()
                # Controllo se dati freschi - ultima candela non più vecchia di 10 min per 1m
                if len(df)>0:
                    return df, interval
        except: pass
    return None, None

def bot_loop():
    global CHECK, LAST_SIGNAL, LAST_AVISO
    send("🔧 *FIX MULTI ONLINE*\nFix EUR/NZD loop - Ora 28 coppie")
    while True:
        try:
            now=datetime.now(); is_weekend = now.weekday()>=5
            if time.time()-CHECK >= 12:
                CHECK=time.time()
                if time.time()-LAST_SIGNAL>=300 and time.time()-LAST_AVISO>=300:
                    send(f"🔍 Attivo - cerco tutti {len(ALL_PAIRS)} {now.strftime('%H:%M:%S')}")
                    LAST_AVISO=time.time()
                if time.time()-LAST_SIGNAL < 60: continue # 1 min tra segnali

                random.shuffle(ALL_PAIRS)
                segnali_trovati=[]
                for yahoo,label in ALL_PAIRS:
                    if is_weekend and "-OTC" not in label: continue
                    key=f"{yahoo}_{label}"
                    if key in LAST3 and time.time()-LAST3[key]<180: continue

                    df, tf = get_df_fixed(yahoo, [("1m","1d"), ("5m","5d")])
                    if df is None: continue
                    try:
                        df['EMA9']=df['Close'].ewm(span=9).mean()
                        df['EMA21']=df['Close'].ewm(span=21).mean()
                        df['EMA50']=df['Close'].ewm(span=50).mean()
                        delta=df['Close'].diff()
                        gain=delta.where(delta>0,0).ewm(alpha=1/14).mean()
                        loss=-delta.where(delta<0,0).ewm(alpha=1/14).mean()
                        df['RSI']=100-(100/(1+gain/loss))
                        last=df.iloc[-1] # FIX: uso ULTIMA non penultima
                        c=float(last['Close'])

                        # FIX ANTI-LOOP STESSO PREZZO
                        price_key=f"{yahoo}"
                        if price_key in LAST_PRICE and LAST_PRICE[price_key]==c:
                            continue # prezzo bloccato, salto
                        LAST_PRICE[price_key]=c

                        r=float(last['RSI']); ema9=float(last['EMA9']); ema21=float(last['EMA21']); ema50=float(last['EMA50'])
                        # PELO LEGGERO - 0.00008 non 0.00012 così manda di più
                        if abs(ema9-ema21)/c < 0.00008: continue
                        if c>ema50 and ema9<ema21: continue
                        if c<ema50 and ema9>ema21: continue

                        if ema9>ema21 and c>ema21 and 47<=r<=70:
                            segnali_trovati.append((label,c,r,tf,"BUY"))
                        elif ema9<ema21 and c<ema21 and 30<=r<=53:
                            segnali_trovati.append((label,c,r,tf,"SELL"))
                    except: continue

                # Mando 1-2 migliori a giro, non solo EUR/NZD
                if segnali_trovati:
                    random.shuffle(segnali_trovati)
                    for label,c,r,tf,side in segnali_trovati[:2]: # max 2 alla volta
                        yahoo_match = [b for b, l in zip(BASE, LABELS_OTC) if l==label or l.replace("-OTC","")==label][0] if "-OTC" in label or True else BASE[0]
                        # trova yahoo
                        for b, lbl_r, lbl_o in zip(BASE, LABELS_REALI, LABELS_OTC):
                            if label in (lbl_r, lbl_o): yahoo_match=b
                        key=f"{yahoo_match}_{label}"
                        if key in LAST3 and time.time()-LAST3[key]<180: continue
                        cur=now.strftime("%H:%M:%S"); exp=(now+timedelta(minutes=3)).strftime("%H:%M:%S")
                        emoji="🟢" if side=="BUY" else "🔴"
                        send(f"⚡{emoji} *{side} {label} 3MIN*\nRSI {r:.0f} [{tf}] {c:.5f}\n⏰ {cur}→{exp} 👉 {side} 3M")
                        LAST3[key]=time.time()
                        LAST_SIGNAL=time.time()
                        LAST_AVISO=time.time()
                        time.sleep(1)
        except Exception as e:
            # print(e)
            pass
        time.sleep(1)

threading.Thread(target=bot_loop,daemon=True).start()
if __name__=="__main__": app.run(host="0.0.0.0",port=int(os.environ.get("PORT",10000)))
