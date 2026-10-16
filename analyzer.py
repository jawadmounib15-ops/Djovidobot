import os, time, threading, json
from flask import Flask, jsonify
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import pandas as pd
import requests
from curl_cffi import requests as cffi_requests

TOKEN = os.getenv("TELEGRAM_TOKEN", os.getenv("TOKEN", ""))
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", os.getenv("CHAT_ID", ""))
PAIRS = ["EURUSD=X","GBPUSD=X","EURGBP=X","USDJPY=X","AUDUSD=X","EURJPY=X","GBPJPY=X","AUDJPY=X","CHFJPY=X","USDCAD=X","USDCHF=X","EURCHF=X","CADJPY=X","CADCHF=X","AUDCHF=X","AUDCAD=X","GBPCAD=X"]
ITALY = ZoneInfo("Europe/Rome")
app = Flask(__name__)
pins_live = []
pins_storico = []
cooldown = {}
LOG_FILE = "/tmp/v68.log"

def log(m):
    line = f"{datetime.now(ITALY).strftime('%H:%M:%S')} {m}"
    print(line, flush=True)
    try:
        with open(LOG_FILE, "a") as f: f.write(line+"\n")
    except: pass
def ora_now(): return datetime.now(ITALY).strftime("%H:%M:%S")
def data_now(): return datetime.now(ITALY).strftime("%d/%m %H:%M:%S")
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
            return df
        except: time.sleep(1)
    return pd.DataFrame()
def scan():
    global pins_live, pins_storico
    log(">>> SCAN LARGO+")
    count=0
    for symbol in PAIRS:
        if count>=8: break
        clean=symbol.replace("=X","")
        if clean in cooldown and time.time()-cooldown[clean] < 1200: continue
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
            if last['atr'] < last['atr_ma50']*0.40: continue
            if last['atr'] > last['atr_ma50']*3.0: continue
            tocco_e20=abs(price-float(last['e20']))/price < 0.01
            if abs(price-float(last['e200']))/price < 0.0002: continue
            signal=None
            if price>float(last['e200']) and tocco_e20 and 20<=rsi_v<=48 and stoch_k<35: signal="BUY"
            if price<float(last['e200']) and tocco_e20 and 52<=rsi_v<=80 and stoch_k>65: signal="SELL"
            if signal:
                scad_time = datetime.now(ITALY) + timedelta(minutes=15)
                pin = {"asset": clean, "dir": "CALL SU" if signal=="BUY" else "PUT GIÙ", "signal": signal, "entry": round(price,5), "rsi": round(rsi_v,0), "sto": round(stoch_k,0), "ora": ora_now(), "data": data_now(), "scadenza": scad_time.strftime("%H:%M:%S"), "scad_ts": scad_time.timestamp(), "scad": "15 MIN", "id": f"{clean}{time.time()}"}
                pins_live.insert(0,pin); pins_storico.insert(0,pin)
                pins_live=pins_live[:30]; pins_storico=pins_storico[:1000]
                send(f"🎯 V68 {signal} {clean} RSI {rsi_v:.0f}")
                cooldown[clean]=time.time(); count+=1
        except: pass
    log(f"FINE {count}")
def loop():
    try: os.remove(LOG_FILE)
    except: pass
    log("LOOP AVVIATO")
    while True:
        try: scan()
        except Exception as e: log(f"ERR {e}")
        time.sleep(40)

@app.route('/')
def home():
    return """<!DOCTYPE html><html><head><meta name='viewport' content='width=device-width, initial-scale=1'><title>V68 FIX</title><style>body{background:#0a0a0a;color:#fff;font-family:Arial;padding:12px}h2{color:#00ff88}.card{background:#1e1e1e;padding:12px;margin:8px 0;border-radius:10px;display:flex;justify-content:space-between}.call{border-left:5px solid #00ff88}.put{border-left:5px solid #ff4444}button{background:#00ff88;color:#000;border:0;padding:14px;width:100%;border-radius:10px;font-weight:bold;font-size:17px;margin:6px 0}.tab{background:#222;color:#fff;border:1px solid #333;padding:10px 18px;border-radius:8px;margin-right:6px}.tab.active{background:#00ff88;color:#000}small{color:#aaa}.scad{color:#ffaa00}</style></head><body>
<h2>📡 V68 FIX STORICO+SUONO</h2>
<button id="btn" onclick="attiva()" style="background:#ff4444;color:#fff">🔴 CLICCA QUI PER ATTIVARE SUONO</button>
<div style="margin:10px 0"><button class="tab active" id="tLive" onclick="show('live')">LIVE</button><button class="tab" id="tStor" onclick="show('stor')">STORICO PERMANENTE (<span id="numStor">0</span>)</button><button class="tab" onclick="clearStor()" style="background:#ff4444;color:#fff">🗑️ PULISCI</button></div>
<div id="ora"></div><div id="listLive"></div><div id="listStor" style="display:none"></div>
<script>
let audioCtx=null, suono=false, lastLiveCount=0;
// CARICA STORICO DA TELEFONO - NON SI CANCELLA MAI
let storicoLocale = JSON.parse(localStorage.getItem('v68_storico') || '[]');
let liveLocale = JSON.parse(localStorage.getItem('v68_live') || '[]');

function attiva(){
    audioCtx = new (window.AudioContext || window.webkitAudioContext)();
    suono = true;
    localStorage.setItem('v68_suono','1');
    document.getElementById('btn').innerHTML='🟢 SUONO ATTIVO - FORTE';
    document.getElementById('btn').style.background='#00ff88';
    document.getElementById('btn').style.color='#000';
    // TEST SUONO FORTE 3 BEEP
    for(let i=0;i<3;i++){
        setTimeout(()=>{let o=audioCtx.createOscillator(),g=audioCtx.createGain();o.type='square';o.frequency.value=880;g.gain.value=0.9;o.connect(g);g.connect(audioCtx.destination);o.start();g.gain.exponentialRampToValueAtTime(0.01,audioCtx.currentTime+0.5);o.stop(audioCtx.currentTime+0.5);},i*600);
    }
    if(navigator.vibrate) navigator.vibrate([300,100,300]);
}
function beepForte(){
    if(!suono ||!audioCtx) return;
    if(audioCtx.state==='suspended') audioCtx.resume();
    for(let i=0;i<4;i++){
        setTimeout(()=>{
            let o=audioCtx.createOscillator(),g=audioCtx.createGain();
            o.type='square';o.frequency.value=i%2==0?880:1200;g.gain.value=1;
            o.connect(g);g.connect(audioCtx.destination);
            o.start();g.gain.exponentialRampToValueAtTime(0.01,audioCtx.currentTime+0.6);o.stop(audioCtx.currentTime+0.6);
        },i*400);
    }
    if(navigator.vibrate) navigator.vibrate([400,100,400,100,800]);
}
function show(t){
    document.getElementById('tLive').classList.toggle('active',t=='live');
    document.getElementById('tStor').classList.toggle('active',t=='stor');
    document.getElementById('listLive').style.display=t=='live'?'block':'none';
    document.getElementById('listStor').style.display=t=='stor'?'block':'none';
}
function clearStor(){
    if(confirm('Cancellare tutto lo storico?')){
        storicoLocale=[];liveLocale=[];
        localStorage.removeItem('v68_storico');localStorage.removeItem('v68_live');
        location.reload();
    }
}
function render(d,el){
    let h='';let now=Date.now()/1000;
    d.forEach(p=>{
        let scaduta=p.scad_ts&&now>p.scad_ts?'<span style="color:#f44">SCADUTO</span>':'<span class="scad">Scad '+p.scadenza+'</span>';
        h+=`<div class='card ${p.signal=='BUY'?'call':'put'}'><div><b>${p.asset}</b> <small>RSI ${p.rsi} STO ${p.sto}</small><br><small>Entry ${p.entry} | ${p.data} IT</small></div><div style='text-align:right'><b style='color:${p.signal=='BUY'?'#00ff88':'#ff4444'}'>${p.dir}</b><br>${scaduta}</div></div>`;
    });
    if(d.length==0) h='<p style="color:#888;text-align:center">In attesa... storico salvato sul telefono</p>';
    document.getElementById(el).innerHTML=h;
}
async function load(){
    try{
        let r1=await fetch('/api/pins');let live=await r1.json();
        let r2=await fetch('/api/storico');let stor=await r2.json();
        // UNISCI CON LOCALE - NON PERDE MAI
        live.forEach(p=>{if(!liveLocale.find(x=>x.id===p.id)) liveLocale.unshift(p);});
        stor.forEach(p=>{if(!storicoLocale.find(x=>x.id===p.id)) storicoLocale.unshift(p);});
        liveLocale=liveLocale.slice(0,50);
        storicoLocale=storicoLocale.slice(0,1000);
        localStorage.setItem('v68_live', JSON.stringify(liveLocale));
        localStorage.setItem('v68_storico', JSON.stringify(storicoLocale));

        let it=new Date().toLocaleString('it-IT',{timeZone:'Europe/Rome'});
        document.getElementById('ora').innerText=it+' | Storico telefono: '+storicoLocale.length;
        document.getElementById('numStor').innerText=storicoLocale.length;

        // SUONA SE NUOVO
        if(liveLocale.length>lastLiveCount && lastLiveCount!=0 && suono){
            beepForte();
        }
        lastLiveCount=liveLocale.length;
        render(liveLocale,'listLive');
        render(storicoLocale,'listStor');
    }catch(e){}
}
// AUTO-ATTIVA SUONO SE GIA ATTIVATO PRIMA
if(localStorage.getItem('v68_suono')==='1'){
    setTimeout(()=>{document.getElementById('btn').innerHTML='🟡 CLICCA ANCORA PER SUONO (browser lo blocca)';},1000);
}
load();setInterval(load,5000);
</script></body></html>"""

@app.route('/api/pins')
def api_pins(): return jsonify(pins_live)
@app.route('/api/storico')
def api_storico(): return jsonify(pins_storico)
@app.route('/debug')
def debug():
    try:
        with open(LOG_FILE, "r") as f: lines=f.readlines()[-60:]
    except: lines=["log vuoto"]
    h="<b>LOG</b><br>"
    for l in lines[::-1]: h+=f"{l}<br>"
    return h
threading.Thread(target=loop, daemon=True).start()
if __name__=="__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT",10000)))
