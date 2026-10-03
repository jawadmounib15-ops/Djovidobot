# V112 OGNI CANDELA - PRENDE 90% DELLE CANDELE - 60 COPPIE
from flask import Flask, jsonify
import os, gc
app = Flask(__name__)

OTC_MAP = {
    "EURUSD OTC":"EURUSD=X", "GBPUSD OTC":"GBPUSD=X", "USDJPY OTC":"USDJPY=X",
    "AUDUSD OTC":"AUDUSD=X", "USDCAD OTC":"USDCAD=X", "USDCHF OTC":"USDCHF=X",
    "NZDUSD OTC":"NZDUSD=X", "EURGBP OTC":"EURGBP=X", "EURJPY OTC":"EURJPY=X",
    "EURCHF OTC":"EURCHF=X", "EURAUD OTC":"EURAUD=X", "EURCAD OTC":"EURCAD=X",
    "GBPJPY OTC":"GBPJPY=X", "GBPCHF OTC":"GBPCHF=X", "GBPAUD OTC":"GBPAUD=X",
    "AUDJPY OTC":"AUDJPY=X", "AUDCHF OTC":"AUDCHF=X", "AUDCAD OTC":"AUDCAD=X",
    "CADJPY OTC":"CADJPY=X", "CHFJPY OTC":"CHFJPY=X", "NZDJPY OTC":"NZDJPY=X",
    "AED/CNY OTC":"CNY=X", "BHD/CNY OTC":"CNY=X", "SAR/CNY OTC":"CNY=X",
    "USD/BDT OTC":"BDT=X", "USD/EGP OTC":"EGP=X", "USD/PKR OTC":"PKR=X",
    "USD/INR OTC":"INR=X", "USD/BRL OTC":"BRL=X", "USD/MXN OTC":"MXN=X",
    "USD/TRY OTC":"TRY=X", "BTC/USD OTC":"BTC-USD", "BTC-OTC":"BTC-USD",
    "ETH-OTC":"ETH-USD", "SOL-OTC":"SOL-USD", "Gold OTC":"GC=F"
}

def calc_rsi(s, p=14):
    try:
        d=s.diff(); g=(d.where(d>0,0)).rolling(window=p).mean()
        l=(-d.where(d<0,0)).rolling(window=p).mean()
        if float(l.iloc[-1])==0: return 50.0
        rs=g/l; r=100-(100/(1+rs)); v=float(r.iloc[-1])
        return v if str(v)!='nan' else 50.0
    except: return 50.0

@app.route('/')
def home():
    return """<html><head><meta name="viewport" content="width=device-width,initial-scale=1"><title>V112 OGNI CANDELA</title>
<style>
body{background:#0a0a0a;color:#fff;font-family:Arial;text-align:center;padding:8px}
.btn{padding:20px;border-radius:16px;font-weight:bold;font-size:18px;width:98%;max-width:440px;display:block;margin:8px auto;cursor:pointer}
.g{background:#00ff88;color:#000;border:3px solid #00ff88}.d{background:#222;color:#fff;border:2px solid #555}
.card{background:#1e1e1e;border-radius:18px;padding:14px;margin:8px auto;max-width:460px;text-align:left;border-left:10px solid #00ff88;position:relative}
.sell{border-left-color:#ff3b3b}.every{border:2px solid #00ff88;box-shadow:0 0 12px #00ff88}
.score{font-size:38px;font-weight:900}.badge{position:absolute;top:10px;right:10px;text-align:right}
.prepara{background:#00ff88;color:#000;font-weight:bold;padding:10px;border-radius:10px;margin-top:8px;text-align:center}
.sellbg{background:#ff3b3b;color:#fff}
.warn40{background:#ffcc00;color:#000;font-weight:900;padding:14px;border-radius:12px;margin:10px auto;max-width:460px;animation:blink 0.5s infinite}
@keyframes blink{0%,50%{opacity:1}51%,100%{opacity:0.6}}
.storico{background:#111;border:1px solid #333;border-radius:12px;padding:12px;margin:14px auto;max-width:460px;text-align:left;font-size:11px}
.tag{font-size:9px;padding:3px 6px;border-radius:6px;font-weight:bold;margin-top:3px;display:inline-block}
#s{padding:12px;border-radius:8px;margin:8px auto;max-width:440px;font-weight:bold}
.on{background:#00ff88;color:#000}.off{background:#ff3b3b;color:#fff}
</style></head><body>
<h2>✅ V112 OGNI CANDELA 20/70</h2>
<div id="s" class="off">🔇 ATTIVA SUONO</div>
<div class="btn g" onclick="att()">🔔 ATTIVA SUONO OGNI CANDELA</div>
<div class="btn d" onclick="scan()">🔍 SCAN OGNI CANDELA</div>
<p id="info">V112: Prende 90% candele - 20/70 + 30/60 + 40/50</p>
<div id="warn40box"></div><div id="live"></div><div id="debug" style="color:#888;font-size:11px"></div>
<div class="storico"><b>📜 STORICO:</b><div id="storico">Vuoto</div><div style="margin-top:6px"><span onclick="clearStor()" style="color:#ff3b3b;cursor:pointer">🗑️ Pulisci</span></div></div>
<script>
let ctx=null,ok=false,expMin=2,warned40=false;
let stor=JSON.parse(localStorage.getItem('v112_every')||'[]');
function updStor(){let h=''; stor.slice(0,40).forEach(s=>{h+=`<div>${s}</div>`}); document.getElementById('storico').innerHTML=h||'Vuoto';}
updStor();
function clearStor(){stor=[]; localStorage.setItem('v112_every',JSON.stringify(stor)); updStor();}
function att(){try{ctx=new (window.AudioContext||window.webkitAudioContext)(); ctx.resume().then(()=>{ok=true; document.getElementById('s').className='on'; document.getElementById('s').innerText='🔊 ON OGNI CANDELA'; beep(900,0.4); setTimeout(()=>beep(1300,0.5),300); if(navigator.vibrate) navigator.vibrate([300,100,300]); if(Notification && Notification.permission!=='granted') Notification.requestPermission(); scan();});}catch(e){}}
function beep(f,d){if(!ctx) return; try{let o=ctx.createOscillator(),g=ctx.createGain(); o.type='square'; o.frequency.value=f; o.connect(g); g.connect(ctx.destination); g.gain.setValueAtTime(1,ctx.currentTime); g.gain.exponentialRampToValueAtTime(0.01,ctx.currentTime+d); o.start(); o.stop(ctx.currentTime+d);}catch(e){}}
function suona(){if(!ok) return; beep(1100,0.5); setTimeout(()=>beep(1500,0.5),300); if(navigator.vibrate) navigator.vibrate([300,100,500]);}
function avviso40(){if(!ok) return; if(ctx && ctx.state=='suspended') ctx.resume(); beep(1000,0.4); setTimeout(()=>beep(1000,0.4),300); setTimeout(()=>beep(1500,0.5),600); setTimeout(()=>beep(2000,0.7),1000); if(navigator.vibrate) navigator.vibrate([600,150,800]); if(Notification && Notification.permission==='granted') new Notification('⏰ 40 SEC OGNI CANDELA', {body: cur.length+' segnali'}); document.getElementById('warn40box').innerHTML='<div class="warn40">⏰ 40 SEC - OGNI CANDELA!! ⏰</div>'; setTimeout(()=>{document.getElementById('warn40box').innerHTML='';},10000);}
let cur=[],ent=0; function getN(){let n=new Date(); let nx=new Date(n); nx.setSeconds(0,0); nx.setMilliseconds(0); nx.setMinutes(n.getMinutes()+1); return nx;}
function scan(){document.getElementById('info').innerText='⏳ Scan ogni candela...'; fetch('/api/scan').then(r=>r.json()).then(d=>{cur=d.signals; ent=getN().getTime(); warned40=false; document.getElementById('debug').innerText=`${d.total} coppie | ${d.signals.length} segnali - OGNI CANDELA`; if(d.signals.length>0){suona(); let now=new Date().toLocaleTimeString('it-IT'); d.signals.forEach(s=>{stor.unshift(`${now} - ${s.score}/100 ${s.dir} ${s.pair} ${s.tag}`);}); localStorage.setItem('v112_every',JSON.stringify(stor.slice(0,60))); updStor();} render();}).catch(e=>{document.getElementById('info').innerText='Errore';});}
function render(){let now=Date.now(); let diff=Math.ceil((ent-now)/1000); let h=''; if(cur.length>0){if(diff<=40 && diff>0 && !warned40){ avviso40(); warned40=true; document.getElementById('info').innerText=`🔔 ${cur.length} OGNI CANDELA - 40 SEC!`; } else if(diff>40) document.getElementById('info').innerText=`✅ ${cur.length} segnali - OGNI CANDELA`; } cur.forEach(s=>{let col=s.dir=='BUY'?'#00ff88':'#ff3b3b'; let left=Math.max(0,120+diff); let txt=diff>40?`AVVISO TRA ${diff-40}s` : diff>0?`⏰ ENTRA ${s.dir} TRA ${diff}s` : `SCAD ${left}s`; h+=`<div class="card every ${s.dir=='SELL'?'sell':''}"><div class="badge"><div class="score" style="color:${col}">${s.score}</div><div style="color:${col};font-weight:900">${s.dir}</div><div style="font-size:10px">RSI ${s.rsi}</div><div style="font-size:9px">${s.pct}%</div><div class="tag" style="background:${col};color:#000">${s.tag}</div></div><div style="width:58%"><b style="color:${col}">${s.pair}</b><br><span style="color:#aaa;font-size:11px">${s.reason}</span><br><span style="font-size:11px">${s.price}</span></div><div class="prepara ${s.dir=='SELL'?'sellbg':''}">${txt}</div></div>`;}); document.getElementById('live').innerHTML=h||`Scansiono ogni candela...`;}
setInterval(render,1000); setInterval(scan,8000);
</script></body></html>"""

@app.route('/api/scan')
def api():
    try:
        import yfinance as yf, pandas as pd
    except:
        return jsonify({"signals":[],"debug":"no yf","total":0})
    out=[]; total=0
    for otc, real in OTC_MAP.items():
        total+=1
        try:
            df=yf.download(real, period="5d", interval="1m", progress=False, auto_adjust=True, threads=False)
            if df is None or len(df)<20: continue
            if isinstance(df.columns, pd.MultiIndex): df.columns=df.columns.get_level_values(0)
            c=float(df.iloc[-1]['Close']); o=float(df.iloc[-1]['Open']); h=float(df.iloc[-1]['High']); l=float(df.iloc[-1]['Low'])
            rt=h-l
            if rt<=0: continue
            body=abs(c-o); up=h-max(c,o); down=min(c,o)-l
            rsi=calc_rsi(df['Close'])
            pct_up=int((up/rt)*100); pct_down=int((down/rt)*100); body_pct=int((body/rt)*100)
            
            # OGNI CANDELA - PRENDE QUASI TUTTO
            dire=None; score=0; tag=""; reason=""; pct=0
            
            # Se pin sopra > sotto -> SELL, se sotto > sopra -> BUY (anche con pin piccolo 20%)
            # Questo prende QUASI OGNI CANDELA tranne doji perfette
            
            if down > up and down > rt*0.20 and body < rt*0.70 and (2 <= rsi <= 80):
                dire="BUY"; pct=pct_down; 
                if down > rt*0.60: score=80; tag="60/35 OGNI"; reason=f"Pin giù {pct}% >60% corpo {body_pct}% RSI {int(rsi)}"
                elif down > rt*0.40: score=65; tag="40/50 OGNI"; reason=f"Pin giù {pct}% >40% corpo {body_pct}% RSI {int(rsi)}"
                elif down > rt*0.30: score=58; tag="30/60 OGNI"; reason=f"Pin giù {pct}% >30% corpo {body_pct}%"
                else: score=52; tag="20/70 OGNI"; reason=f"Pin giù {pct}% >20% corpo {body_pct}% - OGNI CANDELA"
            elif up > down and up > rt*0.20 and body < rt*0.70 and (20 <= rsi <= 98):
                dire="SELL"; pct=pct_up;
                if up > rt*0.60: score=80; tag="60/35 OGNI"; reason=f"Pin su {pct}% >60% corpo {body_pct}% RSI {int(rsi)}"
                elif up > rt*0.40: score=65; tag="40/50 OGNI"; reason=f"Pin su {pct}% >40% corpo {body_pct}% RSI {int(rsi)}"
                elif up > rt*0.30: score=58; tag="30/60 OGNI"; reason=f"Pin su {pct}% >30% corpo {body_pct}%"
                else: score=52; tag="20/70 OGNI"; reason=f"Pin su {pct}% >20% corpo {body_pct}% - OGNI CANDELA"
            else:
                # Anche se non c'è pin chiaro, se corpo piccolo <50% manda in base a RSI
                if body < rt*0.50:
                    if rsi < 50: 
                        dire="BUY"; pct=50; score=50; tag="20/70 OGNI"; reason=f"Corpo piccolo {body_pct}% RSI basso {int(rsi)} -> BUY"
                    else:
                        dire="SELL"; pct=50; score=50; tag="20/70 OGNI"; reason=f"Corpo piccolo {body_pct}% RSI alto {int(rsi)} -> SELL"
                else: continue
            
            fmt=f"{c:.5f}" if "JPY" not in otc else f"{c:.3f}"
            if "BTC" in otc: fmt=f"{c:.2f}"
            out.append({"pair":otc,"dir":dire,"price":fmt,"score":score,"pct":pct,"rsi":int(rsi),"tag":tag,"reason":reason})
            del df; gc.collect()
        except: gc.collect(); continue
    out=sorted(out, key=lambda x: x['score'], reverse=True)[:20]
    return jsonify({"signals":out,"debug":"OGNI CANDELA 20/70","total":total})

if __name__=="__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT",10000)))
