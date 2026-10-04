from flask import Flask, jsonify
import yfinance as yf
from datetime import datetime, timedelta
import pytz
from curl_cffi import requests as cffi_requests
import time

app = Flask(__name__)
session = cffi_requests.Session(impersonate="chrome")
ROMA = pytz.timezone("Europe/Rome")

# STORICO GLOBALE - rimane fino a restart Render
STORICO = []

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
        if df is None or len(df)<30: return None
        df=df.dropna()
        return df if len(df)>=30 else None
    except: return None

def scadenza_1m():
    now = datetime.now(ROMA)
    scad = now.replace(second=0, microsecond=0) + timedelta(minutes=1)
    rimanenti = 60 - now.second
    return scad.strftime("%H:%M:%S"), rimanenti, scad

def rsi_bb_largo(o,h,l,c, df):
    try:
        sma20 = df['Close'].rolling(20).mean()
        std20 = df['Close'].rolling(20).std()
        bb_up = sma20 + std20*2
        bb_low = sma20 - std20*2
        delta = df['Close'].diff()
        gain = delta.where(delta>0,0).ewm(span=14).mean()
        loss = -delta.where(delta<0,0).ewm(span=14).mean()
        rsi_series = 100 - (100/(1+ (gain/(loss+0.00001))))

        if len(rsi_series)<3: return None
        rsi_prev = rsi_series.iloc[-2]
        bb_low_prev = bb_low.iloc[-2]
        bb_up_prev = bb_up.iloc[-2]
        if str(rsi_prev)=='nan' or str(bb_low_prev)=='nan': return None

        prev = df.iloc[-2]
        curr = df.iloc[-1]

        vicino_low = prev['Low'] <= bb_low_prev * 1.0008
        vicino_high = prev['High'] >= bb_up_prev * 0.9992

        if vicino_low and rsi_prev < 42:
            if curr['Close'] > prev['Close']*0.9998:
                return "CALL", int(rsi_prev), "BB LOW", int((bb_low_prev-prev['Low'])*10000)

        if vicino_high and rsi_prev > 58:
            if curr['Close'] < prev['Close']*1.0002:
                return "PUT", int(rsi_prev), "BB HIGH", int((prev['High']-bb_up_prev)*10000)

        return None
    except:
        return None

def analizza():
    global STORICO
    now = datetime.now(ROMA)
    sec = now.second
    # AVVISO PRIMA DI 30 SEC - come vuoi tu: da :15 a :58
    if not (15 <= sec <= 58):
        return {"wait": True, "sec": sec, "signals": [], "storico": STORICO[-20:][::-1]}

    out=[]
    try:
        scad_str, rimanenti, scad_dt = scadenza_1m()
        for i,(ysym,label) in enumerate(OTC_1M):
            try:
                df=get_df_safe(ysym)
                if df is None: continue
                r=df.iloc[-1]
                res=rsi_bb_largo(r['Open'],r['High'],r['Low'],r['Close'], df)
                if not res: continue
                d, rsi, bb, pip=res
                segnale = {
                    "coppia":label,"dir":d,"rsi":rsi,"bb":bb,"pip":pip,
                    "scadenza":scad_str,"ora":now.strftime("%H:%M:%S"),
                    "rimanenti": rimanenti,
                    "scadenza_full": scad_dt.strftime("%H:%M:%S"),
                    "data": now.strftime("%d/%m %H:%M:%S")
                }
                out.append(segnale)

                # AGGIUNGI A STORICO - evita duplicati stesso minuto stessa coppia
                gia = [s for s in STORICO if s['coppia']==label and s['ora'][:5]==now.strftime("%H:%M")]
                if not gia:
                    STORICO.append(segnale)
                    if len(STORICO)>100:
                        STORICO = STORICO[-100:]

                if i % 5 == 0: time.sleep(0.12)
            except: continue
        return {"wait": False, "sec": sec, "signals": out, "storico": STORICO[-20:][::-1]}
    except Exception as e:
        return {"wait": False, "sec": sec, "signals": out, "storico": STORICO[-20:][::-1], "error": str(e)[:80]}

PAGE="""<!DOCTYPE html><html><head><meta charset=utf-8>
<meta name=viewport content='width=device-width, initial-scale=1'>
<title>V9.4 STORICO + SCADENZA</title>
<style>
*{box-sizing:border-box}body{background:#000;color:#fff;font-family:Arial;margin:0;padding:0}
.header{background:#111;padding:14px;border-bottom:3px solid #0f0;position:sticky;top:0;z-index:10}
.header h2{margin:0;color:#0f0;font-size:18px}.sub{color:#ff0;font-size:11px}
.container{padding:10px}.card{border:3px solid #0f0;padding:14px;margin:12px 0;border-radius:14px;background:#151515}
.card.PUT{border-color:#ff3333}.CALL{color:#0f0;font-size:24px;font-weight:bold}.PUT{color:#ff3333;font-size:24px;font-weight:bold}
.timer{font-size:34px;font-weight:bold;color:#ff0;text-align:center;padding:10px;background:#222;border-radius:10px;margin:10px 0}
.countdown{font-size:22px;color:#0f0;text-align:center;font-weight:bold}
button{padding:14px;border:none;border-radius:12px;font-size:16px;font-weight:bold;margin:6px 0;width:100%}
#unlock{background:#0f0;color:#000}#analyze{background:#222;color:#fff;border:1px solid #555}
.wait{background:#332200;border:2px solid #ff0;padding:12px;border-radius:12px;text-align:center;margin:8px 0}
.storico{background:#111;border:1px solid #444;border-radius:12px;padding:10px;margin:15px 0}
.storico h3{margin:5px 0;color:#ff0;font-size:14px}
.row{display:flex;justify-content:space-between;font-size:12px;padding:6px 0;border-bottom:1px solid #222}
.row.CALL b{color:#0f0}.row.PUT b{color:#ff3333}
</style></head><body>
<div class=header>
<h2>✅ V9.4 STORICO + SCADENZA + 30SEC</h2>
<div class=sub>STORICO 20 ultimi + Scadenza 1M + Avviso a 30 sec + Audio + Vibrazione</div>
</div>
<div class=container>
<div id=status>🟢 V9.4 Storico attivo</div>
<div id=timer class=timer>00</div>
<div id=countdown class=countdown></div>
<button id=unlock onclick=enableAudio()>🔊 ATTIVA AUDIO - AVVISO 30 SEC</button>
<button id=analyze onclick=load()>🔄 SCANSIONA ORA</button>
<div id=l></div>

<div class=storico>
<h3>📜 STORICO ULTIMI 20 SEGNALI</h3>
<div id=storico>Carico storico...</div>
</div>
</div>
<audio id=b src=https://cdn.pixabay.com/audio/2022/03/10/audio_1c8c9a0727.mp3 preload=auto></audio>
<audio id=b2 src=https://cdn.pixabay.com/audio/2021/08/04/audio_0625c1539c.mp3 preload=auto></audio>
<script>
let audioEnabled=false;
let lastSignalCount=0;
function enableAudio(){let a=document.getElementById('b');a.play().then(()=>{a.pause();a.currentTime=0;audioEnabled=true;document.getElementById('unlock').innerText='✅ AUDIO ON - AVVISO 30 SEC ATTIVO';localStorage.setItem('audio','1');}).catch(e=>{});}
function renderStorico(list){
  let h=document.getElementById('storico');
  if(!list || list.length==0){h.innerHTML='<div style=color:#666>Ancora nessun segnale - storico vuoto</div>'; return;}
  let html='';
  list.forEach(s=>{
    html+=`<div class=row ${s.dir}><span>${s.data} - ${s.coppia}</span><span><b>${s.dir}</b> RSI${s.rsi} Scad ${s.scadenza}</span></div>`;
  });
  h.innerHTML=html;
}
async function load(){
  try{
    let r=await fetch('/api/signals'); if(!r.ok) throw new Error(r.status);
    let data=await r.json();
    document.getElementById('timer').innerText=':'+String(data.sec).padStart(2,'0')+' sec';

    // AVVISO 30 SEC PRIMA - countdown
    if(data.wait){
      let to30 = 15 - data.sec;
      if(to30>0){
        document.getElementById('countdown').innerText='⏰ Avviso segnale tra '+to30+' sec';
        document.getElementById('status').innerHTML='⏳ Aspetto :15 sec - ora :'+data.sec+' - prossimo avviso tra '+to30+'s';
      } else {
        document.getElementById('countdown').innerText='🔍 Scansione attiva fino a :58';
      }
    } else {
      if(data.signals.length>0){
        document.getElementById('countdown').innerText='🚨 '+data.signals[0].rimanenti+' SEC PER ENTRARE! SCADE '+data.signals[0].scadenza;
      } else {
        document.getElementById('countdown').innerText='✅ Scansione :'+data.sec+' - nessuna rottura ora';
      }
    }

    let c=document.getElementById('l');
    renderStorico(data.storico);

    if(data.wait){
      if(data.sec < 15 && data.storico.length==0){
        c.innerHTML='<div class=wait>⏰ AVVISO 30 SEC<br>Segnale tra '+(15-data.sec)+' sec<br>Scadenza 1M + Storico attivo</div>';
      }
      return;
    }

    let d=data.signals;
    if(d.length==0){
      if(lastSignalCount>0){c.innerHTML='';}
      document.getElementById('status').innerHTML='🟢 Scan :'+data.sec+' - 18 OTC - 0 segnali - Storico '+data.storico.length;
    } else {
      document.getElementById('status').innerHTML='🔥 '+d.length+' SEGNALI - AVVISO 30 SEC! '+d[0].rimanenti+' SEC RIMANENTI!';
      c.innerHTML='';
      d.forEach(s=>{
        let e=document.createElement('div'); e.className='card '+s.dir;
        e.innerHTML=`<b>${s.coppia} 1M</b> <span style=float:right;color:#aaa;font-size:12px>${s.data}</span><br>
        <span class=${s.dir}>${s.dir} 1M</span> - ${s.bb} RSI ${s.rsi}<br>
        <div style=margin-top:8px;background:#222;padding:8px;border-radius:8px>
        ⏰ SEGNALE: <b>${s.ora}</b><br>
        ⏳ SCADENZA: <b style=color:#ff0;font-size:18px>${s.scadenza_full}</b> (1 MIN)<br>
        ⏱️ RIMANENTI: <b style=color:#0f0;font-size:20px>${s.rimanenti} SEC PER ENTRARE!</b>
        </div>
        <div style=margin-top:10px><span style=background:#0f0;color:#000;padding:10px;border-radius:8px;font-weight:bold;display:block;text-align:center>👉 ENTRA ORA - SCADE ${s.scadenza}</span></div>`;
        c.appendChild(e);
      });

      // AVVISO AUDIO + VIBRAZIONE SOLO SE NUOVO SEGNALE
      if(audioEnabled && d.length!= lastSignalCount){
        document.getElementById('b').play().catch(()=>{});
        setTimeout(()=>{document.getElementById('b2').play().catch(()=>{});},400);
        if(navigator.vibrate) navigator.vibrate([500,100,500,100,800]);
      }
      lastSignalCount=d.length;
    }
    if(localStorage.getItem('audio')=='1'){audioEnabled=true;document.getElementById('unlock').innerText='✅ AUDIO ON - AVVISO 30 SEC';}
  }catch(e){document.getElementById('status').innerHTML='❌ '+e.message;}
}
setInterval(load,2000); load();
</script></body></html>"""

@app.route('/')
def home(): return PAGE
@app.route('/api/signals')
def sig(): return jsonify(analizza())

@app.route('/api/storico')
def storico():
    return jsonify(STORICO[-50:][::-1])

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=10000)
