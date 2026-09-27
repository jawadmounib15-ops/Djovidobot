# bot.py - V-OTC 3MIN + AVVISO 5MIN
import os, time, random, requests, yfinance as yf, threading, pandas as pd
from datetime import datetime, timedelta
from flask import Flask
app = Flask(__name__)
@app.route('/')
def home(): return "V-OTC 3MIN + AVVISO 5MIN"

TOKEN = os.environ.get("TELEGRAM_TOKEN")
CHAT = os.environ.get("TELEGRAM_CHAT_ID")

SYMBOLS = ["EURUSD=X","GBPUSD=X","USDJPY=X","AUDUSD=X","EURJPY=X","GBPJPY=X","USDCHF=X","EURGBP=X","AUDJPY=X","CHFJPY=X","EURCAD=X","EURNZD=X"]
PAIRS_OTC = ["EUR/USD-OTC","GBP/USD-OTC","USD/JPY-OTC","AUD/USD-OTC","EUR/JPY-OTC","GBP/JPY-OTC","USD/CHF-OTC","EUR/GBP-OTC","AUD/JPY-OTC","CHF/JPY-OTC","EUR/CAD-OTC","EUR/NZD-OTC"]

LAST={}; CHECK=0; LAST_SIGNAL=0; LAST_AVISO=0

def send(m):
    try: requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage", json={"chat_id":CHAT,"text":m,"parse_mode":"Markdown"},timeout=10)
    except: pass

def get_df_safe(yahoo):
    for interval, period in [("1m","2d"), ("5m","5d"), ("15m","10d")]:
        try:
            df = yf.download(yahoo, period=period, interval=interval, progress=False)
            if len(df) >= 50:
                if isinstance(df.columns, pd.MultiIndex):
                    df.columns = df.columns.get_level_values(0)
                return df, interval
        except: pass
    return None, None

def bot_loop():
    global CHECK, LAST_SIGNAL, LAST_AVISO
    send("🔔 *V-OTC 3MIN + AVVISO ONLINE*\nMando avviso ogni 5min se non trovo\nScadenza 3 MIN")
    while True:
        try:
            now=datetime.now()
            if time.time()-CHECK >= 10:
                CHECK=time.time()
                if time.time() - LAST_SIGNAL < 120:
                    # CONTROLLA SE DEVE MANDARE AVVISO
                    if time.time() - LAST_AVISO >= 300: # 5 min
                        minuti = int((time.time() - LAST_SIGNAL)/60)
                        send(f"🔍 *Nessun segnale da {minuti} min*\nBot attivo, cerco... {datetime.now().strftime('%H:%M:%S')}\nMercato calmo, nessun setup 9/21")
                        LAST_AVISO = time.time()
                    continue

                combined = list(zip(SYMBOLS, PAIRS_OTC))
                random.shuffle(combined)
                trovato = False

                for yahoo,label in combined:
                    if yahoo in LAST and time.time()-LAST[yahoo]<180: continue
                    df, used_interval = get_df_safe(yahoo)
                    if df is None: continue
                    try:
                        df['EMA9']=df['Close'].ewm(span=9).mean()
                        df['EMA21']=df['Close'].ewm(span=21).mean()
                        df['EMA50']=df['Close'].ewm(span=50).mean()
                        delta=df['Close'].diff()
                        gain=delta.where(delta>0,0).ewm(alpha=1/14).mean()
                        loss=-delta.where(delta<0,0).ewm(alpha=1/14).mean()
                        rs=gain/loss
                        df['RSI']=100-(100/(1+rs))

                        last=df.iloc[-2]
                        c=float(last['Close']); r=float(last['RSI'])
                        ema9=float(last['EMA9']); ema21=float(last['EMA21'])

                        if abs(ema9-ema21)/c < 0.00005: continue

                        cur=now.strftime("%H:%M:%S")
                        exp3=(now+timedelta(minutes=3)).strftime("%H:%M:%S")

                        signal=None
                        if ema9>ema21 and c>ema21 and 40<r<72:
                            signal=f"🟢 *BUY {label} 3MIN*\nEMA9>21 RSI {r:.0f} [{used_interval}]\n⏰ {cur}→{exp3} {c:.5f} 👉 *BUY*"
                        elif ema9<ema21 and c<ema21 and 28<r<60:
                            signal=f"🔴 *SELL {label} 3MIN*\nEMA9<21 RSI {r:.0f} [{used_interval}]\n⏰ {cur}→{exp3} {c:.5f} 👉 *SELL*"

                        if signal:
                            send(signal)
                            LAST[yahoo]=time.time()
                            LAST_SIGNAL=time.time()
                            LAST_AVISO=time.time()
                            trovato=True
                            break
                    except: continue

                # SE NON HA TROVATO NIENTE E SONO PASSATI 5 MIN
                if not trovato and time.time() - LAST_AVISO >= 300:
                    minuti = int((time.time() - LAST_SIGNAL)/60) if LAST_SIGNAL>0 else 0
                    send(f"🔍 *Nessun segnale da {minuti} min*\nSto scansionando 12 coppie OTC...\nNessun setup valido ora - {now.strftime('%H:%M:%S')}")
                    LAST_AVISO = time.time()

        except Exception as e:
            print(f"Loop: {e}")
        time.sleep(1)

threading.Thread(target=bot_loop,daemon=True).start()

if __name__=="__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT",10000)))
