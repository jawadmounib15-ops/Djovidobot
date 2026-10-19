# app.py - V69 FIX - 15M con PINBAR VERO + 30M scadenza
import os, time, threading
from flask import Flask, jsonify
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import pandas as pd
from curl_cffi import requests as cffi_requests

PAIRS = ["EURUSD=X","GBPUSD=X","EURGBP=X","USDJPY=X","AUDUSD=X","EURJPY=X","GBPJPY=X","AUDJPY=X","CHFJPY=X","USDCAD=X","USDCHF=X","EURCHF=X","CADJPY=X","CADCHF=X","AUDCHF=X","AUDCAD=X","GBPCAD=X"]
ITALY = ZoneInfo("Europe/Rome")
app = Flask(__name__)
pins_live, pins_storico, cooldown = [], [], {}

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
    try:
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?interval=15m&range=10d"
        r = cffi_requests.get(url, impersonate="chrome120", timeout=8)
        res=r.json()['chart']['result'][0]
        q=res['indicators']['quote'][0]
        # ORA PRENDIAMO OPEN - fondamentale!
        df=pd.DataFrame({'Open':q['open'],'High':q['high'],'Low':q['low'],'Close':q['close']}).dropna()
        return df.tail(400)
    except: return pd.DataFrame()

def scan():
    global pins_live, pins_storico
    for symbol in PAIRS:
        clean=symbol.replace("=X","")
        if clean in cooldown and time.time()-cooldown[clean] < 1800: continue # 30 min cooldown largo
        df=get_df_fast(symbol)
        if len(df)<100: continue
        try:
            df['e20']=df['Close'].ewm(span=20).mean()
            df['e50']=df['Close'].ewm(span=50).mean()
            df['e200']=df['Close'].ewm(span=200).mean()
            df['rsi']=rsi(df['Close'])
            df['atr']=atr(df,14); df['atr_ma']=df['atr'].rolling(50).mean()
            df['stoch_k'], df['stoch_d'] = stochastic(df)
            
            c=df.iloc[-2] # candela chiusa - NON l'ultima in formazione
            conf=df.iloc[-1]
            O,H,L,C = float(c['Open']), float(c['High']), float(c['Low']), float(c['Close'])
            total=H-L
            if total<0.00006: continue
            if c['atr'] < c['atr_ma']*0.50: continue # mercato morto
            if c['atr'] > c['atr_ma']*2.5: continue # troppo volatile
            
            corpo=abs(O-C); inf=min(O,C)-L; sup=H-max(O,C)
            forza=max(inf,sup)/total*100 if total>0 else 0
            
            # PINBAR LARGO 60-92%
            hammer=inf>=corpo*1.5 and inf>=total*0.45 and sup<=total*0.30 and corpo<=total*0.40
            star=sup>=corpo*1.5 and sup>=total*0.45 and inf<=total*0.30 and corpo<=total*0.40
            if not ((hammer or star) and 60<=forza<=92): continue
            
            price=C; rsi_v=float(c['rsi']); stoch_k=float(c['stoch_k'])
            e20=float(c['e20']); e50=float(c['e50']); e200=float(c['e200'])
            
            # FILTRI LARGHI
            if abs(price-e20)/price > 0.006: continue # entro 0.6% da EMA20
            if hammer and not (20<=rsi_v<=45 and stoch_k<=40): continue
            if star and not (55<=rsi_v<=80 and stoch_k>=60): continue
            if hammer and not (price>e200*0.998 or e20>e50*0.999): continue
            if star and not (price<e200*1.002 or e20<e50*1.001): continue
            
            # CONFERMA - chiusa sopra 50% pinbar
            if hammer and float(conf['Close']) < L+total*0.50: continue
            if star and float(conf['Close']) > H-total*0.50: continue
            
            signal="BUY" if hammer else "SELL"
            scadenza = (datetime.now(ITALY)+timedelta(minutes=30)).strftime("%H:%M:%S")
            
            pin={
                "asset":clean,
                "dir":"CALL SU 📈" if signal=="BUY" else "PUT GIÙ 📉",
                "signal":signal,
                "entry":round((H+L)/2,5),
                "price":round(price,5),
                "rsi":round(rsi_v),
                "sto":round(stoch_k),
                "forza":round(forza),
                "ema20":round(e20,5),
                "atr":round(float(c['atr']),5),
                "sl":round(L-total*0.2,5) if hammer else round(H+total*0.2,5),
                "tp":round(price+total*1.5,5) if hammer else round(price-total*1.5,5),
                "ora":datetime.now(ITALY).strftime("%H:%M:%S"),
                "data":datetime.now(ITALY).strftime("%d/%m %H:%M:%S"),
                "scadenza":scadenza,
                "scad_label":"30M",
                "id":f"{clean}{time.time()}"
            }
            pins_live.insert(0,pin); pins_storico.insert(0,pin)
            pins_live=pins_live[:30]; pins_storico=pins_storico[:1000]
            cooldown[clean]=time.time()
        except Exception as e:
            print(f"ERR {clean} {e}")
            continue

def loop():
    while True:
        try: scan()
        except: pass
        time.sleep(45)

@app.route('/')
def home():
    return """<!DOCTYPE html><html><head><meta name='viewport' content='width=device-width, initial-scale=1'><title>V69 FIX</title>
<style>body{background:#0a0a0a;color:#fff;font-family:Arial;padding:12px}h2{color:#00ff88}.card{background:#1e1e1e;padding:14px;margin:10px 0;border-radius:12px}.call{border-left:5px solid #00ff88}.put{border-left:5px solid #ff4444}button{padding:14px;width:100%;border-radius:10px;font-weight:bold;margin:6px 0;border:0}small{color:#aaa;font-size:12px}.det{color:#ffcc00;font-size:12px;margin-top:6px}</style></head><body>
<h2>📡 V69 FIX - 15M con PINBAR + DETTAGLI</h2>
<button id="btn" onclick="attiva()" style="background:#ff4444;color:#fff">🔴 ATTIVA SUONO</button>
<div style="margin:12px 0"><button onclick="show('live')" style="background:#00ff88;padding:10px 16px;border-radius:8px;border:0">LIVE</button>
<button onclick="show('stor')" style="background:#222;color:#fff;padding:10px 16px;border-radius:8px;border:1px solid #333">STORICO (<span id="numStor">0</span>)</button>
<button onclick="localStorage.clear();location.reload()" style="background:#ff4444;color:#fff;padding:10px;border-radius:8px;border:0">🗑️ PULISCI</button></div>
<div id="ora" style="color:#0f8"></div><div id="listLive"></div><div id="listStor" style="display:none"></div>
<script>
let audioCtx=null,suono=false,last=0;
let storico = JSON.parse(localStorage.getItem('v69_storico')||'[]');
let live = JSON.parse(localStorage.getItem('v69_live')||'[]');
function attiva(){audioCtx=new(window.AudioContext||window.webkitAudioContext)();suono=true;document.getElementById('btn').innerHTML='🟢 SUONO ATTIVO';document.getElementById('btn').style.background='#00ff88';document.getElementById('btn').style.color='#000';let o=audioCtx.createOscillator(),g=audioCtx.createGain();o.frequency.value=880;g.gain.value=0.8;o.connect(g);g.connect(audioCtx.destination);o.start();setTimeout(()=>o.stop(),400);}
function beep(){if(!suono||!audioCtx) return;if(audioCtx.state==='suspended') audioCtx.resume();for(let i=0;i<3;i++){setTimeout(()=>{let o=audioCtx.createOscillator(),g=audioCtx.createGain();o.type='square';o.frequency.value=900;g.gain.value=0.9;o.connect(g);g.connect(audioCtx.destination);o.start();setTimeout(()=>o.stop(),350);},i*500);}if(navigator.vibrate) navigator.vibrate([300,100,300]);}
function show(t){document.getElementById('listLive').style.display=t=='live'?'block':'none';document.getElementById('listStor').style.display=t=='stor'?'block':'none';}
function render(d,el){let h='';d.forEach(p=>{h+=`<div class='card ${p.signal=='BUY'?'call':'put'}'><div><b>${p.asset}</b> <small>RSI ${p.rsi} STO ${p.sto} Forza ${p.forza}%</small><br><small>Entry ${p.entry} | Price ${p.price} | ${p.data}</small><br><small class="det">EMA20 ${p.ema20} | ATR ${p.atr} | SL ${p.sl} | TP ${p.tp}</small><br><small style="color:#fa0">Scad ${p.scadenza} (${p.scad_label})</small></div><div style='text-align:right'><b style='color:${p.signal=='BUY'?'#0f8':'#f44'}'>${p.dir}</b></div></div>`;});if(d.length==0) h='<p style="color:#888;text-align:center">Nessun segnale - filtro attivo (largo 60%)</p>';document.getElementById(el).innerHTML=h;}
async function load(){let r1=await fetch('/api/pins');let l=await r1.json();let r2=await fetch('/api/storico');let s=await r2.json();l.forEach(p=>{if(!live.find(x=>x.id==p.id)) live.unshift(p);});s.forEach(p=>{if(!storico.find(x=>x.id==p.id)) storico.unshift(p);});live=live.slice(0,30);storico=storico.slice(0,500);localStorage.setItem('v69_live',JSON.stringify(live));localStorage.setItem('v69_storico',JSON.stringify(storico));document.getElementById('ora').innerText=new Date().toLocaleString('it-IT',{timeZone:'Europe/Rome'})+' | Storico: '+storico.length;document.getElementById('numStor').innerText=storico.length;if(live.length>last&&last!=0&&suono) beep();last=live.length;render(live,'listLive');render(storico,'listStor');}load();setInterval(load,8000);
</script></body></html>"""
@app.route('/api/pins')
def api_pins(): return jsonify(pins_live)
@app.route('/api/storico')
def api_storico(): return jsonify(pins_storico)

threading.Thread(target=loop, daemon=True).start()
if __name__=="__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT",10000)))
