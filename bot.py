import os, time, requests, yfinance as yf, pandas as pd
from threading import Thread
from flask import Flask
from datetime import datetime, timedelta

TOKEN=os.getenv("TELEGRAM_TOKEN")
CHAT=os.getenv("TELEGRAM_CHAT_ID")
VERSION="V60 7 LAVORI MEDIO"

SYMBOLS=["EURUSD=X","GBPUSD=X","USDJPY=X","AUDUSD=X","USDCAD=X","USDCHF=X","EURGBP=X","EURJPY=X","GBPJPY=X"]

app=Flask(__name__)
@app.route("/")
def home():
    return f"{VERSION} LIVE"

def tg(m):
    try:
        url=f"https://api.telegram.org/bot{TOKEN}/sendMessage"
        data={"chat_id":CHAT,"text":m}
        requests.post(url, data=data, timeout=10)
    except:
        pass

def rsi(c):
    d=c.diff()
    g=d.where(d>0,0).rolling(14).mean()
    l=-d.where(d<0,0).rolling(14).mean()
    return 100-(100/(1+g/l))

last={}
stats={"L1":[0,0],"L2":[0,0],"L3":[0,0],"L4":[0,0],"L5":[0,0],"L6":[0,0],"L7":[0,0]}
pending=[]

def add(sym,price,msg,job):
    p={}
    p["sym"]=sym
    p["price"]=price
    p["msg"]=msg
    p["job"]=job
    p["time"]=datetime.now()
    pending.append(p)

def check_results():
    global pending
    now=datetime.now()
    keep=[]
    for p in pending:
        sec=(now-p["time"]).total_seconds()
        if sec<900:
            keep.append(p)
            continue
        try:
            df=yf.download(p["sym"], period="1d", interval="1m", progress=False, auto_adjust=True)
            if isinstance(df.columns, pd.MultiIndex):
                df.columns=df.columns.get_level_values(0)
            curr=float(df["Close"].iloc[-1])
            entry=p["price"]
            buy="BUY" in p["msg"]
            win=False
            if buy and curr>entry:
                win=True
            if not buy and curr<entry:
                win=True
            job=p["job"]
            stats[job][1]+=1
            if win:
                stats[job][0]+=1
            wr=0
            if stats[job][1]>0:
                wr=stats[job][0]/stats[job][1]*100
            res="WIN" if win else "LOSS"
            txt=f"{res} {p['msg']} {job} {stats[job][0]}/{stats[job][1]} {wr:.0f}%"
            tg(txt)
        except:
            keep.append(p)
    pending=keep

def get_sig(sym):
    try:
        df=yf.download(sym, period="5d", interval="15m", progress=False, auto_adjust=True)
        if len(df)<100:
            return
        if isinstance(df.columns, pd.MultiIndex):
            df.columns=df.columns.get_level_values(0)
        c=df["Close"]
        h=df["High"]
        low=df["Low"]
        e9=c.ewm(9).mean()
        e20=c.ewm(20).mean()
        e50=c.ewm(50).mean()
        s50=c.rolling(50).mean()
        r=rsi(c)
        macd=c.ewm(12).mean()-c.ewm(26).mean()
        sig=macd.ewm(9).mean()
        hist=macd-sig
        bmid=c.rolling(20).mean()
        bstd=c.rolling(20).std()
        blow=bmid-2*bstd
        bup=bmid+2*bstd
        atr=(h-low).rolling(14).mean()

        price=float(c.iloc[-1])
        pr=float(c.iloc[-2])
        pr2=float(c.iloc[-3])
        e9v=float(e9.iloc[-1])
        e20v=float(e20.iloc[-1])
        e50v=float(e50.iloc[-1])
        s50v=float(s50.iloc[-1]) if not pd.isna(s50.iloc[-1]) else e50v
        rv=float(r.iloc[-1])
        hv=float(hist.iloc[-1])
        hv2=float(hist.iloc[-2])
        blowv=float(blow.iloc[-1])
        bupv=float(bup.iloc[-1])
        atrv=float(atr.iloc[-1])
        h20=float(h.rolling(20).max().iloc[-2])
        l20=float(low.rolling(20).min().iloc[-2])

        if sym in last:
            if datetime.now()-last[sym] < timedelta(minutes=35):
                return

        pair=sym.replace("=X","")

        # L1 TREND
        if e20v>e50v and price>e20v and 55<=rv<=68 and hv>hv2:
            m=f"L1 TREND BUY {pair} RSI {rv:.0f}"
            tg(m); add(sym,price,m,"L1"); last[sym]=datetime.now(); return
        if e20v<e50v and price<e20v and 32<=rv<=45 and hv<hv2:
            m=f"L1 TREND SELL {pair} RSI {rv:.0f}"
            tg(m); add(sym,price,m,"L1"); last[sym]=datetime.now(); return

        # L2 RIMBALZO
        if price<=blowv*1.001 and rv<38:
            m=f"L2 RIMBALZO BUY {pair}"
            tg(m); add(sym,price,m,"L2"); last[sym]=datetime.now(); return
        if price>=bupv*0.999 and rv>62:
            m=f"L2 RIMBALZO SELL {pair}"
            tg(m); add(sym,price,m,"L2"); last[sym]=datetime.now(); return

        # L3 BREAKOUT
        if price>h20 and rv>58:
            m=f"L3 BREAKOUT BUY {pair}"
            tg(m); add(sym,price,m,"L3"); last[sym]=datetime.now(); return
        if price<l20 and rv<42:
            m=f"L3 BREAKOUT SELL {pair}"
            tg(m); add(sym,price,m,"L3"); last[sym]=datetime.now(); return
# L4 PULLBACK SICURO
e20_prev = float(e20.iloc[-2])
trend_up_forte = e20v > e50v and e20v > e20_prev
trend_down_forte = e20v < e50v and e20v < e20_prev

if trend_up_forte and e20v*0.998 < price < e20v*1.002 and 50 < rv < 60:
    add(f"L4 PULLBACK BUY {sym} RSI {rv:.0f}")
elif trend_down_forte and e20v*0.998 < price < e20v*1.002 and 40 < rv < 50:
    add(f"L4 PULLBACK SELL {sym} RSI {rv:.0f}")
        # L5 DOPPIO
        diff=abs(pr-pr2)/pr*100
        if diff<0.07 and price>pr and rv>50:
            m=f"L5 DOPPIO BUY {pair}"
            tg(m); add(sym,price,m,"L5"); last[sym]=datetime.now(); return
        if diff<0.07 and price<pr and rv<50:
            m=f"L5 DOPPIO SELL {pair}"
            tg(m); add(sym,price,m,"L5"); last[sym]=datetime.now(); return

        # L6 CROSS
        e9p=float(e9.iloc[-2])
        e20p=float(e20.iloc[-2])
        if e9p<e20p and e9v>e20v and rv>52:
            m=f"L6 CROSS BUY {pair}"
            tg(m); add(sym,price,m,"L6"); last[sym]=datetime.now(); return
        if e9p>e20p and e9v<e20v and rv<48:
            m=f"L6 CROSS SELL {pair}"
            tg(m); add(sym,price,m,"L6"); last[sym]=datetime.now(); return

        # L7 SUPPORTO
        dh=float(h.rolling(96).max().iloc[-1])
        dl=float(low.rolling(96).min().iloc[-1])
        if abs(price-dl)/dl*100<0.15 and rv<45:
            m=f"L7 SUPPORTO BUY {pair}"
            tg(m); add(sym,price,m,"L7"); last[sym]=datetime.now(); return
        if abs(price-dh)/dh*100<0.15 and rv>55:
            m=f"L7 SUPPORTO SELL {pair}"
            tg(m); add(sym,price,m,"L7"); last[sym]=datetime.now(); return

    except Exception as e:
        print(e)

def loop():
    time.sleep(5)
    tg(f"{VERSION} PARTITO")
    cnt=0
    while True:
        for s in SYMBOLS:
            get_sig(s)
            time.sleep(5)
        cnt+=1
        if cnt%5==0:
            check_results()
        time.sleep(180)

Thread(target=loop, daemon=True).start()
if __name__=="__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT",10000)))
