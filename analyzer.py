# Analyzer.py - FIX YAHOO BLOCCATO SU RENDER
import yfinance as yf
import pandas as pd
from flask import Flask, jsonify
from datetime import datetime
import threading, time, os, requests
try:
    from curl_cffi import requests as cffi_requests
    CFFI = True
except:
    CFFI = False

PAIRS = ["EURUSD=X","GBPUSD=X","GBPJPY=X","EURJPY=X","USDJPY=X","AUDJPY=X","EURGBP=X","EURCAD=X","GBPCAD=X","USDCAD=X"]
pins_live = []
pins_storico = []
ULTIMO_INVIO = {}
LOGS = []

BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
CHAT_ID = os.environ.get("CHAT_ID", "")

def log(m):
    print(m)
    LOGS.append(f"{datetime.now().strftime('%H:%M:%S')} {m}")
    if len(LOGS)>30: LOGS.pop(0)

def ora_now(): return datetime.now().strftime("%H:%M:%S")

def get_df(symbol):
    # METODO 1: curl_cffi - sblocca Yahoo
    if CFFI:
        try:
            sess = cffi_requests.Session(impersonate="chrome", timeout=15)
            df = yf.Ticker(symbol, session=sess).history(period="1d", interval="1m")
            if len(df)>5:
                log(f"{symbol} OK con cffi: {len(df)} candele")
                return df
        except Exception as e:
            log(f"{symbol} cffi fail: {e}")

    # METODO 2: normale
    try:
        df = yf.Ticker(symbol).history(period="1d", interval="1m")
        if len(df)>5:
            log(f"{symbol} OK normale: {len(df)}")
            return df
        else:
            log(f"{symbol} VUOTO normale: {len(df)}")
    except Exception as e:
        log(f"{symbol} normale fail: {e}")

    # METODO 3: 5m fallback
    try:
        df = yf.Ticker(symbol).history(period="5d", interval="5m")
        if len(df)>5:
            log(f"{symbol} OK 5m fallback: {len(df)}")
            return df
    except Exception as e:
        log(f"{symbol} 5m fail: {e}")

    return pd.DataFrame()

def check_pinbar(df):
    if len(df)<5: return []
    if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
    sigs=[]
    for idx in range(-1,-4,-1):
        try:
            c=df.iloc[idx]
            O=float(c['Open']); H=float(c['High']); L=float(c['Low']); C=float(c['Close'])
            total=H-L
            if total<=0: continue
            corpo=abs(O-C) or total*0.1
            inf=min(O,C)-L; sup=H-max(O,C)
            # ULTRA ALLARGATO 25% - troverà sicuro
            is_hammer=inf>=total*0.28
            is_star=sup>=total*0.28
            if not is_hammer and not is_star: continue
            forza=int((inf if is_hammer else sup)/total*100)
            if forza<25: continue
            sigs.append({"forza":forza,"is_hammer":is_hammer,"H":H,"L":L,"O":O,"C":C})
        except: continue
    return sigs

def scanner_loop():
    global pins_live, pins_storico
    log("SCANNER AVVIATO")
    while True:
        for sym in PAIRS:
            try:
                df=get_df(sym)
                if len(df)==0: continue
                pins=check_pinbar(df)
                for p in pins:
                    if sym in ULTIMO_INVIO and time.time()-ULTIMO_INVIO[sym]<60: continue
                    asset=sym.replace("=X","")
                    pin={"asset":asset,"dir":"CALL SU" if p['is_hammer'] else "PUT GIÙ","dir_full":"CALL HAMMER" if p['is_hammer'] else "PUT STAR","tipo":"HAMMER" if p['is_hammer'] else "STAR","entry":round((p['H']+p['L'])/2,5),"entry50":round((p['H']+p['L'])/2,5),"entry70":round((p['H']+p['L'])/2,5),"forza":p['forza'],"ora":ora_now(),"data":datetime.now().strftime("%d/%m %H:%M:%S"),"scad":"5 MIN"}
                    pins_live.insert(0,pin); pins_storico.insert(0,pin)
                    pins_live=pins_live[:30]; pins_storico=pins_storico[:100]
                    ULTIMO_INVIO[sym]=time.time()
                    log(f"SIGNALE {asset} {pin['dir']}")
                    if BOT_TOKEN and CHAT_ID:
                        try: requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage?chat_id={CHAT_ID}&text=💎 {asset} {pin['dir_full']} Forza {p['forza']}%", timeout=5)
                        except: pass
            except Exception as e:
                log(f"Loop err {sym}: {e}")
        time.sleep(12)

app=Flask(__name__)

@app.route('/')
def home():
    return """<!DOCTYPE html><html><head><meta name='viewport' content='width=device-width, initial-scale=1'><style>body{background:#0a0a0a;color:#fff;font-family:Arial;padding:12px}h2{color:#0f8}.card{background:#1e1e1e;padding:12px;margin:8px 0;border-radius:10px;display:flex;justify-content:space-between}.call{border-left:5px solid #0f8}.put{border-left:5px solid #f44}button{background:#0f8;color:#000;border:0;padding:14px;width:100%;border-radius:10px;font-weight:bold;font-size:17px;margin:6px 0}.tab{background:#222;color:#fff;border:1px solid #333;padding:10px 18px;border-radius:8px;margin-right:6px}.tab.active{background:#0f8;color:#000}small{color:#aaa}</style></head><body>
<h2>📡 SCANNER ALLARGATO V3</h2>
<button id="btn" onclick="attiva()">🔔 ATTIVA SUONO FORTE</button>
<div style="margin:10px 0"><button class="tab active" id="tLive" onclick="show('live')">LIVE</button><button class="tab" id="tStor" onclick="show('stor')">STORICO (<span id="numStor">0</span>)</button><a href="/debug" style="color:#0f8;margin-left:10px">DEBUG</a></div>
<div id="ora"></div><div id="listLive">Avvio... 30 sec</div><div id="listStor" style="display:none"></div>
<script>
let audioCtx=null,suono=false,last=0,tab='live';
function attiva(){audioCtx=new(window.AudioContext||window.webkitAudioContext)();suono=true;document.getElementById('btn').innerHTML='🔊 SUONO ATTIVO';document.getElementById('btn').style.background='#ffaa00';beep();}
function beep(){if(!audioCtx)return;for(let i=0;i<3;i++){setTimeout(()=>{let o=audioCtx.createOscillator(),g=audioCtx.createGain();o.type='square';o.frequency.value=880;g.gain.value=0.9;o.connect(g);g.connect(audioCtx.destination);o.start();g.gain.exponentialRampToValueAtTime(0.01,audioCtx.currentTime+0.4);o.stop(audioCtx.currentTime+0.4);},i*500);}}
function show(t){tab=t;document.getElementById('tLive').classList.toggle('active',t=='live');document.getElementById('tStor').classList.toggle('active',t=='stor');document.getElementById('listLive').style.display=t=='live'?'block':'none';document.getElementById('listStor').style.display=t=='stor'?'block':'none';}
function render(d,el){let h='';d.forEach(p=>{h+=`<div class='card ${p.dir.includes('CALL')?'call':'put'}'><div><b>${p.asset}</b> <small>${p.tipo} ${p.forza}%</small><br><small>${p.entry} | ${p.scad}</small><br><small>${p.data}</small></div><div style='text-align:right'><b style='color:${p.dir.includes('CALL')?'#0f8':'#f44'}'>${p.dir}</b></div></div>`;});if(d.length==0)h='<p style="color:#888;text-align:center">Nessun segnale...<br>controlla DEBUG</p>';document.getElementById(el).innerHTML=h;}
async function load(){let r1=await fetch('/api/pins');let live=await r1.json();let r2=await fetch('/api/storico');let stor=await r2.json();document.getElementById('ora').innerText=new Date().toLocaleTimeString()+' | Live:'+live.length+' Storico:'+stor.length;document.getElementById('numStor').innerText=stor.length;if(live.length>last&&last!=0&&suono){beep();if(navigator.vibrate)navigator.vibrate([300,100,300,100,600]);}last=live.length;render(live,'listLive');render(stor,'listStor');}load();setInterval(load,8000);
</script></body></html>"""

@app.route('/api/pins')
def api_pins(): return jsonify(pins_live)
@app.route('/api/storico')
def api_storico(): return jsonify(pins_storico)
@app.route('/debug')
def debug():
    html="<h3>LOGS ULTIMI 30</h3><br>"
    for l in LOGS[::-1]: html+=f"{l}<br>"
    html+=f"<br><br>Live:{len(pins_live)} Storico:{len(pins_storico)} CFFI:{CFFI}<br><br><a href='/'>torna</a>"
    return html

threading.Thread(target=scanner_loop, daemon=True).start()
if __name__=="__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT",10000)))
