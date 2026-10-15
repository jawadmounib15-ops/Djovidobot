import os, time, threading
from flask import Flask, jsonify
from datetime import datetime, timedelta
import pandas as pd
import requests
from curl_cffi import requests as cffi_requests

TOKEN = os.getenv("TELEGRAM_TOKEN", os.getenv("TOKEN", ""))
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", os.getenv("CHAT_ID", ""))

PAIRS = [ # bot.py - STRETTO +2 PELO - 66% + coppie richieste
import os, time, threading
from datetime import datetime
from zoneinfo import ZoneInfo
import pandas as pd, requests
from curl_cffi import requests as cffi_requests
from flask import Flask

TOKEN = os.getenv("TELEGRAM_TOKEN", os.getenv("TOKEN", ""))
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", os.getenv("CHAT_ID", ""))

# COPPIE COME RICHIESTO DA TE
PAIRS = ["EURUSD=X","GBPUSD=X","EURGBP=X","USDJPY=X","AUDUSD=X","EURJPY=X","GBPJPY=X","AUDJPY=X","CHFJPY=X","USDCAD=X","USDCHF=X","EURCHF=X","CADJPY=X","CADCHF=X","AUDCHF=X","AUDCAD=X","GBPCAD=X"]

_YF = cffi_requests.Session(impersonate="chrome", timeout=20)
ITALY = ZoneInfo("Europe/Rome")
cooldown = {}

def ora_it(): return datetime.now(ITALY).strftime("%H:%M:%S")
def ora_num(): return datetime.now(ITALY).hour
def fix_df(df):
    if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
    return df
def ema(s,p): return s.ewm(span=p).mean()

def pinbar_stretto(df):
    if len(df)<80: return None
    pin_c, conf_c = df.iloc[-2], df.iloc[-1]
    O,H,L,C = float(pin_c['Open']),float(pin_c['High']),float(pin_c['Low']),float(pin_c['Close'])
    total = H-L
    if total<=0: return None
    corpo = abs(O-C) or total*0.05
    inf, sup = min(O,C)-L, H-max(O,C)
    forza = (inf if inf>sup else sup)/total*100

    # +2 PELO: prima 1.55x 44% sup 33% corpo 50% forza 64%
    # ora: 1.65x 46% sup 31% corpo 46% forza 66%
    is_hammer = (inf >= corpo*1.65 and inf >= total*0.46 and sup <= total*0.31 and corpo <= total*0.46)
    is_star = (sup >= corpo*1.65 and sup >= total*0.46 and inf <= total*0.31 and corpo <= total*0.46)
    if not (is_hammer or is_star): return None
    if forza < 66: return None

    # SR 0.13% -> 0.11%
    last_30_high = df['High'].iloc[-32:-2].max()
    last_30_low = df['Low'].iloc[-32:-2].min()
    tocca_sr = (L <= last_30_low*1.0011) if is_hammer else (H >= last_30_high*0.9989)
    if not tocca_sr: return None

    ema20 = float(df['ema20'].iloc[-2])
    ema50 = float(df['ema50'].iloc[-2])
    ema20_prev = float(df['ema20'].iloc[-6])
    if is_hammer:
        if ema20 > ema50*1.001 and ema20 >= ema20_prev: return None
    else:
        if ema20 < ema50*0.999 and ema20 <= ema20_prev: return None

    # CONF 55% -> 60%
    if is_hammer and float(conf_c['Close']) < L + total*0.60: return None
    if is_star and float(conf_c['Close']) > H - total*0.60: return None
    if is_hammer and float(conf_c['Close']) <= float(conf_c['Open']): return None
    if is_star and float(conf_c['Close']) >= float(conf_c['Open']): return None

    if ora_num() < 8 or ora_num() > 22: return None

    return {"dir":"SU" if is_hammer else "GIÙ","tipo":"HAMMER" if is_hammer else "STAR","entry50":(H+L)/2,"forza":forza}

def send(m):
    try: requests.get(f"https://api.telegram.org/bot{TOKEN}/sendMessage", params={"chat_id":CHAT_ID,"text":m,"parse_mode":"HTML"}, timeout=10)
    except: pass

def scan():
    trovati=0
    for s in PAIRS:
        if trovati>=2: break
        clean=s.replace("=X","")
        if clean in cooldown and time.time()-cooldown[clean] < 600: continue
        try:
            import yfinance as yf
            df = fix_df(yf.Ticker(s, session=_YF).history(period="1d", interval="1m"))
            if len(df)<80: continue
            df['ema20']=ema(df['Close'],20)
            df['ema50']=ema(df['Close'],50)
            pin = pinbar_stretto(df)
            if not pin: continue
            cooldown[clean]=time.time()
            sig = "CALL" if pin["dir"]=="SU" else "PUT"
            send(f"💎 <b>PIN +2 PELO 66%</b> 💎\nAsset: <b>{clean}</b> {pin['tipo']}\nDir: <b>{sig}</b> Forza {pin['forza']:.0f}%\nEntry: <code>{pin['entry50']:.5f}</code>\nSR 0.11% + Trend + Conf 60%\n{ora_it()}")
            print(f"SEGNALE {clean} {pin['forza']:.0f}%", flush=True)
            trovati+=1
        except: continue

def loop():
    send(f"🚀 <b>STRETTO +2 PELO 66% AVVIATO</b>\nPin 1.65x 46% Forza 66%\nSR 0.11% Conf 60%\nCoppie: {len(PAIRS)}\nOra {ora_it()}")
    while True:
        try: scan(); time.sleep(40)
        except: time.sleep(10)

threading.Thread(target=loop, daemon=True).start()
app=Flask(__name__)
@app.route('/')
def home(): return f"+2 PELO 66% {ora_it()} - {len(PAIRS)} pairs"
if __name__=="__main__": app.run(host="0.0.0.0", port=int(os.environ.get("PORT",10000)))]

app = Flask(__name__)
pins_live = []
pins_storico = []
cooldown = {}
LOG_FILE = "/tmp/v68.log"

def log(m):
    line = f"{datetime.now().strftime('%H:%M:%S')} {m}"
    print(line, flush=True)
    try:
        with open(LOG_FILE, "a") as f: f.write(line+"\n")
    except: pass

def ora_now(): return datetime.now().strftime("%H:%M:%S")
def data_now(): return datetime.now().strftime("%d/%m %H:%M:%S")

def send(msg):
    try: requests.get(f"https://api.telegram.org/bot{TOKEN}/sendMessage", params={"chat_id":CHAT_ID,"text":msg}, timeout=10)
    except: pass

def rsi(s,p=14):
    d=s.diff(); g=d.where(d>0,0).rolling(p).mean(); l=-d.where(d<0,0).rolling(p).mean()
    return 100-(100/(1+g/l))
def atr(df,p=14):
    hl=df['High']-df['Low']; hc=abs(df['High']-df['Close'].shift()); lc=abs(df['Low']-df['Close'].shift())
    tr=pd.concat([hl,hc,lc],axis=1).max(axis=1)
    return tr.rolling(p).mean()
def stochastic(df,k=14,d=3):
    lo=df['Low'].rolling(k).min(); hi=df['High'].rolling(k).max()
    k_perc=100*((df['Close']-lo)/(hi-lo))
    return k_perc, k_perc.rolling(d).mean()

def get_df_fast(symbol):
    for _ in range(2):
        try:
            url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?interval=15m&range=5d"
            r = cffi_requests.get(url, impersonate="chrome120", timeout=8)
            if r.status_code!=200: continue
            j=r.json()
            quote=j['chart']['result'][0]['indicators']['quote'][0]
            df=pd.DataFrame({'High':quote['high'],'Low':quote['low'],'Close':quote['close']}).dropna()
            if len(df)<50: continue
            log(f"{symbol} OK {len(df)}")
            return df
        except Exception as e:
            log(f"{symbol} ERR {str(e)[:40]}")
            time.sleep(1)
    log(f"{symbol} SKIP")
    return pd.DataFrame()

def scan():
    global pins_live, pins_storico
    log(">>> INIZIO SCAN")
    count=0
    for symbol in PAIRS:
        if count>=3: break
        clean=symbol.replace("=X","")
        if clean in cooldown and time.time()-cooldown[clean] < 2700: continue # 45min
        df=get_df_fast(symbol)
        if len(df)<210: continue
        try:
            df['e20']=df['Close'].ewm(span=20).mean()
            df['e200']=df['Close'].ewm(span=200).mean()
            df['rsi']=rsi(df['Close'])
            df['atr']=atr(df,14)
            df['atr_ma50']=df['atr'].rolling(50).mean()
            df['stoch_k'],_ = stochastic(df)
            last=df.iloc[-1]
            price=float(last['Close']); rsi_v=float(last['rsi']); stoch_k=float(last['stoch_k'])
            # ALLARGATO UN PELO come chiesto
            if last['atr'] < last['atr_ma50']*0.55: continue
            if last['atr'] > last['atr_ma50']*2.2: continue
            tocco_e20=abs(price-float(last['e20']))/price < 0.006
            dist_e200=abs(price-float(last['e200']))/price
            if dist_e200 < 0.0005: continue
            signal=None
            if price>float(last['e200']) and tocco_e20 and 25<=rsi_v<=42 and stoch_k<22: signal="BUY"
            if price<float(last['e200']) and tocco_e20 and 58<=rsi_v<=75 and stoch_k>78: signal="SELL"
            if signal:
                scad_time = datetime.now() + timedelta(minutes=15)
                pin = {"asset": clean, "dir": "CALL SU" if signal=="BUY" else "PUT GIÙ", "signal": signal, "entry": round(price,5), "rsi": round(rsi_v,0), "sto": round(stoch_k,0), "ora": ora_now(), "data": data_now(), "scadenza": scad_time.strftime("%H:%M:%S"), "scad_ts": scad_time.timestamp(), "scad": "15 MIN"}
                pins_live.insert(0,pin); pins_storico.insert(0,pin)
                pins_live=pins_live[:20]; pins_storico=pins_storico[:100]
                send(f"🎯 V68 {signal} {clean} RSI {rsi_v:.0f} STO {stoch_k:.0f}")
                log(f"*** SEGNALE {clean} {signal} RSI {rsi_v:.0f} ***")
                cooldown[clean]=time.time()
                count+=1
        except Exception as e:
            log(f"calc {clean} {e}")
    log(f">>> FINE SCAN trovati {count}")

def loop():
    try: os.remove(LOG_FILE)
    except: pass
    log("LOOP V68 AVVIATO - LARGO + SUONO + STORICO + SCADENZA")
    send("🚀 V68 LARGO con SUONO STORICO SCADENZA 15MIN")
    while True:
        try: scan()
        except Exception as e: log(f"LOOP ERR {e}")
        time.sleep(60)

@app.route('/')
def home():
    return """
<!DOCTYPE html><html><head><meta name='viewport' content='width=device-width, initial-scale=1'><title>V68</title>
<style>body{background:#0a0a0a;color:#fff;font-family:Arial;padding:12px}h2{color:#00ff88}.card{background:#1e1e1e;padding:12px;margin:8px 0;border-radius:10px;display:flex;justify-content:space-between}.call{border-left:5px solid #00ff88}.put{border-left:5px solid #ff4444}button{background:#00ff88;color:#000;border:0;padding:14px;width:100%;border-radius:10px;font-weight:bold;font-size:17px;margin:6px 0}.tab{background:#222;color:#fff;border:1px solid #333;padding:10px 18px;border-radius:8px;margin-right:6px}.tab.active{background:#00ff88;color:#000}small{color:#aaa}.scad{color:#ffaa00;font-weight:bold}</style>
</head><body>
<h2>📡 V68 LARGO + SUONO</h2>
<button id="btn" onclick="attiva()">🔔 ATTIVA SUONO FORTE</button>
<div style="margin:10px 0"><button class="tab active" id="tLive" onclick="show('live')">LIVE</button><button class="tab" id="tStor" onclick="show('stor')">STORICO (<span id="numStor">0</span>)</button><a href="/debug" style="color:#0f8;margin-left:12px">DEBUG</a></div>
<div id="ora"></div><div id="listLive">Avvio V68...</div><div id="listStor" style="display:none"></div>
<script>
let audioCtx=null,suono=false,last=0;
function attiva(){audioCtx=new(window.AudioContext||window.webkitAudioContext)();suono=true;document.getElementById('btn').innerHTML='🔊 SUONO ATTIVO - forte';document.getElementById('btn').style.background='#ffaa00';beep();}
function beep(){if(!audioCtx)return;for(let i=0;i<3;i++){setTimeout(()=>{let o=audioCtx.createOscillator(),g=audioCtx.createGain();o.type='square';o.frequency.value=880;g.gain.value=0.9;o.connect(g);g.connect(audioCtx.destination);o.start();g.gain.exponentialRampToValueAtTime(0.01,audioCtx.currentTime+0.4);o.stop(audioCtx.currentTime+0.4);},i*500);}}
function show(t){document.getElementById('tLive').classList.toggle('active',t=='live');document.getElementById('tStor').classList.toggle('active',t=='stor');document.getElementById('listLive').style.display=t=='live'?'block':'none';document.getElementById('listStor').style.display=t=='stor'?'block':'none';}
function render(d,el){let h='';let now=Date.now()/1000;d.forEach(p=>{let scaduta= p.scad_ts && now>p.scad_ts?'<span style="color:#f44">SCADUTO</span>':'<span class="scad">Scad '+p.scadenza+'</span>';h+=`<div class='card ${p.signal=='BUY'?'call':'put'}'><div><b style="font-size:18px">${p.asset}</b> <small>RSI ${p.rsi} STO ${p.sto}</small><br><small>Entry: ${p.entry}</small><br><small>${p.data}</small></div><div style='text-align:right'><b style='color:${p.signal=='BUY'?'#00ff88':'#ff4444'}'>${p.dir}</b><br>${scaduta}</div></div>`;});if(d.length==0)h='<p style="color:#888;text-align:center">In attesa segnali... filtra largo attivo</p>';document.getElementById(el).innerHTML=h;}
async function load(){let r1=await fetch('/api/pins');let live=await r1.json();let r2=await fetch('/api/storico');let stor=await r2.json();document.getElementById('ora').innerText=new Date().toLocaleTimeString()+' | Live:'+live.length+' Storico:'+stor.length;document.getElementById('numStor').innerText=stor.length;if(live.length>last&&last!=0&&suono){beep();if(navigator.vibrate)navigator.vibrate([300,100,300,100,600]);}last=live.length;render(live,'listLive');render(stor,'listStor');}load();setInterval(load,8000);
</script></body></html>
"""
@app.route('/api/pins')
def api_pins(): return jsonify(pins_live)
@app.route('/api/storico')
def api_storico(): return jsonify(pins_storico)
@app.route('/debug')
def debug():
    try:
        with open(LOG_FILE, "r") as f: lines=f.readlines()[-60:]
    except: lines=["log vuoto"]
    h="<b>LOG V68 LARGO + SUONO + STORICO + SCAD</b><br><br>"
    for l in lines[::-1]: h+=f"{l}<br>"
    h+=f"<br>Live:{len(pins_live)} Storico:{len(pins_storico)}<br><a href='/debug'>reload</a> - <a href='/'>home</a>"
    return h

threading.Thread(target=loop, daemon=True).start()
if __name__=="__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT",10000)))
