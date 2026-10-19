# bot.py - PINBAR LARGO 1H+4H - DETTAGLI COMPLETI
import os, time, threading
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import pandas as pd, requests
from curl_cffi import requests as cffi_requests
from flask import Flask

TOKEN = os.getenv("TELEGRAM_TOKEN", os.getenv("TOKEN", ""))
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", os.getenv("CHAT_ID", ""))
PAIRS = ["EURUSD=X","GBPUSD=X","EURGBP=X","USDJPY=X","AUDUSD=X","EURJPY=X","GBPJPY=X","AUDJPY=X","CHFJPY=X","USDCAD=X","USDCHF=X","EURCHF=X"]

FORZA_MIN, FORZA_MAX = 60, 92
RSI_BUY_MIN, RSI_BUY_MAX = 20, 45
RSI_SELL_MIN, RSI_SELL_MAX = 55, 80
WICK_RATIO, CORPO_MAX = 1.5, 0.40

TFS = {
    "1H": {"interval":"60m","range":"15d","scad_min":120,"label":"2H","cool":3600},
    "4H": {"interval":"60m","range":"30d","scad_min":480,"label":"8H","resample":"4H","cool":10800},
}

ITALY = ZoneInfo("Europe/Rome")
cooldown = {}; lock = threading.Lock()
stats = {"1H":0,"4H":0}

def ora_it(): return datetime.now(ITALY).strftime("%H:%M:%S %d/%m")
def scadenza_it(m): return (datetime.now(ITALY)+timedelta(minutes=m)).strftime("%H:%M:%S %d/%m")
def ema(s,p): return s.ewm(span=p).mean()
def rsi(s,p=14):
    d=s.diff(); g=d.where(d>0,0).rolling(p).mean(); l=-d.where(d<0,0).rolling(p).mean()
    return 100-(100/(1+g/l))
def atr(df,p=14):
    hl=df['High']-df['Low']; hc=abs(df['High']-df['Close'].shift()); lc=abs(df['Low']-df['Close'].shift())
    tr=pd.concat([hl,hc,lc],axis=1).max(axis=1)
    return tr.rolling(p).mean()

def get_df(sym, interval, range_str, resample=None):
    try:
        with lock:
            url=f"https://query1.finance.yahoo.com/v8/finance/chart/{sym}?interval={interval}&range={range_str}"
            r=cffi_requests.get(url, impersonate="chrome120", timeout=10)
            q=r.json()['chart']['result'][0]['indicators']['quote'][0]
            df=pd.DataFrame({'Open':q['open'],'High':q['high'],'Low':q['low'],'Close':q['close']}).dropna()
            if len(df)<60: return pd.DataFrame()
            if resample=="4H":
                df=df.set_index(pd.date_range(end=datetime.now(), periods=len(df), freq='H')).resample('4H').agg({'Open':'first','High':'max','Low':'min','Close':'last'}).dropna().reset_index(drop=True)
            return df.tail(200)
    except: return pd.DataFrame()

def send(m):
    try: requests.get(f"https://api.telegram.org/bot{TOKEN}/sendMessage", params={"chat_id":CHAT_ID,"text":m,"parse_mode":"HTML"}, timeout=8)
    except: pass

def lavoro_pinbar_dettagli():
    print("PINBAR DETTAGLI avviato", flush=True)
    while True:
        try:
            for tf_name, cfg in TFS.items():
                for sym in PAIRS:
                    clean=sym.replace("=X","")
                    key=f"{clean}_{tf_name}"
                    if key in cooldown and time.time()-cooldown[key]<cfg["cool"]: continue
                    df=get_df(sym, cfg["interval"], cfg["range"], cfg.get("resample"))
                    if len(df)<60: continue
                    df['ema20']=ema(df['Close'],20); df['ema50']=ema(df['Close'],50); df['ema200']=ema(df['Close'],200)
                    df['rsi']=rsi(df['Close']); df['atr']=atr(df,14); df['atr_ma']=df['atr'].rolling(50).mean()
                    c=df.iloc[-2]; conf=df.iloc[-1]
                    O,H,L,C=float(c['Open']),float(c['High']),float(c['Low']),float(c['Close'])
                    total=H-L
                    if total<0.00005: continue
                    if df['atr'].iloc[-2] < df['atr_ma'].iloc[-2]*0.50: continue
                    corpo=abs(O-C) or total*0.05; inf=min(O,C)-L; sup=H-max(O,C)
                    forza=max(inf,sup)/total*100
                    hammer=inf>=corpo*WICK_RATIO and inf>=total*0.45 and sup<=total*0.30 and corpo<=total*CORPO_MAX
                    star=sup>=corpo*WICK_RATIO and sup>=total*0.45 and inf<=total*0.30 and corpo<=total*CORPO_MAX
                    if not ((hammer or star) and FORZA_MIN<=forza<=FORZA_MAX): continue
                    e20=float(df['ema20'].iloc[-2]); e50=float(df['ema50'].iloc[-2]); e200=float(df['ema200'].iloc[-2])
                    rv=float(df['rsi'].iloc[-2]); atr_v=float(df['atr'].iloc[-2])
                    if hammer and not (RSI_BUY_MIN <= rv <= RSI_BUY_MAX): continue
                    if star and not (RSI_SELL_MIN <= rv <= RSI_SELL_MAX): continue
                    if hammer and (float(conf['Close'])<L+total*0.50): continue
                    if star and (float(conf['Close'])>H-total*0.50): continue

                    cooldown[key]=time.time(); stats[tf_name]+=1
                    sig="CALL 📈" if hammer else "PUT 📉"
                    tipo="Hammer" if hammer else "Shooting Star"
                    sc=scadenza_it(cfg["scad_min"])
                    
                    # CALCOLI DETTAGLI
                    dist_ema20 = ((C-e20)/C*100); dist_ema200 = ((C-e200)/C*100)
                    sl = L - total*0.2 if hammer else H + total*0.2
                    tp1 = C + total*1.5 if hammer else C - total*1.5
                    tp2 = C + total*2.5 if hammer else C - total*2.5
                    conf_close = float(conf['Close'])
                    low50 = df['Low'].iloc[-51:-2].min(); high50 = df['High'].iloc[-51:-2].max()

                    msg = (
                        f"🎯 <b>PINBAR {tf_name} DETTAGLI</b> 🎯\n"
                        f"━━━━━━━━━━━━━━\n"
                        f"💱 Coppia: <b>{clean}</b>\n"
                        f"📊 Segnale: <b>{sig} - {tipo}</b>\n"
                        f"⏰ TF: <b>{tf_name}</b> | Scadenza: <b>{cfg['label']}</b>\n"
                        f"━━━━━━━━━━━━━━\n"
                        f"📍 Entry: <b>{(H+L)/2:.5f}</b>\n"
                        f"💰 Prezzo attuale: {C:.5f}\n"
                        f"🕐 Scadenza: <b>{sc}</b> ({cfg['label']})\n"
                        f"━━━━━━━━━━━━━━\n"
                        f"📈 DETTAGLI TECNICI:\n"
                        f"Forza: {forza:.1f}% (min {FORZA_MIN}%)\n"
                        f"RSI: {rv:.1f} ({'Ipervenduto' if rv<40 else 'Ipercomprato' if rv>60 else 'Neutro'})\n"
                        f"Corpo: {corpo/total*100:.1f}% | Wick: {max(inf,sup)/total*100:.1f}%\n"
                        f"EMA20: {e20:.5f} Dist: {dist_ema20:+.2f}%\n"
                        f"EMA50: {e50:.5f}\n"
                        f"EMA200: {e200:.5f} Dist: {dist_ema200:+.2f}%\n"
                        f"ATR: {atr_v:.5f} {'(Mercato attivo)' if atr_v>df['atr_ma'].iloc[-2] else '(Lento)'}\n"
                        f"Min 50: {low50:.5f} | Max 50: {high50:.5f}\n"
                        f"━━━━━━━━━━━━━━\n"
                        f"✅ CONFERMA: {conf_close:.5f} {'OK' if (hammer and conf_close> C) or (star and conf_close < C) else 'DEBOLE'}\n"
                        f"🛡️ SL: {sl:.5f}\n"
                        f"🎯 TP1: {tp1:.5f} (+1.5x)\n"
                        f"🎯 TP2: {tp2:.5f} (+2.5x)\n"
                        f"━━━━━━━━━━━━━━\n"
                        f"🕒 Segnale: {ora_it()}\n"
                        f"⚙️ Filtro: {FORZA_MIN}-{FORZA_MAX}% LARGO"
                    )
                    send(msg)
                    time.sleep(1.5)
                time.sleep(2)
            time.sleep(60)
        except Exception as e: print(f"DETTAGLI ERR {e}"); time.sleep(15)

threading.Thread(target=lavoro_pinbar_dettagli, daemon=True).start()
app=Flask(__name__)
@app.route('/')
def home(): return f"PINBAR DETTAGLI LARGO | 1H:{stats['1H']} 4H:{stats['4H']} | {ora_it()}"
if __name__=="__main__":
    send(f"🚀 <b>PINBAR DETTAGLI AVVIATO</b>\nTF 1H→2H 4H→8H\nCon SL/TP + EMA + RSI + Forza\n{ora_it()}")
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT",10000)))
