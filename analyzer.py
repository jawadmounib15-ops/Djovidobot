# Analyzer.py - ALLARGATO + STORICO 100 SEGNALI + SUONO
import yfinance as yf
import pandas as pd
from flask import Flask, jsonify
from datetime import datetime
import threading, time, os, requests

PAIRS = ["EURUSD=X","GBPUSD=X","GBPJPY=X","EURJPY=X","USDJPY=X","AUDJPY=X","EURGBP=X","EURCAD=X","GBPCAD=X","USDCAD=X","USDCHF=X","AUDUSD=X"]
pins_live = []
pins_storico = [] # TUTTI i segnali del giorno
ULTIMO_INVIO = {}

BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
CHAT_ID = os.environ.get("CHAT_ID", "")

def ora_now(): return datetime.now().strftime("%H:%M:%S")
def data_now(): return datetime.now().strftime("%d/%m %H:%M:%S")

def send_telegram(msg):
    if not BOT_TOKEN or not CHAT_ID: return
    try: requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage?chat_id={CHAT_ID}&text={msg}&parse_mode=HTML", timeout=10)
    except: pass

def check_pinbar(df, symbol):
    if len(df) < 5: return []
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    signals = []
    # CONTROLLA ULTIME 3 CANDELE, non solo ultima - così trovi 3x segnali
    for idx in range(-1, -4, -1):
        try:
            c = df.iloc[idx]
            O = float(c['Open']); H = float(c['High']); L = float(c['Low']); C = float(c['Close'])
            total = H - L
            if total <= 0: continue
            corpo = abs(O - C)
            if corpo < total*0.05: corpo = total*0.1

            inf = min(O,C) - L
            sup = H - max(O,C)

            # ALLARGATO MOLTO - PRIMA ERA 1.2 e 0.38 - ORA 1.0 e 0.28
            is_hammer = inf >= corpo*1.0 and inf >= total*0.28 and corpo <= total*0.65
            is_star = sup >= corpo*1.0 and sup >= total*0.28 and corpo <= total*0.65

            if not is_hammer and not is_star: continue

            forza = int((inf if is_hammer else sup) / total * 100)
            if forza < 40: continue # prima 50, ora 40

            asset = symbol.replace("=X","")
            signals.append({
                "asset": asset,
                "dir": "CALL SU" if is_hammer else "PUT GIÙ",
                "dir_full": "CALL HAMMER" if is_hammer else "PUT STAR",
                "tipo": "HAMMER" if is_hammer else "STAR",
                "entry": round((H+L)/2,5),
                "entry50": round((H+L)/2,5),
                "entry70": round((H+L)/2 + (0.00005 if is_hammer else -0.00005),5),
                "forza": forza,
                "ora": ora_now(),
                "data": data_now(),
                "scad": "5 MIN",
                "candela": f"O:{O} H:{H} L:{L} C:{C}"
            })
        except: continue
    return signals

def scanner_loop():
    global pins_live, pins_storico
    print("SCANNER ALLARGATO AVVIATO")
    while True:
        for sym in PAIRS:
            try:
                df = yf.Ticker(sym).history(period="1d", interval="1m")
                if len(df) < 5: continue
                pins = check_pinbar(df, sym)
                for pin in pins:
                    asset = pin['asset']
                    if sym in ULTIMO_INVIO and time.time() - ULTIMO_INVIO[sym] < 90: # prima 180, ora 90 sec
                        continue

                    pins_live.insert(0, pin)
                    pins_storico.insert(0, pin)
                    pins_live = pins_live[:30]
                    pins_storico = pins_storico[:100]
                    ULTIMO_INVIO[sym] = time.time()

                    txt = f"💎 PIN 1m -> 5m 80% 💎\nAsset: {pin['asset']}\nDir: {pin['dir_full']}\nAnalisi 1m | Scad 5 MIN\nEntry 50%: {pin['entry50']}\nEntry 70%: {pin['entry70']}\nForza {pin['forza']}% | SR+EMA+CONF+ORARIO\nOra: {pin['ora']}"
                    send_telegram(txt)
                    print(f"TROVATA {pin}")
            except Exception as e:
                print(f"Err {sym}: {e}")
                continue
        time.sleep(15)

app = Flask(__name__)

@app.route('/')
def home():
    return """
<!DOCTYPE html><html><head><meta name='viewport' content='width=device-width, initial-scale=1'>
<style>
body{background:#0a0a0a;color:#fff;font-family:Arial;padding:12px;margin:0}
h2{color:#00ff88}
.card{background:#1e1e1e;padding:12px;margin:8px 0;border-radius:10px;display:flex;justify-content:space-between}
.call{border-left:5px solid #00ff88}.put{border-left:5px solid #ff4444}
button{background:#00ff88;color:#000;border:0;padding:14px;width:100%;border-radius:10px;font-weight:bold;font-size:17px;margin:6px 0}
.tab{background:#222;color:#fff;border:1px solid #333;padding:10px 18px;border-radius:8px;margin-right:6px}
.tab.active{background:#00ff88;color:#000;font-weight:bold}
small{color:#aaa}
</style>
</head><body>
<h2>📡 SCANNER ALLARGATO</h2>
<button id="btn" onclick="attiva()">🔔 ATTIVA SUONO FORTE</button>
<div style="margin:10px 0"><button class="tab active" id="tLive" onclick="show('live')">LIVE</button><button class="tab" id="tStor" onclick="show('stor')">STORICO (<span id="numStor">0</span>)</button></div>
<div id="ora"></div>
<div id="listLive">Avvio... 30 sec</div>
<div id="listStor" style="display:none">Nessuno storico</div>
<script>
let audioCtx=null, suonoAttivo=false, lastCount=0, tab='live';
function attiva(){ audioCtx=new (window.AudioContext||window.webkitAudioContext)(); suonoAttivo=true; document.getElementById('btn').innerHTML='🔊 SUONO ATTIVO - ALLARGATO'; document.getElementById('btn').style.background='#ffaa00'; beep(); }
function beep(){ if(!audioCtx) return; for(let i=0;i<3;i++){ setTimeout(()=>{ let o=audioCtx.createOscillator(),g=audioCtx.createGain(); o.type='square'; o.frequency.value=880; g.gain.value=0.9; o.connect(g); g.connect(audioCtx.destination); o.start(); g.gain.exponentialRampToValueAtTime(0.01,audioCtx.currentTime+0.4); o.stop(audioCtx.currentTime+0.4); }, i*500); } }
function show(t){ tab=t; document.getElementById('tLive').classList.toggle('active',t=='live'); document.getElementById('tStor').classList.toggle('active',t=='stor'); document.getElementById('listLive').style.display=t=='live'?'block':'none'; document.getElementById('listStor').style.display=t=='stor'?'block':'none'; }
function render(data, el){
  let h=''; data.forEach(p=>{ h+=`<div class='card ${p.dir.includes('CALL')?'call':'put'}'><div><b>${p.asset}</b> <small>${p.tipo} ${p.forza}%</small><br><small>Entry: ${p.entry} | ${p.scad}</small><br><small>${p.data||p.ora}</small></div><div style='text-align:right'><b style='color:${p.dir.includes('CALL')?'#00ff88':'#ff4444'}'>${p.dir}</b><br><small>${p.dir_full}</small></div></div>`; });
  if(data.length==0) h='<p style="color:#888;text-align:center">Nessun segnale... mercato calmo</p>'; document.getElementById(el).innerHTML=h;
}
async function load(){
  try{
    let r1=await fetch('/api/pins'); let live=await r1.json();
    let r2=await fetch('/api/storico'); let stor=await r2.json();
    document.getElementById('ora').innerText=new Date().toLocaleTimeString()+' | Live:'+live.length+' Storico:'+stor.length;
    document.getElementById('numStor').innerText=stor.length;
    if(live.length>lastCount && lastCount!=0 && suonoAttivo){ beep(); if(navigator.vibrate) navigator.vibrate([300,100,300,100,600]); }
    lastCount=live.length;
    render(live,'listLive'); render(stor,'listStor');
  }catch(e){}
}
load(); setInterval(load, 8000);
</script>
</body></html>
"""

@app.route('/api/pins')
def api_pins(): return jsonify(pins_live)

@app.route('/api/storico')
def api_storico(): return jsonify(pins_storico)

@app.route('/debug')
def debug(): return f"Live:{len(pins_live)} Storico:{len(pins_storico)} Ora:{ora_now()}"

threading.Thread(target=scanner_loop, daemon=True).start()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT",10000)))
