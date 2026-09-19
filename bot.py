# BOT V22 FINALE - SEGUE REGOLE FOTO - H1+M5+M1 + SMA50 + RSI + BB
import yfinance as yf, pandas as pd, pandas_ta as ta, requests, time, os
from flask import Flask
from threading import Thread
app = Flask(__name__)

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
PAIRS = {"EURUSD=X":"EUR/USD","GBPUSD=X":"GBP/USD","USDJPY=X":"USD/JPY","EURJPY=X":"EUR/JPY","GBPJPY=X":"GBP/JPY"}

def send(msg):
    try: requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage", data={"chat_id":CHAT_ID,"text":msg,"parse_mode":"Markdown"}, timeout=10)
    except: pass

def get_data(s,i,p):
    try:
        df=yf.download(s,period=p,interval=i,progress=False,auto_adjust=False)
        if df.empty: return pd.DataFrame()
        if isinstance(df.columns,pd.MultiIndex): df.columns=df.columns.get_level_values(0)
        return df
    except: return pd.DataFrame()

def pinbar(df):
    if len(df)<5: return None
    c=df.iloc[-1]; pr=df.iloc[-2]
    body=abs(float(c['Close'])-float(c['Open'])); rng=float(c['High'])-float(c['Low'])
    if rng==0: return None
    up=float(c['High'])-max(float(c['Open']),float(c['Close'])); lo=min(float(c['Open']),float(c['Close']))-float(c['Low'])
    if lo>body*2 and up<body*0.6: return "PINBAR_BUY"
    if up>body*2 and lo<body*0.6: return "PINBAR_SELL"
    if float(c['Close'])>float(c['Open']) and float(pr['Close'])<float(pr['Open']) and body>abs(float(pr['Close'])-float(pr['Open']))*1.2: return "ENGULFING_BUY"
    if float(c['Close'])<float(c['Open']) and float(pr['Close'])>float(pr['Open']) and body>abs(float(pr['Close'])-float(pr['Open']))*1.2: return "ENGULFING_SELL"
    return None

def check(s,name):
    # REGOLA FOTO: Trend H1 con SMA50
    df_h1=get_data(s,"60m","10d"); df_m5=get_data(s,"5m","5d"); df_m1=get_data(s,"1m","2d")
    if len(df_h1)<60 or len(df_m5)<60 or len(df_m1)<30: return None

    # SMA50 per capire se prezzo sopra/sotto - come da tua foto
    sma50_h1=float(ta.sma(df_h1['Close'],50).iloc[-1]); close_h1=float(df_h1['Close'].iloc[-1])
    ema20_m5=float(ta.ema(df_m5['Close'],20).iloc[-1]); ema50_m5=float(ta.ema(df_m5['Close'],50).iloc[-1])
    rsi_m1=float(ta.rsi(df_m1['Close'],14).iloc[-1]); rsi_m5=float(ta.rsi(df_m5['Close'],14).iloc[-1])

    # Bollinger per rimbalzo bordo - come da foto
    bb=ta.bbands(df_m1['Close'],20,2); lower=float(bb.iloc[-1,0]); upper=float(bb.iloc[-1,2]); close_m1=float(df_m1['Close'].iloc[-1])

    # CAPISCE SE STA SCENDENDO DA 1H+ - COME TUA FOTO PRECEDENTE
    ultime=df_h1['Close'].iloc[-8:].tolist()
    down_count=sum(1 for i in range(1,8) if ultime[i]<ultime[i-1])
    up_count=7-down_count
    sta_scendendo_forte=down_count>=6
    sta_salendo_forte=up_count>=6

    trend_h1_up=close_h1 > sma50_h1
    trend_m5_up=ema20_m5 > ema50_m5

    # EVITA CONTRO-TREND DURANTE SPINTE FORTI - REGOLA FOTO
    if trend_h1_up!= trend_m5_up: return None
    if sta_scendendo_forte and trend_h1_up: return None
    if sta_salendo_forte and not trend_h1_up: return None

    pattern=pinbar(df_m1)
    if pattern is None: return None

    # CONFERMA CON RSI + BOLLINGER + ENGULFING - REGOLA FOTO
    conferma_rsi = (rsi_m1<30 or rsi_m1>70 or abs(rsi_m1-50)>10)
    conferma_bb = (close_m1 <= lower*1.001 or close_m1 >= upper*0.999)

    if not (conferma_rsi or conferma_bb): return None

    # SCADENZA COME DA FOTO: 5 MIN BASE SICURA, MAI SOTTO 3 MIN
    if abs(rsi_m1-50)>25 and conferma_bb:
        scadenza="3 MINUTI"
    else:
        scadenza="5 MINUTI" # più sicuro, 1 candela M5

    if trend_h1_up and trend_m5_up and "BUY" in pattern and rsi_m1<55:
        if sta_scendendo_forte: return None # non comprare se scende da 1h come tua foto
        return f"🟢 BUY {name}\n📊 H1 SOPRA SMA50 + M5 UP | Trend lungo: {'UP' if sta_salendo_forte else 'ok'}\n📈 RSI M1:{rsi_m1:.0f} M5:{rsi_m5:.0f} BB:{'RIMBALZO' if conferma_bb else ''} Pattern:{pattern}\n👉 PO: 1 MIN | BUY | ⏱️ {scadenza}"

    if not trend_h1_up and not trend_m5_up and "SELL" in pattern and rsi_m1>45:
        if sta_salendo_forte: return None
        return f"🔴 SELL {name}\n📊 H1 SOTTO SMA50 + M5 DOWN | Trend lungo: {'DOWN da 1h+ come foto' if sta_scendendo_forte else 'ok'} ({down_count}/7 rosse)\n📈 RSI M1:{rsi_m1:.0f} M5:{rsi_m5:.0f} BB:{'RIMBALZO' if conferma_bb else ''} Pattern:{pattern}\n👉 PO: 1 MIN | SELL | ⏱️ {scadenza}"
    return None

def loop():
    send("✅ V22 FINALE PARTITO - Legge trend 1h+ come tua foto | SMA50 + RSI + BB + Engulfing | Scadenza 5MIN sicura | Libero")
    while True:
        try:
            for c,n in PAIRS.items():
                s=check(c,n)
                if s: send(s); time.sleep(20)
            time.sleep(90)
        except: time.sleep(60)

@app.route('/')
def home(): return "V22 attivo"
Thread(target=loop,daemon=True).start()
if __name__=="__main__": app.run(host="0.0.0.0",port=int(os.environ.get("PORT",10000)))
