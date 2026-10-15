# Analyzer.py V4 - BYPASS YAHOO DIRETTO - FUNZIONA SU RENDER
import pandas as pd
from flask import Flask, jsonify
from datetime import datetime
import threading, time, os, requests
from curl_cffi import requests as cffi_requests

PAIRS = ["EURUSD=X","GBPUSD=X","GBPJPY=X","EURJPY=X","USDJPY=X","AUDJPY=X","EURGBP=X","EURCAD=X","GBPCAD=X","USDCAD=X","USDCHF=X","AUDUSD=X"]
pins_live = []
pins_storico = []
ULTIMO_INVIO = {}
LOGS = []

BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
CHAT_ID = os.environ.get("CHAT_ID", "")

def log(m):
    print(m)
    LOGS.append(f"{datetime.now().strftime('%H:%M:%S')} {m}")
    if len(LOGS)>40: LOGS.pop(0)

def ora_now(): return datetime.now().strftime("%H:%M:%S")

def get_candles_yahoo_direct(symbol):
    """Prende candele diretto da Yahoo API - bypassa blocco Render"""
    try:
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?interval=1m&range=1d&includePrePost=false"
        sess = cffi_requests.Session(impersonate="chrome120", timeout=20)
        r = sess.get(url, headers={"User-Agent":"Mozilla/5.0"})
        if r.status_code!= 200:
            log(f"{symbol} HTTP {r.status_code}")
            return pd.DataFrame()
        data = r.json()
        result = data['chart']['result'][0]
        timestamps = result['timestamp']
        quote = result['indicators']['quote'][0]

        df = pd.DataFrame({
            'Open': quote['open'],
            'High': quote['high'],
            'Low': quote['low'],
            'Close': quote['close']
        })
        df = df.dropna()
        if len(df) < 5:
            log(f"{symbol} poche candele: {len(df)}")
            return pd.DataFrame()
        log(f"{symbol} OK diretto: {len(df)} candele, ultima {df.iloc[-1]['Close']}")
        return df
    except Exception as e:
        log(f"{symbol} diretto FAIL: {e}")
        return pd.DataFrame()

def check_pinbar(df):
    if len(df)<5: return []
    sigs=[]
    for idx in range(-1,-4,-1):
        try:
            if abs(idx) > len(df): continue
            c=df.iloc[idx]
            O=float(c['Open']); H=float(c['High']); L=float(c['Low']); C=float(c['Close'])
            total=H-L
            if total<=0 or total<0.00001: continue
            corpo=abs(O-C) or total*0.1
            inf=min(O,C)-L; sup=H-max(O,C)
            # ULTRA ALLARGATO 25%
            is_hammer=inf>=total*0.30
            is_star=sup>=total*0.30
            if not is_hammer and not is_star: continue
            forza=int((inf if is_hammer else sup)/total*100)
            if forza<20: continue
            sigs.append({"forza":forza,"is_hammer":is_hammer,"H":H,"L":L})
        except: continue
    return sigs

def scanner_loop():
    global pins_live, pins_storico
    log("SCANNER V4 AVVIATO - METODO DIRETTO")
    while True:
        for sym in PAIRS:
            try:
                df=get_candles_yahoo_direct(sym)
                if len(df)==0:
                    time.sleep(1)
                    continue
                pins=check_pinbar(df)
                for p in pins:
                    if sym in ULTIMO_INVIO and time.time()-ULTIMO_INVIO[sym]<45: continue
                    asset=sym.replace("=X","")
                    pin={"asset":asset,"dir":"CALL SU" if p['is_hammer'] else "PUT GIÙ","dir_full":"CALL HAMMER" if p['is_hammer'] else "PUT STAR","tipo":"HAMMER" if p['is_hammer'] else "STAR","entry":round((p['H']+p['L'])/2,5),"entry50":round((p['H']+p['L'])/2,5),"entry70":round((p['H']+p['L'])/2,5),"forza":p['forza'],"ora":ora_now(),"data":datetime.now().strftime("%d/%m %H:%M:%S"),"scad":"5 MIN"}
                    pins_live.insert(0,pin); pins_storico.insert(0,pin)
                    pins_live=pins_live[:30]; pins_storico=pins_storico[:100]
                    ULTIMO_INVIO[sym]=time.time()
                    log(f"*** SIGNALE {asset} {pin['dir']} {p['forza']}% ***")
            except Exception as e:
                log(f"Loop err {sym}: {e}")
            time.sleep(2) # pausa tra pair per non far bannare
        time.sleep(10)

app=Flask(__name__)

@app.route('/')
def home():
    return """<!DOCTYPE html><html><head><meta name='viewport' content='width=device-width, initial-scale=1'><style>body{background:#0a0a0a;color:#fff;font-family:Arial;padding:12px}h2{color:#0f8}.card{background:#1e1e1e;padding:12px;margin:8px 0;border-radius:10px;display:flex;justify-content:space-between}.call{border-left:5px solid #0f8}.put{border-left:5px solid #f44}button{background:#0f8;color:#000;border:0;padding:14px;width:100%;border-radius:10px;font-weight:bold;font-size:17px;margin:6px 0}.tab{background:#222;color:#fff;border:1px solid #333;padding:10px 18px;border-radius:8px;margin-right:6px}.tab.active{background:#0f8;color:#000}small{color:#aaa}</style></head><body>
<h2>📡 SCANNER V4 DIRETTO</h2><button id="btn" onclick="attiva()">🔔 ATTIVA SUONO FORTE</button><div style="margin:10px 0"><button class="tab active" id="tLive" onclick="show('live')">LIVE</button><button class="tab" id="tStor" onclick="show('stor')">STORICO (<span id="numStor">0</span>)</button><a href="/debug" style="color:#0f8;margin-left:10px">DEBUG</a></div><div id="ora"></div><div id="listLive">Avvio V4... 20 sec</div><div id="listStor" style="display:none"></div>
<script>
let audioCtx=null,suono=false,last=0;function attiva(){audioCtx=new(window.AudioContext||window.webkitAudioContext)();suono=true;document.getElementById('btn').innerHTML='🔊 SUONO ATTIVO';document.getElementById('btn').style.background='#ffaa00';beep();}function beep(){if(!audioCtx)return;for(let i=0;i<3;i++){setTimeout(()=>{let o=audioCtx.createOscillator(),g=audioCtx.createGain();o.type='square';o.frequency.value=880;g.gain.value=0.9;o.connect(g);g.connect(audioCtx.destination);o.start();g.gain.exponentialRampToValueAtTime(0.01,audioCtx.currentTime+0.4);o.stop(audioCtx.currentTime+0.4);},i*500);}}function show(t){document.getElementById('tLive').classList.toggle('active',t=='live');document.getElementById('tStor').classList.toggle('active',t=='stor');document.getElementById('listLive').style.display=t=='live'?'block':'none';document.getElementById('listStor').style.display=t=='stor'?'block':'none';}function render(d,el){let h='';d.forEach(p=>{h+=`<div class='card ${p.dir.includes('CALL')?'call':'put'}'><div><b>${p.asset}</b> <small>${p.tipo} ${p.forza}%</small><br><small>${p.entry} | ${p.scad}</small><br><small>${p.data}</small></div><div style='text-align:right'><b style='color:${p.dir.includes('CALL')?'#0f8':'#f44'}'>${p.dir}</b></div></div>`;});if(d.length==0)h='<p style="color:#888;text-align:center">Scanner V4 attivo...<br>aspetto candele</p>';document.getElementById(el).innerHTML=h;}async function load(){let r1=await fetch('/api/pins');let live=await r1.json();let r2=await fetch('/api/storico');let stor=await r2.json();document.getElementById('ora').innerText=new Date().toLocaleTimeString()+' | Live:'+live.length+' Storico:'+stor.length;document.getElementById('numStor').innerText=stor.length;if(live.length>last&&last!=0&&suono){beep();if(navigator.vibrate)navigator.vibrate([300,100,300,100,600]);}last=live.length;render(live,'listLive');render(stor,'listStor');}load();setInterval(load,7000);
</script></body></html>"""

@app.route('/api/pins')
def api_pins(): return jsonify(pins_live)
@app.route('/api/storico')
def api_storico(): return jsonify(pins_storico)
@app.route('/debug')
def debug():
    html="<h3>LOGS (ultimi 40)</h3>"
    for l in LOGS[::-1]: html+=f"{l}<br>"
    html+=f"<br>Live:{len(pins_live)} Storico:{len(pins_storico)}<br><a href='/'>torna</a>"
    return html

threading.Thread(target=scanner_loop, daemon=True).start()
if __name__=="__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT",10000)))
