from flask import Flask, jsonify
import yfinance as yf
from datetime import datetime, timedelta
import pytz
from curl_cffi import requests as cffi_requests
import time

app = Flask(__name__)
session = cffi_requests.Session(impersonate="chrome")
ROMA = pytz.timezone("Europe/Rome")

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
    return scad.strftime("%H:%M:%S"), (60 - now.second), scad

def rsi_bb_medio_stretto(o,h,l,c, df):
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

        # STRINGIAMO:
        # 1. RSI da 42/58 -> 35/65 (più estremo)
        # 2. BB deve ROMPERE davvero, non solo avvicinarsi
        # 3. Serve ombra inversione min 25%

        b_curr = abs(curr['Close']-curr['Open'])
        r_curr = curr['High']-curr['Low']
        lo_curr = min(curr['Open'],curr['Close']) - curr['Low']
        up_curr = curr['High'] - max(curr['Open'],curr['Close'])
        lo_perc = lo_curr/r_curr if r_curr>0 else 0
        up_perc = up_curr/r_curr if r_curr>0 else 0

        # CALL - più stretto
        rottura_inf = prev['Close'] < bb_low_prev or prev['Low'] < bb_low_prev*0.9998 # vera rottura
        if rottura_inf and rsi_prev < 36 and (lo_perc >= 0.28 or curr['Close'] > curr['Open']):
            score = (35 - rsi_prev) + (lo_perc*20) # punteggio per scegliere migliori
            return "CALL", int(rsi_prev), "BB LOW ROTTURA", score

        # PUT - più stretto
        rottura_sup = prev['Close'] > bb_up_prev or prev['High'] > bb_up_prev*1.0002
        if rottura_sup and rsi_prev > 64 and (up_perc >= 0.28 or curr['Close'] < curr['Open']):
            score = (rsi_prev - 65) + (up_perc*20)
            return "PUT", int(rsi_prev), "BB HIGH ROTTURA", score

        return None
    except:
        return None

def analizza():
    global STORICO
    now = datetime.now(ROMA)
    sec = now.second
    if not (20 <= sec <= 58):
        return {"wait": True, "sec": sec, "signals": [], "storico": STORICO[-20:][::-1]}

    out=[]
    try:
        scad_str, rimanenti, scad_dt = scadenza_1m()
        candidati = []
        for i,(ysym,label) in enumerate(OTC_1M):
            try:
                df=get_df_safe(ysym)
                if df is None: continue
                r=df.iloc[-1]
                res=rsi_bb_medio_stretto(r['Open'],r['High'],r['Low'],r['Close'], df)
                if not res: continue
                d, rsi, bb, score=res
                candidati.append({
                    "coppia":label,"dir":d,"rsi":rsi,"bb":bb,"score":score,
                    "scadenza":scad_str,"ora":now.strftime("%H:%M:%S"),
                    "rimanenti": rimanenti, "scadenza_full": scad_dt.strftime("%H:%M:%S"),
                    "data": now.strftime("%d/%m %H:%M:%S")
                })
                if i % 5 == 0: time.sleep(0.12)
            except: continue

        # STRINGIAMO: ordina per score migliore e prendi solo TOP 3-4
        candidati.sort(key=lambda x: x['score'], reverse=True)
        out = candidati[:4] # MAX 4 SEGNALI PER MINUTO, non 14!

        for segnale in out:
            gia = [s for s in STORICO if s['coppia']==segnale['coppia'] and s['ora'][:5]==now.strftime("%H:%M")]
            if not gia:
                STORICO.append(segnale)
                if len(STORICO)>100: STORICO = STORICO[-100:]

        return {"wait": False, "sec": sec, "signals": out, "storico": STORICO[-20:][::-1]}
    except Exception as e:
        return {"wait": False, "sec": sec, "signals": out, "storico": STORICO[-20:][::-1], "error": str(e)[:80]}

PAGE="""<!DOCTYPE html><html><head><meta charset=utf-8>
<meta name=viewport content='width=device-width, initial-scale=1'>
<title>V9.5 MEDIO STRETTO</title>
<style>
*{box-sizing:border-box}body{background:#000;color:#fff;font-family:Arial;margin:0;padding:0}
.header{background:#111;padding:14px;border-bottom:3px solid #ff0;position:sticky;top:0;z-index:10}
.header h2{margin:0;color:#ff0;font-size:18px}.sub{color:#0f0;font-size:11px}
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
<h2>⚡ V9.5 MEDIO - STRINGIAMO - TOP 4 MAX</h2>
<div class=sub>STRETTO: RSI 36/64 + Rottura BB vera + Ombra 28% + Max 4 segnali/min + Storico + 30sec</div>
</div>
<div class=container>
<div id=status>🟡 V9.5 MEDIO - stringiamo - max 4</div>
<div id=timer class=timer>00</div>
<div id=countdown class=countdown></div>
<button id=unlock onclick=enableAudio()>🔊 AUDIO ON - TOP 4</button>
<button id=analyze onclick=load()>🔄 SCANSIONA MEDIO</button>
<div id=l></div>
<div class=storico><h3>📜 STORICO ULTIMI 20 - FILTRATO</h3><div id=storico>...</div></div>
</div>
<audio id=b src=https://cdn.pixabay.com/audio/2022/03/10/audio_1c8c9a0727.mp3 preload=auto></audio>
<script>
let audioEnabled=false, lastCount=0;
function enableAudio(){let a=document.getElementById('b');a.play().then(()=>{a.pause();a.currentTime=0;audioEnabled=true;document.getElementById('unlock').innerText='✅ AUDIO ON - MEDIO';localStorage.setItem('audio','1');}).catch(e=>{});}
function renderStorico(list){let h=document.getElementById('storico'); if(!list||list.length==0){h.innerHTML='<div style=color:#666>Nessun segnale - storico vuoto</div>';return;} let html=''; list.forEach(s=>{html+=`<div class=row ${s.dir}><span>${s.data} - ${s.coppia}</span><span><b>${s.dir}</b> RSI${s.rsi} Scad ${s.scadenza}</span></div>`;}); h.innerHTML=html;}
async function load(){
  try{
    let r=await fetch('/api/signals'); if(!r.ok) throw new Error(r.status);
    let data=await r.json();
    document.getElementById('timer').innerText=':'+String(data.sec).padStart(2,'0')+' sec';
    if(data.wait){document.getElementById('countdown').innerText='⏰ Avviso tra '+(20-data.sec)+' sec - ora max 4 segnali'; document.getElementById('status').innerHTML='⏳ V9.5 MEDIO aspetto :20 - ora :'+data.sec; renderStorico(data.storico); return;}
    renderStorico(data.storico);
    let c=document.getElementById('l');
    if(data.signals.length==0){document.getElementById('status').innerHTML='🟢 MEDIO scan :'+data.sec+' - 0 segnali - filtrato meglio'; document.getElementById('countdown').innerText='✅ Nessuna rottura BB vera ora'; if(lastCount>0){c.innerHTML='';}}
    else{
      document.getElementById('status').innerHTML='🔥 '+data.signals.length+' SEGNALI MEDIO (MAX 4) A :'+data.sec+' - '+data.signals[0].rimanenti+' SEC!';
      document.getElementById('countdown').innerText='🚨 '+data.signals[0].rimanenti+' SEC PER ENTRARE! SCADE '+data.signals[0].scadenza;
      c.innerHTML=''; data.signals.forEach(s=>{
        let e=document.createElement('div'); e.className='card '+s.dir;
        e.innerHTML=`<b>${s.coppia} 1M</b> <span style=float:right;font-size:12px>${s.data}</span><br><span class=${s.dir}>${s.dir} 1M MEDIO</span> - ${s.bb} RSI ${s.rsi}<br><div style=margin-top:8px;background:#222;padding:8px;border-radius:8px>⏰ ${s.ora} → SCAD <b style=color:#ff0>${s.scadenza_full}</b> - <b style=color:#0f0>${s.rimanenti} SEC</b></div><div style=margin-top:10px><span style=background:#ff0;color:#000;padding:10px;border-radius:8px;font-weight:bold;display:block;text-align:center>👉 ENTRA 1 MIN - MEDIO</span></div>`;
        c.appendChild(e);
      });
      if(audioEnabled && data.signals.length!=lastCount){document.getElementById('b').play().catch(()=>{}); if(navigator.vibrate) navigator.vibrate([500,100,500]);}
      lastCount=data.signals.length;
    }
    if(localStorage.getItem('audio')=='1'){audioEnabled=true;document.getElementById('unlock').innerText='✅ AUDIO ON';}
  }catch(e){document.getElementById('status').innerHTML='❌ '+e.message;}
}
setInterval(load,2000); load();
</script></body></html>"""

@app.route('/')
def home(): return PAGE
@app.route('/api/signals')
def sig(): return jsonify(analizza())
@app.route('/api/storico')
def storico(): return jsonify(STORICO[-50:][::-1])

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=10000)
