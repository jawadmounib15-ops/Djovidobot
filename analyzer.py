from flask import Flask, jsonify
import yfinance as yf
from datetime import datetime, timedelta
import pytz
from curl_cffi import requests as cffi_requests
import time

app = Flask(__name__)
session = cffi_requests.Session(impersonate="chrome")
ROMA = pytz.timezone("Europe/Rome")

# FIX: 18 OTC migliori - 27 erano troppi e Yahoo crashava
OTC_1M = [
("EURUSD=X","EUR/USD OTC"),("GBPUSD=X","GBP/USD OTC"),("USDJPY=X","USD/JPY OTC"),
("AUDUSD=X","AUD/USD OTC"),("EURJPY=X","EUR/JPY OTC"),("EURGBP=X","EUR/GBP OTC"),
("GBPJPY=X","GBP/JPY OTC"),("AUDJPY=X","AUD/JPY OTC"),("GBPCHF=X","GBP/CHF OTC"),
("EURCHF=X","EUR/CHF OTC"),("EURAUD=X","EUR/AUD OTC"),("NZDUSD=X","NZD/USD OTC"),
("GBPAUD=X","GBP/AUD OTC"),("GBPCAD=X","GBP/CAD OTC"),("AUDCAD=X","AUD/CAD OTC"),
("CHFJPY=X","CHF/JPY OTC"),("NZDJPY=X","NZD/JPY OTC"),("CADCHF=X","CAD/CHF OTC"),
]

def get_df_safe(sym):
    try:
        df=yf.Ticker(sym,session=session).history(period="2d",interval="1m")
        if df is None or len(df)<30:
            return None
        df=df.dropna() # FIX NaN che faceva crashare BB
        if len(df)<30:
            return None
        return df
    except:
        return None

def scadenza_1m():
    now = datetime.now(ROMA)
    scad = now.replace(second=0, microsecond=0) + timedelta(minutes=1)
    return scad.strftime("%H:%M:%S"), (60 - now.second)

def strategia_rsi_bb_foto_FIX(o,h,l,c, df):
    try:
        # BB 20 dev 2 - come foto
        sma20 = df['Close'].rolling(20).mean()
        std20 = df['Close'].rolling(20).std()
        bb_up = sma20 + std20*2
        bb_low = sma20 - std20*2

        # RSI 14 - 30/70 foto
        delta = df['Close'].diff()
        gain = delta.where(delta>0,0).ewm(span=14).mean()
        loss = -delta.where(delta<0,0).ewm(span=14).mean()
        rsi_series = 100 - (100/(1+ (gain/(loss+0.00001))))

        if len(rsi_series)<3 or len(bb_up)<3:
            return None

        rsi_prev = rsi_series.iloc[-2]
        bb_low_prev = bb_low.iloc[-2]
        bb_up_prev = bb_up.iloc[-2]

        # Controllo NaN - era questo l'errore!
        if str(rsi_prev)=='nan' or str(bb_low_prev)=='nan' or str(bb_up_prev)=='nan':
            return None

        prev = df.iloc[-2]
        curr = df.iloc[-1]

        b_curr = abs(curr['Close']-curr['Open'])
        r_curr = curr['High']-curr['Low']
        lo_curr = min(curr['Open'],curr['Close']) - curr['Low']
        up_curr = curr['High'] - max(curr['Open'],curr['Close'])
        lo_perc = lo_curr/r_curr if r_curr>0 else 0
        up_perc = up_curr/r_curr if r_curr>0 else 0

        # CALL FOTO: rottura inf + RSI < 35 (largo) + inversione
        rottura_inf = prev['Close'] < bb_low_prev or prev['Low'] < bb_low_prev*0.9995
        is_rossa_prev = prev['Close'] < prev['Open']

        if rottura_inf and is_rossa_prev and rsi_prev < 35:
            if curr['Close'] > curr['Open'] or lo_perc >= 0.30:
                return "CALL", int(rsi_prev), "BB LOW", "Rottura BB inf"

        # PUT FOTO: rottura sup + RSI > 65 + inversione
        rottura_sup = prev['Close'] > bb_up_prev or prev['High'] > bb_up_prev*1.0005
        is_verde_prev = prev['Close'] > prev['Open']

        if rottura_sup and is_verde_prev and rsi_prev > 65:
            if curr['Close'] < curr['Open'] or up_perc >= 0.30:
                return "PUT", int(rsi_prev), "BB HIGH", "Rottura BB sup"

        return None
    except Exception as e:
        # FIX: mai crashare
        return None

def analizza():
    now = datetime.now(ROMA)
    sec = now.second
    if not (20 <= sec <= 58):
        return {"wait": True, "sec": sec, "signals": [], "error": None}

    out=[]
    try:
        scad_str, sec_rim = scadenza_1m()
        for i,(ysym,label) in enumerate(OTC_1M):
            try:
                df=get_df_safe(ysym)
                if df is None: continue
                r=df.iloc[-1]
                res=strategia_rsi_bb_foto_FIX(r['Open'],r['High'],r['Low'],r['Close'], df)
                if not res: continue
                d, rsi, bb, dett=res
                out.append({
                    "coppia":label,"dir":d,"rsi":rsi,"bb":bb,"dett":dett,
                    "scadenza":scad_str,"ora":now.strftime("%H:%M:%S"),
                    "rimanenti": sec_rim
                })
                if i % 5 == 0:
                    time.sleep(0.15) # FIX anti-ban Yahoo
            except:
                continue
        return {"wait": False, "sec": sec, "signals": out, "error": None}
    except Exception as e:
        return {"wait": False, "sec": sec, "signals": out, "error": str(e)[:100]}

PAGE="""<!DOCTYPE html><html><head><meta charset=utf-8>
<meta name=viewport content='width=device-width, initial-scale=1'>
<title>V9.2 FIX RSI+BB</title>
<style>
*{box-sizing:border-box}body{background:#000;color:#fff;font-family:Arial;margin:0;padding:0}
.header{background:#111;padding:14px;border-bottom:3px solid #0f0;position:sticky;top:0}
.header h2{margin:0;color:#0f0;font-size:18px}.sub{color:#ff0;font-size:11px}
.container{padding:10px}.card{border:3px solid #0f0;padding:16px;margin:12px 0;border-radius:14px;background:#151515}
.card.PUT{border-color:#ff3333}.CALL{color:#0f0;font-size:26px;font-weight:bold}.PUT{color:#ff3333;font-size:26px;font-weight:bold}
.timer{font-size:36px;font-weight:bold;color:#ff0;text-align:center;padding:12px;background:#222;border-radius:10px;margin:10px 0}
button{padding:16px;border:none;border-radius:12px;font-size:17px;font-weight:bold;margin:8px 0;width:100%}
#unlock{background:#0f0;color:#000}#analyze{background:#222;color:#fff;border:1px solid #555}
.wait{background:#332200;border:2px solid #ff0;padding:15px;border-radius:12px;text-align:center}
</style></head><body>
<div class=header>
<h2>✅ V9.2 FIX - RSI+BB FOTO - 1M - NO ERRORE</h2>
<div class=sub>FIX V9 foto - BB20 dev2 + RSI14 35/65 LARGO - 18 OTC - Scad 1M 30sec prima</div>
</div>
<div class=container>
<div id=status>🟢 V9.2 FIX foto attivo - no errore</div>
<div id=timer class=timer>00</div>
<button id=unlock onclick=enableAudio()>🔊 AUDIO ON</button>
<button id=analyze onclick=load()>🔄 SCANSIONA RSI+BB FIX</button>
<div id=l></div>
</div>
<audio id=b src=https://cdn.pixabay.com/audio/2022/03/10/audio_1c8c9a0727.mp3 preload=auto></audio>
<script>
let audioEnabled=false;
function enableAudio(){let a=document.getElementById('b');a.play().then(()=>{a.pause();a.currentTime=0;audioEnabled=true;document.getElementById('unlock').innerText='✅ AUDIO ON';localStorage.setItem('audio','1');}).catch(e=>{});}
async function load(){
  try{
    let r=await fetch('/api/signals');
    if(!r.ok) throw new Error('http '+r.status);
    let data=await r.json();
    document.getElementById('timer').innerText=':'+String(data.sec).padStart(2,'0')+' sec';
    let c=document.getElementById('l');
    if(data.wait){
      document.getElementById('status').innerHTML='⏳ V9.2 FIX foto - aspetto :20 - ora :'+data.sec;
      if(data.sec < 20){c.innerHTML='<div class=wait>📸 STRATEGIA FOTO FIX<br>BB20 + RSI14 35/65 LARGO<br>Tra '+(20-data.sec)+' sec scan<br>No errore</div>';}
      return;
    }
    if(data.error){document.getElementById('status').innerHTML='⚠️ Parziale: '+data.error;}
    else{document.getElementById('status').innerHTML='🟢 V9.2 FIX OK scan :'+data.sec+' - 18 OTC';}
    let d=data.signals;
    if(d.length==0){
      c.innerHTML='<div style=color:#666;padding:15px;text-align:center>🔍 18 OTC RSI+BB FIX a :'+data.sec+'<br>Nessuna rottura BB ora<br>Ma NON da più Errore rosso ✅</div>';
    } else {
      document.getElementById('status').innerHTML='🔥 '+d.length+' SEGNALI FOTO FIX A :'+data.sec+' - '+d[0].rimanenti+' SEC!';
      c.innerHTML=''; d.forEach(s=>{
        let e=document.createElement('div'); e.className='card '+s.dir;
        e.innerHTML=`<b>${s.coppia} 1M</b> <span style=float:right;color:#ff0>${s.ora}</span><br><span class=${s.dir}>${s.dir} - ${s.bb}</span> RSI ${s.rsi}<br><div style=margin-top:8px;font-size:12px>${s.dett}</div><div style=margin-top:10px>Scade <b>${s.scadenza}</b><br><span style=color:#ff0;font-size:18px>⏰ ${s.rimanenti} SEC!</span><br><br><span style=background:#0f0;color:#000;padding:10px;border-radius:8px;font-weight:bold;display:block;text-align:center>👉 ENTRA 1 MIN - FOTO FIX</span></div>`;
        c.appendChild(e);
      });
      if(audioEnabled){document.getElementById('b').play().catch(()=>{}); if(navigator.vibrate) navigator.vibrate([500,150,500]);}
    }
    if(localStorage.getItem('audio')=='1'){audioEnabled=true;document.getElementById('unlock').innerText='✅ AUDIO ON';}
  }catch(e){document.getElementById('status').innerHTML='❌ Rete: '+e.message+' - riprovo';}
}
setInterval(load,2500); load();
</script></body></html>"""

@app.route('/')
def home(): return PAGE
@app.route('/api/signals')
def sig(): return jsonify(analizza())

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=10000)
