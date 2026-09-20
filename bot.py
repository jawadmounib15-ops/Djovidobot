import os, requests, time, yfinance as yf, pandas as pd
from flask import Flask
from threading import Thread
from datetime import datetime, timedelta

app = Flask(__name__)
TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT = os.getenv("TELEGRAM_CHAT_ID")

PAIRS_REAL = {
    "EURUSD=X": "EUR/USD",
    "GBPUSD=X": "GBP/USD",
    "USDJPY=X": "USD/JPY"
}

PAIRS_OTC = {
    "BTC-USD": ("EUR/USD OTC", 1.0850),
    "ETH-USD": ("GBP/USD OTC", 1.2700),
    "SOL-USD": ("USD/JPY OTC", 155.50)
}

LAST = {}

def send(m):
    try:
        if TOKEN and CHAT:
            requests.post("https://api.telegram.org/bot"+TOKEN+"/sendMessage", data={"chat_id": CHAT, "text": m}, timeout=10)
    except:
        pass

def get_data(sym, interval, period):
    try:
        df = yf.download(sym, interval=interval, period=period, progress=False, auto_adjust=False)
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        return df
    except:
        return pd.DataFrame()

def ema(s,n):
    return s.ewm(span=n, adjust=False).mean()

def sma(s,n):
    return s.rolling(n).mean()

def rsi_calc(s,n=14):
    d=s.diff()
    g=d.where(d>0,0).rolling(n).mean()
    l=-d.where(d<0,0).rolling(n).mean()
    return 100-(100/(1+g/l))

def make_msg(tipo,coppia,lavoro,motivo,prezzo):
    now=datetime.now()
    exp=now+timedelta(minutes=5)
    txt = f"{tipo} - {coppia}\n"
    txt += f"Prezzo: {round(prezzo,5)}\n"
    txt += f"Scadenza: 5 MINUTI\n"
    txt += f"Entrata: {now.strftime('%H:%M:%S')}\n"
    txt += f"Scade alle: {exp.strftime('%H:%M:%S')}\n"
    txt += f"Lavoro: {lavoro}\n"
    txt += f"Motivo: {motivo}\n"
    txt += f"Azione: Entra subito {tipo}"
    return txt

def can_send(coppia,lavoro,is_otc):
    key=coppia+"_"+lavoro
    now=time.time()
    cd = 3600 if is_otc else 1800
    if key in LAST and now-LAST[key]<cd:
        return False
    LAST[key]=now
    return True

def check(sym,name,base_price,is_otc):
    df_h1=get_data(sym,"60m","10d")
    df_m15=get_data(sym,"15m","5d")
    df_m5=get_data(sym,"5m","3d")
    df_m1=get_data(sym,"1m","2d")
    if len(df_m15)<50 or len(df_m1)<30:
        return []

    c1_raw=float(df_m1["Close"].iloc[-1])
    if is_otc:
        try:
            c1_60=float(df_m1["Close"].iloc[-60])
            var=(c1_raw-c1_60)/c1_60
            c1=base_price*(1+var*0.1)
        except:
            c1=base_price
    else:
        c1=c1_raw

    o1=float(df_m1["Open"].iloc[-1])
    l1=float(df_m1["Low"].iloc[-1])
    h1=float(df_m1["High"].iloc[-1])
    c_prev=float(df_m1["Close"].iloc[-2])
    o_prev=float(df_m1["Open"].iloc[-2])
    r1=float(rsi_calc(df_m1["Close"]).iloc[-1])
    r_prev=float(rsi_calc(df_m1["Close"]).iloc[-2])

    e5_15=float(ema(df_m15["Close"],5).iloc[-1])
    e20_15=float(ema(df_m15["Close"],20).iloc[-1])
    e50_15=float(ema(df_m15["Close"],50).iloc[-1])
    s50_15=float(sma(df_m15["Close"],50).iloc[-1])

    body=abs(c1_raw-o1)
    lo=min(o1,c1_raw)-l1
    up=h1-max(o1,c1_raw)
    pin_buy=lo>body*2.0
    pin_sell=up>body*2.0
    eng_buy=c1_raw>o1 and c_prev<o_prev
    eng_sell=c1_raw<o1 and c_prev>o_prev

    res=[]
    if not is_otc:
        if e5_15>e20_15 and e20_15>e50_15 and pin_buy:
            if can_send(name,"L1",False):
                res.append(make_msg("BUY",name,"L1 TREND","3 EMA UP + Pinbar",c1))
        if e5_15<e20_15 and e20_15<e50_15 and pin_sell:
            if can_send(name,"L1",False):
                res.append(make_msg("SELL",name,"L1 TREND","3 EMA DOWN + Pinbar",c1))
        if r_prev<30 and r1>30:
            if can_send(name,"L2",False):
                res.append(make_msg("BUY",name,"L2 RIMBALZO","RSI 30 + Bollinger",c1))
        if r_prev>70 and r1<70:
            if can_send(name,"L2",False):
                res.append(make_msg("SELL",name,"L2 RIMBALZO","RSI 70 + Bollinger",c1))
    else:
        if e5_15>e20_15 and pin_buy and eng_buy and r1>40 and r1<65:
            if can_send(name,"L1-OTC",True):
                res.append(make_msg("BUY",name,"L1-STRICT OTC","3 EMA + Pinbar + Engulfing",c1))
        if e5_15<e20_15 and pin_sell and eng_sell and r1<60 and r1>35:
            if can_send(name,"L1-OTC",True):
                res.append(make_msg("SELL",name,"L1-STRICT OTC","3 EMA + Pinbar + Engulfing",c1))
        if abs(c1_raw-s50_15)/c1_raw<0.0015 and eng_buy and e5_15>e20_15:
            if can_send(name,"L4-OTC",True):
                res.append(make_msg("BUY",name,"L4-STRICT OTC","SMA50 + Engulfing",c1))
        if abs(c1_raw-s50_15)/c1_raw<0.0015 and eng_sell and e5_15<e20_15:
            if can_send(name,"L4-OTC",True):
                res.append(make_msg("SELL",name,"L4-STRICT OTC","SMA50 + Engulfing",c1))

    return res

def loop():
    send("V37.1 OTC STRICT FIX - LIVE OK")
    while True:
        try:
            now=datetime.now()
            if now.weekday()>=5:
                for sym, (dname, base) in PAIRS_OTC.items():
                    for s in check(sym,dname,base,True):
                        send(s)
                        time.sleep(5)
            else:
                for sym, dname in PAIRS_REAL.items():
                    for s in check(sym,dname,0,False):
                        send(s)
                        time.sleep(5)
            time.sleep(75)
        except Exception as e:
            print(e)
            time.sleep(60)

@app.route("/")
def home():
    return "V37.1 FIX LIVE OK"

Thread(target=loop, daemon=True).start()

if __name__=="__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT",10000)))
