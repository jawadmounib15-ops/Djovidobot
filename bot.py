# bot.py - V70 FIX - 1H+4H - ANTI DUPLICATO + SOLO SEGNALI OK
import os, time, threading
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import pandas as pd, requests
from curl_cffi import requests as cffi_requests
from flask import Flask

TOKEN = os.getenv("TELEGRAM_TOKEN", os.getenv("TOKEN", ""))
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", os.getenv("CHAT_ID", ""))
PAIRS = ["EURUSD=X","GBPUSD=X","EURGBP=X","USDJPY=X","AUDUSD=X","EURJPY=X","GBPJPY=X","AUDJPY=X","CHFJPY=X","USDCAD=X","USDCHF=X","EURCHF=X"]

# V70 PARAMETRI STRETTI BASATI SUI TUOI SEGNALI
FORZA_MIN, FORZA_MAX = 70, 92
RSI_BUY_MIN, RSI_BUY_MAX = 25, 38
RSI_SELL_MIN, RSI_SELL_MAX = 62, 75
WICK_RATIO, CORPO_MAX = 2.0, 0.30

TFS = {
    "1H": {"interval":"60m","range":"15d","scad_min":120,"label":"2H","cool":3600}, # 1 ora no duplicati
    "4H": {"interval":"60m","range":"30d","scad_min":480,"label":"8H","resample":"4H","cool":14400}, # 4 ore
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
            if len(df)<80: return pd.DataFrame()
            if resample=="4H":
                df=df.set_index(pd.date_range(end=datetime.now(), periods=len(df), freq='H')).resample('4H').agg({'Open':'first','High':'max','Low':'min','Close':'last'}).dropna().reset_index(drop=True)
            return df.tail(200)
    except: return pd.DataFrame()

def send(m):
    try: requests.get(f"https://api.telegram.org/bot{TOKEN}/sendMessage", params={"chat_id":CHAT_ID,"text":m,"parse_mode":"HTML"}, timeout=8)
    except: pass

def lavoro_v70():
    print("V70 FIX avviato", flush=True)
    while True:
        try:
            for tf_name, cfg in TFS.items():
                for sym in PAIRS:
                    clean=sym.replace("=X","")
                    key=f"{clean}_{tf_name}"
                    if key in cooldown and time.time()-cooldown[key]<cfg["cool"]: continue
                    
                    df=get_df(sym, cfg["interval"], cfg["range"], cfg.get("resample"))
                    if len(df)<80: continue
                    df['ema20']=ema(df['Close'],20); df['ema50']=ema(df['Close'],50); df['ema200']=ema(df['Close'],200)
                    df['rsi']=rsi(df['Close']); df['atr']=atr(df,14); df['atr_ma']=df['atr'].rolling(50).mean()
                    c=df.iloc[-2]; conf=df.iloc[-1]
                    O,H,L,C=float(c['Open']),float(c['High']),float(c['Low']),float(c['Close'])
                    total=H-L
                    if total<0.00008: continue
                    
                    # FIX 1: SOLO ATR ATTIVO - toglie CHFJPY lento che ti ha dato falso
                    if float(c['atr']) < float(c['atr_ma'])*0.70: continue
                    
                    corpo=abs(O-C) or total*0.05; inf=min(O,C)-L; sup=H-max(O,C)
                    forza=max(inf,sup)/total*100
                    hammer=inf>=corpo*WICK_RATIO and inf>=total*0.55 and sup<=total*0.20 and corpo<=total*CORPO_MAX
                    star=sup>=corpo*WICK_RATIO and sup>=total*0.55 and inf<=total*0.20 and corpo<=total*CORPO_MAX
                    if not ((hammer or star) and FORZA_MIN<=forza<=FORZA_MAX): continue
                    
                    e20=float(c['ema20']); e50=float(c['ema50']); e200=float(c['ema200'])
                    rv=float(c['rsi']); price=C
                    
                    # FIX 2: RSI STRETTISSIMO - toglie AUDUSD 58.6 e USDCAD 43 neutro
                    if hammer and not (RSI_BUY_MIN <= rv <= RSI_BUY_MAX): continue
                    if star and not (RSI_SELL_MIN <= rv <= RSI_SELL_MAX): continue
                    
                    # FIX 3: CONTRO EMA200 NO - toglie USDCAD CALL sotto EMA200
                    if hammer and C < e200*0.998: continue
                    if star and C > e200*1.002: continue
                    
                    # FIX 4: SOLO CONFERMA OK - toglie DEBOLE
                    conf_c=float(conf['Close'])
                    if hammer and (conf_c < L+total*0.65 or conf_c <= float(conf['Open'])): continue
                    if star and (conf_c > H-total*0.65 or conf_c >= float(conf['Open'])): continue
                    
                    # FIX 5: SL troppo stretto NO
                    sl = L-total*0.25 if hammer else H+total*0.25
                    if abs(sl-C)/C < 0.0008: continue # SL < 0.08% troppo vicino
                    
                    cooldown[key]=time.time(); stats[tf_name]+=1
                    sig="CALL 📈" if hammer else "PUT 📉"
                    tipo="Hammer"; 
                    if star: tipo="Shooting Star"
                    sc=scadenza_it(cfg["scad_min"])
                    dist_e20=(C-e20)/C*100; dist_e200=(C-e200)/C*100
                    sl_val=sl; tp1=C+total*1.8 if hammer else C-total*1.8; tp2=C+total*3.0 if hammer else C-total*3.0
                    
                    msg=(
                        f"🎯 <b>PINBAR V70 {tf_name}</b> 🎯\n"
                        f"━━━━━━━━━━━━━━\n"
                        f"💱 {clean} | <b>{sig} {tipo}</b>\n"
                        f"⏰ TF: {tf_name} → Scad: {cfg['label']} alle {sc}\n"
                        f"━━━━━━━━━━━━━━\n"
                        f"📍 Entry: {(H+L)/2:.5f}\n"
                        f"💰 Price: {C:.5f}\n"
                        f"📊 Forza: {forza:.1f}% | Corpo: {corpo/total*100:.1f}% | Wick: {max(inf,sup)/total*100:.1f}%\n"
                        f"📈 RSI: {rv:.1f} ({'BUY' if hammer else 'SELL'} OK) | ATR: ATTIVO ✓\n"
                        f"📉 EMA20: {e20:.5f} ({dist_e20:+.2f}%) | EMA200: {e200:.5f} ({dist_e200:+.2f}%)\n"
                        f"━━━━━━━━━━━━━━\n"
                        f"✅ Conferma: {conf_c:.5f} OK ✓\n"
                        f"🛡️ SL: {sl_val:.5f} | 🎯 TP1: {tp1:.5f} | TP2: {tp2:.5f}\n"
                        f"🕒 {ora_it()} | Filtro V70 {FORZA_MIN}-{FORZA_MAX}%"
                    )
                    send(msg)
                    time.sleep(2)
                time.sleep(3)
            time.sleep(90)
        except Exception as e: print(f"V70 ERR {e}"); time.sleep(20)

threading.Thread(target=lavoro_v70, daemon=True).start()
app=Flask(__name__)
@app.route('/')
def home(): return f"V70 FIX | 1H:{stats['1H']} 4H:{stats['4H']} | Forza {FORZA_MIN}-{FORZA_MAX} | {ora_it()} | No duplicati"
if __name__=="__main__":
    send(f"🚀 <b>V70 FIX AVVIATO</b>\nAnti-duplicato 1H/4H\nSolo ATR attivo + RSI {RSI_BUY_MIN}-{RSI_BUY_MAX}/{RSI_SELL_MIN}-{RSI_SELL_MAX} + Conferma OK\n{ora_it()}")
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT",10000)))
