# V103 FIX - TUE REGOLE - FIX about:blank - STESSO CODICE
import yfinance as yf, pandas as pd, gc
from flask import Flask, jsonify
import os
app = Flask(__name__)

OTC_MAP = {
    "EURUSD-OTC":"EURUSD=X", "GBPUSD-OTC":"GBPUSD=X", "USDJPY-OTC":"USDJPY=X",
    "AUDUSD-OTC":"AUDUSD=X", "EURJPY-OTC":"EURJPY=X", "EURGBP-OTC":"EURGBP=X",
    "GBPJPY-OTC":"GBPJPY=X", "AUDJPY-OTC":"AUDJPY=X", "EURCHF-OTC":"EURCHF=X",
    "CADJPY-OTC":"CADJPY=X", "EURAUD-OTC":"EURAUD=X", "GBPAUD-OTC":"GBPAUD=X",
    "AUDCHF-OTC":"AUDCHF=X", "EURTRY-OTC":"EURTRY=X", "USDTRY-OTC":"USDTRY=X",
    "NZDJPY-OTC":"NZDJPY=X", "EURCAD-OTC":"EURCAD=X", "AUDCAD-OTC":"AUDCAD=X",
    "EURUSD":"EURUSD=X", "GBPUSD":"GBPUSD=X", "USDJPY":"USDJPY=X", "AUDUSD":"AUDUSD=X",
    "Gold":"GC=F", "Silver":"SI=F", "WTI":"CL=F"
}

def fix(df):
    try:
        if isinstance(df.columns, pd.MultiIndex): 
            df.columns=df.columns.get_level_values(0)
    except: pass
    return df

def calc_rsi(series, period=14):
    try:
        delta=series.diff()
        gain=(delta.where(delta>0,0)).rolling(window=period).mean()
        loss=(-delta.where(delta<0,0)).rolling(window=period).mean()
        if loss.iloc[-1]==0:
            return 50.0
        rs=gain/loss
        rsi=100-(100/(1+rs))
        v=float(rsi.iloc[-1])
        if pd.isna(v): return 50.0
        return v
    except: 
        return 50.0

@app.route('/')
def home():
    return """<html><head><meta name="viewport" content="width=device-width,initial-scale=1"><title>V103 RSI+PIN PERFETTA</title>
<style>
body{background:#0a0a0a;color:#fff;font-family:Arial;text-align:center;padding:8px}
.btn{padding:20px;border-radius:16px;font-weight:bold;font-size:18px;width:98%;max-width:440px;display:block;margin:8px auto;cursor:pointer}
.g{background:#00ff88;color:#000;border:3px solid #00ff88}.d{background:#222;color:#fff;border:2px solid #555}
.card{background:#1e1e1e;border-radius:20px;padding:16px;margin:10px auto;max-width:460px;text-align:left;border-left:10px solid #00ff88;position:relative}
.sell{border-left-color:#ff3b3b}.perf{border:2px solid gold;box-shadow:0 0 12px gold}
.score{font-size:48px;font-weight:900}
.badge{position:absolute;top:12px;right:12px;text-align:right}
.prepara{background:#00ff88;color:#000;font-weight:bold;padding:12px;border-radius:10px;margin-top:10px;text-align:center}
.sellbg{background:#ff3b3b;color:#fff}
.warn40{background:#ffcc00;color:#000;font-weight:900;padding:14px;border-radius:12px;margin:10px auto;max-width:460px;animation:blink 0.5s infinite}
@keyframes blink{0%,50%{opacity:1}51%,100%{opacity:0.6}}
.storico{background:#111;border:1px solid #333;border-radius:12px;padding:12px;margin:14px auto;max-width:460px;text-align:left;font-size:12px}
.tag{font-size:10px;padding:3px 6px;border-radius:6px;font-weight:bold;margin-top:4px;display:inline-block}
.tag-rsi{background:#00ff88;color:#000}.tag-perf{background:gold;color:#000}
#s{padding:12px;border-radius:8px;margin:8px auto;max-width:440px;font-weight:bold}
.on{background:#00ff88;color:#000}.off{background:#ff3b3b;color:#fff}
</style></head><body>
<h2>✅ V103 - RSI ZONA + PIN PERFETTA OVUNQUE</h2>
<div id="s" class="off">🔇 ATTIVA</div>
<div class="btn g" onclick="att()">🔔 ATTIVA SUONO + 40 SEC</div>
<div class="btn d" onclick="scan()">🔍 SCAN ORA</div>
<p id="info">Prende TANTI in RSI 20-30/60-70 + PIN PERFETTE ovunque</p>
<div id="warn40box"></div>
<div id="live"></div>
<div class="storico"><b>📜 STORICO:</b><div id="storico">Vuoto</div><div style="margin-top:6px"><span onclick="clearStor()" style="color:#ff3b3b;cursor:pointer">🗑️ Pulisci</span> | <span onclick="testSuono()" style="color:#00ff88;cursor:pointer">🔊 Test</span></div></div>
<script>
let ctx=null,ok=false,expMin=2,warned40=false;
let stor=JSON.parse(localStorage.getItem('v103_stor')||'[]');
function updStor(){let h=''; stor.slice(0,30).forEach(s=>{h+=`<div>${s}</div>`}); document.getElementById('storico').innerHTML=h||'Vuoto';}
updStor();
function clearStor(){stor=[]; localStorage.setItem('v103_stor',JSON.stringify(stor)); updStor();}
function att(){try{ctx=new (window.AudioContext||window.webkitAudioContext)(); ctx.resume().then(()=>{ok=true; document.getElementById('s').className='on'; document.getElementById('s').innerText='🔊 ON - RSI + PERFETTE'; beep(900,0.4); setTimeout(()=>beep(1300,0.5),300); if(navigator.vibrate) navigator.vibrate([300,100,300]); if(Notification && Notification.permission!=='granted') Notification.requestPermission(); scan();});}catch(e){}}
function beep(f,d){if(!ctx) return; try{let o=ctx.createOscillator(),g=ctx.createGain(); o.type='square'; o.frequency.value=f; o.connect(g); g.connect(ctx.destination); g.gain.setValueAtTime(1,ctx.currentTime); g.gain.exponentialRampToValueAtTime(0.01,ctx.currentTime+d); o.start(); o.stop(ctx.currentTime+d);}catch(e){}}
function suonaSegnale(){if(!ok) return; beep(1100,0.6); setTimeout(()=>beep(1500,0.6),400); if(navigator.vibrate) navigator.vibrate([400,100,600]);}
function avviso40(){if(!ok) return; if(ctx && ctx.state=='suspended') ctx.resume(); beep(1000,0.5); setTimeout(()=>beep(1000,0.5),400); setTimeout(()=>beep(1500,0.6),800); setTimeout(()=>beep(2000,0.8),1300); if(navigator.vibrate) navigator.vibrate([800,200,1000]); if(Notification && Notification.permission==='granted') new Notification('⏰ 40 SEC', {body: cur.length+' segnali'}); document.getElementById('warn40box').innerHTML='<div class="warn40">⏰ 40 SEC - PREPARA 2 MIN!! ⏰</div>'; setTimeout(()=>{document.getElementById('warn40box').innerHTML='';},12000);}
function testSuono(){if(!ok){alert('Attiva'); return;} suonaSegnale();}
let cur=[],ent=0; function getN(){let n=new Date(); let nx=new Date(n); nx.setSeconds(0,0); nx.setMilliseconds(0); nx.setMinutes(n.getMinutes()+1); return nx;}
function scan(){document.getElementById('info').innerText='⏳ Scan RSI ZONA + PIN PERFETTE...'; fetch('/api/scan').then(r=>r.json()).then(d=>{cur=d.signals; ent=getN().getTime(); warned40=false; if(d.signals.length>0){suonaSegnale(); let now=new Date().toLocaleTimeString('it-IT'); d.signals.forEach(s=>{stor.unshift(`${now} - ${s.score}/100 ${s.dir} ${s.pair} RSI${s.rsi} ${s.tag}`);}); localStorage.setItem('v103_stor',JSON.stringify(stor.slice(0,50))); updStor();} render();}).catch(e=>{document.getElementById('info').innerText='Errore';});}
function render(){let now=Date.now(); let diff=Math.ceil((ent-now)/1000); let tot=expMin*60; let h=''; if(cur.length>0){if(diff>40) document.getElementById('info').innerText=`✅ ${cur.length} segnali - avviso tra ${diff-40}s`; else if(diff<=40 && diff>0 && !warned40){ avviso40(); warned40=true; document.getElementById('info').innerText=`🔔 40 SEC!`; } else if(diff<=40 && diff>0) document.getElementById('info').innerText=`⏰ ${diff}s - ENTRA!`; } cur.forEach(s=>{let col=s.dir=='BUY'?'#00ff88':'#ff3b3b'; let left=Math.max(0,tot+diff); let txt=diff>40?`AVVISO TRA ${diff-40}s` : diff>0?`⏰ ENTRA TRA ${diff}s - 2 MIN` : `SCAD ${left}s`; let perfClass=s.tag.includes('PERFETTA')?'perf':''; h+=`<div class="card ${s.dir=='SELL'?'sell':''} ${perfClass}"><div class="badge"><div class="score" style="color:${col}">${s.score}/100</div><div style="color:${col};font-weight:900">${s.dir}</div><div style="font-size:11px">RSI ${s.rsi}</div><div style="font-size:10px">${s.pct}%</div><div class="tag ${s.tag.includes('RSI')?'tag-rsi':'tag-perf'}">${s.tag}</div></div><div style="width:58%"><b style="color:${col}">${s.pair}</b><br><span style="color:#aaa;font-size:11px">${s.reason}</span><br><span style="font-size:12px">${s.price}</span></div><div class="prepara ${s.dir=='SELL'?'sellbg':''}">${txt}</div></div>`;}); document.getElementById('live').innerHTML=h||`Nessun segnale - scan 30 simboli`;}
setInterval(render,1000); setInterval(scan,35000);
</script></body></html>"""

@app.route('/api/scan')
def api():
    out=[]
    for otc, real in OTC_MAP.items():
        try:
            df=yf.download(real, period="1d", interval="1m", progress=False, auto_adjust=True, threads=False)
            df=fix(df)
            if df is None or len(df)<20: 
                continue
            c=float(df.iloc[-1]['Close']); o=float(df.iloc[-1]['Open']); h=float(df.iloc[-1]['High']); l=float(df.iloc[-1]['Low'])
            range_tot=h-l
            if range_tot<=0: 
                continue
            body=abs(c-o)
            up=h-max(c,o)
            down=min(c,o)-l
            rsi=calc_rsi(df['Close'], 14)
            
            pct_up=int((up/range_tot)*100) if range_tot>0 else 0
            pct_down=int((down/range_tot)*100) if range_tot>0 else 0
            body_pct=int((body/range_tot)*100) if range_tot>0 else 0
            
            cond_base_bull = (down > range_tot*0.70) and (body < range_tot*0.25)
            cond_base_bear = (up > range_tot*0.70) and (body < range_tot*0.25)
            cond_perf_bull = (down > range_tot*0.80) and (body < range_tot*0.15)
            cond_perf_bear = (up > range_tot*0.80) and (body < range_tot*0.15)
            
            dire=None; score=0; tag=""; reason=""; pct=0
            
            if cond_base_bull and (20 <= rsi <= 35):
                dire="BUY"; pct=pct_down; score=85 + (5 if rsi<=30 else 0)
                tag="ZONA RSI BUY"
                reason=f"RSI {rsi:.0f} zona 20-30 OVERSOLD + Pin {pct}% >70% corpo {body_pct}% <25%"
            elif cond_base_bear and (60 <= rsi <= 75):
                dire="SELL"; pct=pct_up; score=85 + (5 if rsi>=70 else 0)
                tag="ZONA RSI SELL"
                reason=f"RSI {rsi:.0f} zona 60-70 OVERBOUGHT + Pin {pct}% >70% corpo {body_pct}% <25%"
            elif cond_perf_bull and (15 <= rsi <= 45):
                dire="BUY"; pct=pct_down; score=92
                tag="PERFETTA PULITA"
                reason=f"PIN PERFETTA {pct}% ombra >80% corpo {body_pct}% <15% + RSI {rsi:.0f} - PRESA OVUNQUE"
            elif cond_perf_bear and (55 <= rsi <= 85):
                dire="SELL"; pct=pct_up; score=92
                tag="PERFETTA PULITA"
                reason=f"PIN PERFETTA {pct}% ombra >80% corpo {body_pct}% <15% + RSI {rsi:.0f} - PRESA OVUNQUE"
            else:
                continue
            
            if score>95: score=95
            fmt=f"{c:.5f}" if "JPY" not in otc else f"{c:.3f}"
            out.append({"pair":otc,"dir":dire,"price":fmt,"score":score,"pct":pct,"rsi":int(rsi),"tag":tag,"reason":reason})
            del df; gc.collect()
        except Exception as e:
            print(f"Skip {otc} {e}")
            gc.collect()
            continue
    out=sorted(out, key=lambda x: x['score'], reverse=True)[:12]
    return jsonify({"signals":out})

if __name__=="__main__":
    port=int(os.environ.get("PORT",10000))
    app.run(host="0.0.0.0", port=port)
