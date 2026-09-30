# ANALYZER.PY V68 - ALLARME + SCADENZA 10 MIN
import yfinance as yf, pandas as pd
from flask import Flask, jsonify
from datetime import datetime
import pytz, os, time
from concurrent.futures import ThreadPoolExecutor, as_completed

app = Flask(__name__)
PAIRS = ["EURUSD=X","GBPUSD=X","USDJPY=X","AUDUSD=X","USDCAD=X","USDCHF=X","EURJPY=X","GBPJPY=X","EURGBP=X","EURCHF=X","AUDJPY=X","GBPCHF=X","EURAUD=X","GBPAUD=X","EURNZD=X","GBPNZD=X","NZDUSD=X","NZDCAD=X"]

def fix_df(df):
    if isinstance(df.columns, pd.MultiIndex): df.columns=df.columns.get_level_values(0)
    return df

def check_pair(sym):
    try:
        df_h = yf.download(sym, period="20d", interval="60m", progress=False)
        df_h = fix_df(df_h)
        if len(df_h) < 60: return None
        df_4h = df_h.resample('4h').agg({'Open':'first','High':'max','Low':'min','Close':'last'}).dropna()
        if len(df_4h) < 12: return None
        last_12 = df_4h.iloc[-12:]; rh=float(last_12['High'].max()); rl=float(last_12['Low'].min()); rs=rh-rl
        if rs==0: return None
        df_5 = yf.download(sym, period="5d", interval="5m", progress=False)
        df_5 = fix_df(df_5)
        if len(df_5)<20: return None
        last=df_5.iloc[-1]; o=float(last['Open']); h=float(last['High']); l=float(last['Low']); c=float(last['Close']); body=abs(c-o)
        up=h-max(o,c); down=min(o,c)-l
        if body==0 or max(up,down) < body*2.5 or body > (h-l)*0.45: return None
        if abs(c-rl)/rs < 0.12 and l < rl and c > rl and down > up:
            return {"pair":sym.replace("=X",""),"dir":"BUY","price":f"{c:.5f}","note":f"Rimbalzo su Low 4H - Forza {down/body:.1f}x"}
        if abs(c-rh)/rs < 0.12 and h > rh and c < rh and up > down:
            return {"pair":sym.replace("=X",""),"dir":"SELL","price":f"{c:.5f}","note":f"Rifiuto su High 4H - Forza {up/body:.1f}x"}
    except: return None

@app.route('/')
def home():
    return """<html><head><meta name="viewport" content="width=device-width,initial-scale=1"><title>V68 ALARM</title>
<style>body{background:#0a0a0a;color:#fff;font-family:Arial;text-align:center;padding:20px}
.btn{background:#00ff88;color:#000;border:none;padding:18px;border-radius:14px;font-weight:bold;font-size:20px;width:90%;max-width:360px;display:block;margin:12px auto}
.card{background:#1a1a1a;border-radius:14px;padding:16px;margin:12px auto;max-width:380px;text-align:left;border-left:5px solid #00ff88}
.exp{background:#00ff88;color:#000;font-weight:bold;padding:6px 10px;border-radius:8px;display:inline-block;margin-top:8px;font-size:16px}
.sell{border-left-color:#ff3b3b}
</style></head><body>
<h1>🔔 V68 ALARM + 10 MIN</h1>
<button class="btn" id="b1" onclick="attiva()">🔔 ATTIVA ALLARME FORTE</button>
<button class="btn" style="background:#222;color:#fff;border:1px solid #444" onclick="cerca()">🔍 SCAN ORA</button>
<p id="info">Attiva l'allarme poi lascia aperto...</p><div id="box"></div>
<audio id="s1" src="https://actions.google.com/sounds/v1/alarms/beep_short.ogg" preload="auto"></audio>
<audio id="s2" src="https://actions.google.com/sounds/v1/alarms/alarm_clock.ogg" preload="auto"></audio>
<script>
let ok=false;
let a1=document.getElementById('s1'), a2=document.getElementById('s2');
function attiva(){
 ok=true; 
 a1.play().then(()=>{a1.pause(); a1.currentTime=0;}).catch(()=>{});
 a2.play().then(()=>{a2.pause(); a2.currentTime=0;}).catch(()=>{});
 document.getElementById('b1').innerHTML='✅ ALLARME ATTIVO - LASCIA APERTO'; 
 document.getElementById('b1').style.background='#ffcc00';
 if(Notification && Notification.permission!='granted'){Notification.requestPermission();}
}
function suona(){
 if(!ok) return;
 a1.currentTime=0; a1.play(); 
 setTimeout(()=>{a2.currentTime=0; a2.play();}, 400);
 setTimeout(()=>{a1.currentTime=0; a1.play();}, 900);
 if(navigator.vibrate) navigator.vibrate([1000,300,1000,300,1000]);
 if(Notification && Notification.permission=='granted'){
   new Notification('🔔 SEGNALE V68!', {body:'Entra ora - Scadenza 10 MIN'});
 }
}
function cerca(){fetch('/api/scan').then(r=>r.json()).then(d=>{
 document.getElementById('info').innerText=d.time+' | Trovati: '+d.signals.length;
 let h=''; 
 if(d.signals.length>0){
   suona();
   d.signals.forEach(s=>{
     let cls=s.dir=='SELL'?'card sell':'card';
     h+=`<div class="${cls}"><b style="font-size:20px;color:${s.dir=='BUY'?'#00ff88':'#ff3b3b'}">${s.dir} ${s.pair}</b><br>${s.note}<br>Prezzo: ${s.price}<br><span class="exp">⏱️ SCADENZA: 10 MINUTI</span><br><span style="font-size:12px;color:#aaa">Entra SUBITO su Pocket</span></div>`;
   });
 }
 document.getElementById('box').innerHTML=h;
});}
setInterval(cerca,60000); window.onload=cerca;
</script></body></html>"""

@app.route('/api/scan')
def api():
    t0=time.time(); tz=pytz.timezone('Europe/Rome'); now=datetime.now(tz).strftime('%H:%M:%S IT')
    out=[]
    with ThreadPoolExecutor(max_workers=18) as ex:
        futs={ex.submit(check_pair,s):s for s in PAIRS}
        for f in as_completed(futs):
            r=f.result()
            if r: out.append(r)
    return jsonify({"signals":out,"time":now})

if __name__=="__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT",10000)))
