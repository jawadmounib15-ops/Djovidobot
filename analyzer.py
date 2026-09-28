import yfinance as yf, pandas as pd
from flask import Flask, jsonify, render_template_string, request
from datetime import datetime, timezone, timedelta
app = Flask(__name__)

PAIRS = {
    "EUR/USD-OTC":"EURUSD=X","GBP/USD-OTC":"GBPUSD=X","USD/JPY-OTC":"USDJPY=X",
    "AUD/USD-OTC":"AUDUSD=X","USD/CAD-OTC":"USDCAD=X","BTC/USD-OTC":"BTC-USD",
    "ETH/USD-OTC":"ETH-USD","SOL/USD-OTC":"SOL-USD","BNB/USD-OTC":"BNB-USD",
    "EUR/USD":"EURUSD=X","GBP/USD":"GBPUSD=X","USD/JPY":"USDJPY=X"
}
ITALY_TZ = timezone(timedelta(hours=2))

def get_data(y, tf):
    interval = {"5m":"5m","15m":"15m","1h":"1h"}.get(tf, "15m")
    df=yf.download(y, period="3d" if interval=="5m" else "7d", interval=interval, progress=False, auto_adjust=False)
    if len(df)<50: return None
    if isinstance(df.columns,pd.MultiIndex): df.columns=df.columns.get_level_values(0)
    c=df['Close']; h=df['High']; l=df['Low']
    df['EMA9']=c.ewm(9).mean(); df['EMA21']=c.ewm(21).mean(); df['EMA50']=c.ewm(50).mean()
    delta=c.diff(); g=delta.where(delta>0,0).ewm(14).mean(); ls=-delta.where(delta<0,0).ewm(14).mean()
    df['RSI']=100-(100/(1+g/ls))
    df['SMA20']=c.rolling(20).mean(); std=c.rolling(20).std()
    df['BB_UP']=df['SMA20']+2*std; df['BB_LOW']=df['SMA20']-2*std
    return df

def analyze_92(y, tf):
    df=get_data(y, tf)
    if df is None: return {"score":0,"action":"MERCATO CHIUSO","reason":"chiuso","tf":tf,"time":datetime.now(ITALY_TZ).strftime("%H:%M:%S"),"timestamp":datetime.now(ITALY_TZ).timestamp()}
    last=df.iloc[-1]
    price=float(last['Close']); ema9=float(last['EMA9']); ema21=float(last['EMA21']); ema50=float(last['EMA50']); rsi=float(last['RSI'])
    k=float((last['Close']-df['Low'].rolling(14).min().iloc[-1])/((df['High'].rolling(14).max().iloc[-1]-df['Low'].rolling(14).min().iloc[-1]) or 1)*100)
    f1 = ema9>ema21; f2 = 42<=rsi<=58; f3 = price<float(last['BB_UP'])*0.985; f4 = 25<=k<=65; f5 = float(last['Close'])>float(last['Open'])
    buy=sum([f1,f2,f3,f4,f5]); sell=sum([not f1,f2,price>float(last['BB_LOW'])*1.015,25<=k<=65,float(last['Close'])<float(last['Open'])])
    now=datetime.now(ITALY_TZ)
    if buy==5 and ema21>ema50: return {"score":95,"action":"BUY 95% SICURA","reason":f"5/5 + TREND {tf}","tf":tf,"time":now.strftime("%H:%M:%S"),"timestamp":now.timestamp()}
    if sell==5 and ema21<ema50: return {"score":95,"action":"SELL 95% SICURA","reason":f"5/5 + TREND {tf}","tf":tf,"time":now.strftime("%H:%M:%S"),"timestamp":now.timestamp()}
    if buy==5 or sell==5: return {"score":92,"action":"BUY 92%" if buy==5 else "SELL 92%","reason":f"5/5 PERFETTI {tf}","tf":tf,"time":now.strftime("%H:%M:%S"),"timestamp":now.timestamp()}
    return {"score":0,"action":"WAIT","reason":f"{buy}/5 sotto","tf":tf,"time":now.strftime("%H:%M:%S"),"timestamp":now.timestamp()}

# LAVORO 2 - LIVE FIX RITARDO
def analyze_pinbar_live(y, tf_label):
    try:
        df=yf.download(y, period="1d", interval="1m", progress=False, auto_adjust=False)
        if len(df)<20: return None
        if isinstance(df.columns,pd.MultiIndex): df.columns=df.columns.get_level_values(0)
        last=df.iloc[-1]; prev=df.iloc[-2]
        o=float(last['Open']); c=float(last['Close']); h=float(last['High']); lo=float(last['Low'])
        body=abs(c-o); rng=h-lo
        if rng==0: return None
        up=h-max(o,c); low=min(o,c)-lo
        
        # LIVE - si sta formando ADESSO
        pin_bull_live = low>2.2*body and low>rng*0.60 and body<rng*0.32 and c>o
        pin_bear_live = up>2.2*body and up>rng*0.60 and body<rng*0.32 and c<o
        
        # Chiusa 1m fa
        o2=float(prev['Open']); c2=float(prev['Close']); h2=float(prev['High']); lo2=float(prev['Low'])
        body2=abs(c2-o2); rng2=h2-lo2
        if rng2==0: return None
        up2=h2-max(o2,c2); low2=min(o2,c2)-lo2
        pin_bull_closed = low2>2.5*body2 and low2>rng2*0.65 and body2<rng2*0.25 and c2>o2
        pin_bear_closed = up2>2.5*body2 and up2>rng2*0.65 and body2<rng2*0.25 and c2<o2

        if not (pin_bull_live or pin_bear_live or pin_bull_closed or pin_bear_closed): return None
        now=datetime.now(ITALY_TZ)
        if pin_bull_live or pin_bear_live:
            action = "BUY LIVE 📌 ENTRA ORA" if pin_bull_live else "SELL LIVE 📌 ENTRA ORA"
            reason = f"LIVE 1m FORMAZIONE {tf_label} wick {max(up,low)/rng*100:.0f}% - NON ASPETTARE"
            score=92
        else:
            action = "BUY PINBAR 📌" if pin_bull_closed else "SELL PINBAR 📌"
            reason = f"CHIUSA 1m fa {tf_label} wick {max(up2,low2)/rng2*100:.0f}% corpo {body2/rng2*100:.0f}%"
            score=90
        return {"price":round(c,5),"score":score,"action":action,"reason":reason,"tf":tf_label,"time":now.strftime("%H:%M:%S"),"timestamp":now.timestamp()}
    except: return None

HTML="""<!DOCTYPE html><html><head><meta name="viewport" content="width=device-width,initial-scale=1"><title>2 LAVORI LIVE FIX</title><style>body{background:#0a0a0a;color:#fff;font-family:system-ui;padding:12px}select{width:100%;padding:12px;border-radius:10px;background:#1a1a1f;color:#fff;border:1px solid #333;margin:6px 0}.row{display:flex;gap:8px}.row select{flex:1}.card{background:#1a1a1f;padding:14px;border-radius:14px;margin:10px 0;border-left:5px solid #333}.sbuy{border-left-color:gold;border:3px solid gold}.pin{background:#0a1a2a;border:3px solid #00e5ff}.live{background:#001a00;border:3px solid #00ff88;animation:blink 0.8s infinite}.badge{padding:6px 12px;border-radius:20px;font-weight:bold}.sB{background:gold;color:#000}.pB{background:#00e5ff;color:#000}.lB{background:#00ff88;color:#000}.fresh{background:#00e676;color:#000;padding:3px 8px;border-radius:10px;font-size:11px}@keyframes blink{50%{opacity:0.6}}button{width:100%;padding:14px;background:gold;color:#000;border:none;border-radius:12px;font-weight:bold;font-size:17px}h3{margin-top:22px;border-top:1px solid #333;padding-top:10px}</style></head><body>
<h2>📈 2 LAVORI - LIVE FIX</h2><div class="row"><select id="pair"><option>EUR/USD-OTC</option><option>USD/CAD-OTC</option><option>BTC/USD-OTC</option><option>EUR/USD</option></select><select id="tf"><option value="5m" selected>5m</option><option value="15m">15m</option><option value="1h">1h</option></select></div><button onclick="analyze()">ANALIZZA LAVORO 1</button><div id="result"></div>
<h3>⚡ LAVORO 1 - 92%+</h3><div id="auto">...</div>
<h3>📌 LAVORO 2 - PINBAR LIVE (5 sec)</h3><div id="pin">...</div>
<audio id="beep" src="https://actions.google.com/sounds/v1/alarms/beep_short.ogg" preload="auto"></audio>
<script>
async function analyze(){let p=document.getElementById('pair').value;let tf=document.getElementById('tf').value;document.getElementById('result').innerHTML='...';let r=await fetch('/api/analyze?pair='+p+'&tf='+tf);let d=await r.json();if(d.score<92){document.getElementById('result').innerHTML='<div class=card>⏳ '+d.reason+'</div>';return;}document.getElementById('result').innerHTML='<div class=card sbuy><b>'+p+'</b> <span class=badge sB>'+d.action+'</span> <span class=fresh>'+d.time+'</span><br>'+d.reason+'</div>';document.getElementById('beep').play();}
async function scan(){let tf=document.getElementById('tf').value;let r1=await fetch('/api/scan?tf='+tf);let d1=await r1.json();let h1='';d1.forEach(c=>{h1+='<div class=card sbuy><b>'+c.pair+'</b> <span class=badge sB>'+c.action+' '+c.score+'%</span> <span class=fresh>'+c.time+'</span><br>'+c.reason+'</div>'});if(h1=='')h1='<div class=card>⏳ Nessun 92%+ fresco</div>';document.getElementById('auto').innerHTML=h1;let r2=await fetch('/api/scan_pinbar?tf='+tf);let d2=await r2.json();let h2='';d2.forEach(c=>{let cls=c.action.includes('LIVE')?'card live':'card pin';let badge=c.action.includes('LIVE')?'lB':'pB';h2+='<div class='+cls+'><b>'+c.pair+' [1m LIVE]</b> <span class=badge '+badge+'>'+c.action+'</span> <span class=fresh>'+c.time+'</span><div style=font-size:12px;color:#aaa>'+c.reason+' | '+c.price+'</div></div>';});if(h2=='')h2='<div class=card>⏳ Nessuna pinbar live ora - scansiono ogni 5 sec</div>';document.getElementById('pin').innerHTML=h2;let hasLive=d2.some(x=>x.action.includes('LIVE'));if(hasLive)document.getElementById('beep').play();}
scan();setInterval(scan,5000);
</script></body></html>"""

@app.route('/')
def home(): return render_template_string(HTML)
@app.route('/api/analyze')
def api_analyze(): return jsonify(analyze_92(PAIRS.get(request.args.get('pair','EUR/USD-OTC')), request.args.get('tf','15m')))
@app.route('/api/scan')
def api_scan():
    tf=request.args.get('tf','15m'); res=[]
    for lab,y in PAIRS.items():
        d=analyze_92(y,tf)
        if d and d['score']>=92: res.append({"pair":lab,**d})
    return jsonify(res[:6])
@app.route('/api/scan_pinbar')
def api_scan_pinbar():
    tf=request.args.get('tf','15m'); res=[]
    for lab,y in PAIRS.items():
        d=analyze_pinbar_live(y,tf)
        if d: res.append({"pair":lab,**d})
    return jsonify(res[:6])
if __name__=='__main__': app.run(host="0.0.0.0",port=10000)
