from flask import Flask, jsonify
import yfinance as yf
from datetime import datetime, timedelta
import pytz
from curl_cffi import requests as cffi_requests

app = Flask(__name__)
session = cffi_requests.Session(impersonate="chrome")
ROMA = pytz.timezone("Europe/Rome")

OTC_1M = [
("EURUSD=X","EUR/USD OTC"),("GBPUSD=X","GBP/USD OTC"),("USDJPY=X","USD/JPY OTC"),
("AUDUSD=X","AUD/USD OTC"),("USDCAD=X","USD/CAD OTC"),("USDCHF=X","USD/CHF OTC"),
("NZDUSD=X","NZD/USD OTC"),("EURJPY=X","EUR/JPY OTC"),("EURGBP=X","EUR/GBP OTC"),
("EURCHF=X","EUR/CHF OTC"),("EURAUD=X","EUR/AUD OTC"),("EURCAD=X","EUR/CAD OTC"),
("EURNZD=X","EUR/NZD OTC"),("GBPJPY=X","GBP/JPY OTC"),("GBPCHF=X","GBP/CHF OTC"),
("GBPAUD=X","GBP/AUD OTC"),("GBPCAD=X","GBP/CAD OTC"),("GBPNZD=X","GBP/NZD OTC"),
("AUDJPY=X","AUD/JPY OTC"),("AUDCAD=X","AUD/CAD OTC"),("AUDCHF=X","AUD/CHF OTC"),
("AUDNZD=X","AUD/NZD OTC"),("CADJPY=X","CAD/JPY OTC"),("CHFJPY=X","CHF/JPY OTC"),
("NZDJPY=X","NZD/JPY OTC"),("CADCHF=X","CAD/CHF OTC"),("NZDCAD=X","NZD/CAD OTC"),
("EURCAD=X","EUR/CAD OTC"),("GBPCAD=X","GBP/CAD 2"),("AUDCAD=X","AUD/CAD 2"),
("GBPCHF=X","GBP/CHF 2"),("EURCHF=X","EUR/CHF 2"),
]

def get_df(sym):
    try:
        df=yf.Ticker(sym,session=session).history(period="1d",interval="1m")
        return df if len(df)>=100 else None
    except: return None

def scadenza_1m():
    now = datetime.now(ROMA)
    scad = now.replace(second=0, microsecond=0) + timedelta(minutes=1)
    return scad.strftime("%H:%M:%S"), (60 - now.second)

def pinbar_otc_largo(o,h,l,c, df):
    b=abs(c-o); r=h-l
    if r==0 or b==0: return None
    up=h-max(o,c); lo=min(o,c)-l
    lo_perc = lo/r; up_perc = up/r; body_perc = b/r

    # LARGO - PRIMA ERA 58% ORA 50%
    if body_perc > 0.42: return None # prima 35% ora 42%
    if lo_perc < 0.50 and up_perc < 0.50: return None # prima 58% ora 50%

    ema9 = df['Close'].ewm(span=9).mean().iloc[-1]
    ema21 = df['Close'].ewm(span=21).mean().iloc[-1]
    delta = df['Close'].diff()
    gain = delta.where(delta>0,0).ewm(span=7).mean()
    loss = -delta.where(delta<0,0).ewm(span=7).mean()
    rs = gain.iloc[-1] / (loss.iloc[-1] + 0.00001)
    rsi = 100 - (100/(1+rs))

    # CALL LARGO
    if lo_perc >= 0.50 and up_perc <= 0.32: # prima 0.25 ora 0.32
        ratio = lo/b if b>0 else 0
        if ratio < 1.3: return None # prima 1.6 ora 1.3
        if rsi > 70: return None # prima 65 ora 70 - più largo
        min10 = df['Low'].iloc[-11:-1].min()
        if l > min10 * 1.0015: return None # prima 1.0008 ora 1.0015
        return "CALL", int(lo_perc*100), round(ratio,1), int(rsi)

    # PUT LARGO
    if up_perc >= 0.50 and lo_perc <= 0.32:
        ratio = up/b if b>0 else 0
        if ratio < 1.3: return None
        if rsi < 30: return None # prima 35 ora 30
        max10 = df['High'].iloc[-11:-1].max()
        if h < max10 * 0.9985: return None # prima 0.9992 ora 0.9985
        return "PUT", int(up_perc*100), round(ratio,1), int(rsi)

    return None

def analizza():
    now = datetime.now(ROMA)
    sec = now.second
    if not (20 <= sec <= 58): # prima 25 ora 20 - inizia 5 sec prima
        return {"wait": True, "sec": sec, "signals": []}
    out=[]; scad_str, sec_rim = scadenza_1m()
    for ysym,label in OTC_1M:
        df=get_df(ysym)
        if df is None: continue
        r=df.iloc[-1]
        res=pinbar_otc_largo(r['Open'],r['High'],r['Low'],r['Close'], df)
        if not res: continue
        d, perc, ratio, rsi=res
        out.append({
            "coppia":label,"dir":d,"perc":perc,"ratio":ratio,"rsi":rsi,
            "scadenza":scad_str,"ora":now.strftime("%H:%M:%S"),
            "rimanenti": sec_rim
        })
    return {"wait": False, "sec": sec, "signals": out}

PAGE="""<!DOCTYPE html><html><head><meta charset=utf-8>
<meta name=viewport content='width=device-width, initial-scale=1'>
<title>V8.2 LARGO 1MIN</title>
<style>
*{box-sizing:border-box}
body{background:#000;color:#fff;font-family:Arial;margin:0;padding:0}
.header{background:#111;padding:14px;border-bottom:3px solid #ff0;position:sticky;top:0}
.header h2{margin:0;color:#ff0;font-size:20px}
.sub{color:#0f0;font-size:12px}
.container{padding:10px}
.card{border:3px solid #0f0;padding:16px;margin:12px 0;border-radius:14px;background:#151515}
.card.PUT{border-color:#ff3333}
.CALL{color:#0f0;font-size:28px;font-weight:bold}
.PUT{color:#ff3333;font-size:28px;font-weight:bold}
.timer{font-size:32px;font-weight:bold;color:#ff0;text-align:center;padding:10px;background:#222;border-radius:10px;margin:10px 0}
button{padding:16px;border:none;border-radius:12px;font-size:17px;font-weight:bold;margin:8px 0;width:100%}
#unlock{background:#0f0;color:#000}
#analyze{background:#222;color:#fff;border:1px solid #555}
.wait{background:#332200;border:2px solid #ff0;padding:15px;border-radius:12px;text-align:center;margin:10px 0}
</style></head><body>
<div class=header>
<h2>⚡ V8.2 LARGO - OTC 1 MIN - 50%+</h2>
<div class=sub>32 OTC - Pinbar 50%+ LARGO - Ratio 1.3x - RSI 30-70 - 20 sec start - Scad 1 MIN</div>
</div>
<div class=container>
<div id=status>🟡 V8.2 LARGO attivo - più segnali - aspetto :20 sec...</div>
<div id=timer class=timer>00</div>
<button id=unlock onclick=enableAudio()>🔊 ATTIVA AUDIO</button>
<button id=analyze onclick=load()>🔄 SCANSIONA ORA LARGO</button>
<div id=l></div>
</div>
<audio id=b src=https://cdn.pixabay.com/audio/2022/03/10/audio_1c8c9a0727.mp3 preload=auto></audio>
<script>
let audioEnabled=false;
function enableAudio(){let a=document.getElementById('b');a.play().then(()=>{a.pause();a.currentTime=0;audioEnabled=true;document.getElementById('unlock').innerText='✅ AUDIO ON';localStorage.setItem('audio','1');}).catch(e=>{});}
async function load(){
  try{
    let r=await fetch('/api/signals'); let data=await r.json();
    document.getElementById('timer').innerText=':'+String(data.sec).padStart(2,'0')+' sec';
    let c=document.getElementById('l');
    if(data.wait){
      document.getElementById('status').innerHTML='⏳ V8.2 LARGO - aspetto :20 sec - ora :'+data.sec+' - scan ogni 2s';
      if(data.sec < 20){c.innerHTML='<div class=wait>⏰ LARGO MODE<br>Segnale tra '+(20-data.sec)+' sec<br>Trova di più ora - poi stringiamo</div>';}
      return;
    }
    let d=data.signals;
    if(d.length==0){
      document.getElementById('status').innerHTML='✅ Scan LARGO a :'+data.sec+' - 32 OTC - 0 pinbar - riprovo 2s';
      c.innerHTML='<div style=color:#666;padding:15px;text-align:center>🔍 32 OTC LARGO scan a :'+data.sec+'<br>Nessuna ora - ma troverà di più di prima</div>';
    } else {
      document.getElementById('status').innerHTML='🔥🔥 '+d.length+' SEGNALI LARGO A :'+data.sec+' - '+d[0].rimanenti+' SEC!';
      c.innerHTML=''; d.forEach(s=>{
        let e=document.createElement('div'); e.className='card '+s.dir;
        e.innerHTML=`<b>${s.coppia} 1M LARGO</b> <span style=float:right;color:#ff0>${s.ora}</span><br><span class=${s.dir}>${s.dir} 1M</span> - ${s.perc}% ${s.ratio}x RSI ${s.rsi}<br><div style=margin-top:10px>Scade <b style=font-size:20px>${s.scadenza}</b><br><span style=color:#ff0;font-size:18px>⏰ ${s.rimanenti} SEC!</span><br><br><span style=background:#ff0;color:#000;padding:8px 15px;border-radius:8px;font-weight:bold>👉 ENTRA 1 MIN - LARGO</span></div>`;
        c.appendChild(e);
      });
      if(audioEnabled){document.getElementById('b').play().catch(()=>{}); if(navigator.vibrate) navigator.vibrate([600,100,600,100,600]);}
    }
    if(localStorage.getItem('audio')=='1'){audioEnabled=true;document.getElementById('unlock').innerText='✅ AUDIO ON';}
  }catch(e){document.getElementById('status').innerHTML='❌ Errore...';}
}
setInterval(load,2000); load();
</script></body></html>"""

@app.route('/')
def home(): return PAGE
@app.route('/api/signals')
def sig(): return jsonify(analizza())
if __name__ == "__main__":
    app.run(host='0.0.0.0', port=10000)
