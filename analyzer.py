import os, time, threading
from flask import Flask, jsonify
from datetime import datetime, timedelta
import pandas as pd
import requests
from curl_cffi import requests as cffi_requests

TOKEN = os.getenv("TELEGRAM_TOKEN", os.getenv("TOKEN", ""))
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", os.getenv("CHAT_ID", ""))

PAIRS = ["EURUSD=X","GBPUSD=X","USDJPY=X","AUDUSD=X","USDCAD=X","USDCHF=X","NZDUSD=X","EURJPY=X","EURGBP=X","EURCHF=X","EURCAD=X","EURAUD=X","GBPJPY=X","GBPCHF=X","GBPAUD=X","AUDJPY=X","CADJPY=X","CHFJPY=X","NZDJPY=X","AUDCAD=X","NZDCAD=X"]

app = Flask(__name__)
pins_live = []
pins_storico = []
cooldown = {}
LOGS = []

def log(m):
    print(m, flush=True)
    LOGS.append(f"{datetime.now().strftime('%H:%M:%S')} {m}")
    if len(LOGS)>30: LOGS.pop(0)

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

def get_df_direct(symbol):
    try:
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?interval=15m&range=5d&includePrePost=false"
        sess = cffi_requests.Session(impersonate="chrome120", timeout=25)
        r = sess.get(url, headers={"User-Agent":"Mozilla/5.0"})
        if r.status_code!= 200:
            log(f"{symbol} HTTP {r.status_code}")
            return pd.DataFrame()
        j = r.json()
        result = j['chart']['result'][0]
        quote = result['indicators']['quote'][0]
        df = pd.DataFrame({
            'Open': quote['open'],
            'High': quote['high'],
            'Low': quote['low'],
            'Close': quote['close'],
        })
        df = df.dropna()
        if len(df) < 200:
            log(f"{symbol} poche {len(df)}")
            return pd.DataFrame()
        log(f"{symbol} OK {len(df)}")
        return df
    except Exception as e:
        log(f"{symbol} FAIL {e}")
        return pd.DataFrame()

def scan():
    global pins_live, pins_storico
    count=0
    log("INIZIO SCAN...")
    for symbol in PAIRS:
        if count>=3: break
        clean=symbol.replace("=X","")
        if clean in cooldown and time.time()-cooldown[clean] < 2700: continue
        df = get_df_direct(symbol)
        if len(df)<210:
            time.sleep(1)
            continue
        try:
            df['e20']=df['Close'].ewm(span=20).mean()
            df['e200']=df['Close'].ewm(span=200).mean()
            df['rsi']=rsi(df['Close'])
            df['atr']=atr(df,14)
            df['atr_ma50']=df['atr'].rolling(50).mean()
            df['stoch_k'],_ = stochastic(df)
            last=df.iloc[-1]
            price=float(last['Close']); rsi_v=float(last['rsi']); stoch_k=float(last['stoch_k'])
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
                send(f"🎯 V64 {signal} {clean} RSI {rsi_v:.0f} STO {stoch_k:.0f}")
                log(f"*** SEGNALE {clean} {signal} ***")
                cooldown[clean]=time.time()
                count+=1
        except Exception as e:
            log(f"calc {clean} {e}")
        time.sleep(1.5)
    log(f"FINE SCAN trovato {count}")

def loop():
    log("LOOP V64 AVVIATO")
    send(f"🚀 V64 DIRETTO SBLOCCATO")
    while True:
        try: scan()
        except Exception as e: log(f"loop err {e}")
        time.sleep(60)

@app.route('/')
def home():
    return """
<!DOCTYPE html><html><head><meta name='viewport' content='width=device-width, initial-scale=1'><title>V64</title>
<style>body{background:#0a0a0a;color:#fff;font-family:Arial;padding:12px}h2{color:#00ff88}.card{background:#1e1e1e;padding:12px;margin:8px 0;border-radius:10px;display:flex;justify-content:space-between}.call{border-left:5px solid #00ff88}.put{border-left:5px solid #ff4444}button{background:#00ff88;color:#000;border:0;padding:14px;width:100%;border-radius:10px;font-weight:bold;font-size:17px;margin:6px 0}.tab{background:#222;color:#fff;border:1px solid #333;padding:10px 18px;border-radius:8px;margin-right:6px}.tab.active{background:#00ff88;color:#000}small{color:#aaa}.scad{color:#ffaa00;font-weight:bold}</style>
</head><body>
<h2>📡 V64 DIRETTO + SUONO</h2>
<button id="btn" onclick="attiva()">🔔 ATTIVA SUONO FORTE</button>
<div style="margin:10px 0"><button class="tab active" id="tLive" onclick="show('live')">LIVE</button><button class="tab" id="tStor" onclick="show('stor')">STORICO (<span id="numStor">0</span>)</button><a href="/debug" style="color:#0f8;margin-left:12px">DEBUG</a></div>
<div id="ora"></div><div id="listLive">Avvio V64...</div><div id="listStor" style="display:none"></div>
<script>
let audioCtx=null,suono=false,last=0;
function attiva(){audioCtx=new(window.AudioContext||window.webkitAudioContext)();suono=true;document.getElementById('btn').innerHTML='🔊 SUONO ATTIVO';document.getElementById('btn').style.background='#ffaa00';beep();}
function beep(){if(!audioCtx)return;for(let i=0;i<3;i++){setTimeout(()=>{let o=audioCtx.createOscillator(),g=audioCtx.createGain();o.type='square';o.frequency.value=880;g.gain.value=0.9;o.connect(g);g.connect(audioCtx.destination);o.start();g.gain.exponentialRampToValueAtTime(0.01,audioCtx.currentTime+0.4);o.stop(audioCtx.currentTime+0.4);},i*500);}}
function show(t){document.getElementById('tLive').classList.toggle('active',t=='live');document.getElementById('tStor').classList.toggle('active',t=='stor');document.getElementById('listLive').style.display=t=='live'?'block':'none';document.getElementById('listStor').style.display=t=='stor'?'block':'none';}
function render(d,el){let h='';let now=Date.now()/1000;d.forEach(p=>{let scaduta= p.scad_ts && now>p.scad_ts?'<span style="color:#f44">SCADUTO</span>':'<span class="scad">Scad '+p.scadenza+'</span>';h+=`<div class='card ${p.signal=='BUY'?'call':'put'}'><div><b style="font-size:18px">${p.asset}</b> <small>RSI ${p.rsi} STO ${p.sto}</small><br><small>Entry: ${p.entry}</small><br><small>${p.data}</small></div><div style='text-align:right'><b style='color:${p.signal=='BUY'?'#00ff88':'#ff4444'}'>${p.dir}</b><br>${scaduta}</div></div>`;});if(d.length==0)h='<p style="color:#888;text-align:center">V64 attivo... guarda DEBUG</p>';document.getElementById(el).innerHTML=h;}
async function load(){let r1=await fetch('/api/pins');let live=await r1.json();let r2=await fetch('/api/storico');let stor=await r2.json();document.getElementById('ora').innerText=new Date().toLocaleTimeString()+' | Live:'+live.length+' Storico:'+stor.length;document.getElementById('numStor').innerText=stor.length;if(live.length>last&&last!=0&&suono){beep();if(navigator.vibrate)navigator.vibrate([300,100,300,100,600]);}last=live.length;render(live,'listLive');render(stor,'listStor');}load();setInterval(load,8000);
</script></body></html>
"""
@app.route('/api/pins')
def api_pins(): return jsonify(pins_live)
@app.route('/api/storico')
def api_storico(): return jsonify(pins_storico)
@app.route('/debug')
def debug():
    h="<b>LOG V64 DIRETTO - devi vedere OK per ogni coppia</b><br><br>"
    for l in LOGS[::-1]: h+=f"{l}<br>"
    h+=f"<br>Live:{len(pins_live)} Storico:{len(pins_storico)}<br><a href='/'>torna</a>"
    return h

threading.Thread(target=loop, daemon=True).start()
if __name__=="__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT",10000)))
