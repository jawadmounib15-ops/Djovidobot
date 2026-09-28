import yfinance as yf, pandas as pd
from flask import Flask, jsonify, render_template_string, request
from datetime import datetime, timezone, timedelta
app = Flask(__name__)

PAIRS = {
    "EUR/USD-OTC":"EURUSD=X","GBP/USD-OTC":"GBPUSD=X","USD/JPY-OTC":"USDJPY=X",
    "USD/CAD-OTC":"USDCAD=X","BTC/USD-OTC":"BTC-USD","SOL/USD-OTC":"SOL-USD",
    "EUR/USD":"EURUSD=X","GBP/USD":"GBPUSD=X"
}
ITALY_TZ = timezone(timedelta(hours=2))

def get_data(y, tf):
    interval = {"5m":"5m","15m":"15m","1h":"1h"}.get(tf, "15m")
    df=yf.download(y, period="3d" if interval=="5m" else "7d", interval=interval, progress=False, auto_adjust=False)
    if len(df)<50: return None
    if isinstance(df.columns,pd.MultiIndex): df.columns=df.columns.get_level_values(0)
    c=df['Close']; df['EMA9']=c.ewm(9).mean(); df['EMA21']=c.ewm(21).mean(); df['EMA50']=c.ewm(50).mean()
    delta=c.diff(); g=delta.where(delta>0,0).ewm(14).mean(); ls=-delta.where(delta<0,0).ewm(14).mean()
    df['RSI']=100-(100/(1+g/ls)); df['SMA20']=c.rolling(20).mean(); std=c.rolling(20).std()
    df['BB_UP']=df['SMA20']+2*std; df['BB_LOW']=df['SMA20']-2*std
    return df

def analyze_92(y, tf):
    df=get_data(y, tf)
    if df is None: return {"score":0,"action":"WAIT","reason":"chiuso","tf":tf,"time":datetime.now(ITALY_TZ).strftime("%H:%M:%S"),"timestamp":datetime.now(ITALY_TZ).timestamp()}
    last=df.iloc[-1]
    price=float(last['Close']); ema9=float(last['EMA9']); ema21=float(last['EMA21']); ema50=float(last['EMA50']); rsi=float(last['RSI'])
    k=float((last['Close']-df['Low'].rolling(14).min().iloc[-1])/((df['High'].rolling(14).max().iloc[-1]-df['Low'].rolling(14).min().iloc[-1]) or 1)*100)
    f1=ema9>ema21; f2=42<=rsi<=58; f3=price<float(last['BB_UP'])*0.985; f4=25<=k<=65; f5=float(last['Close'])>float(last['Open'])
    buy=sum([f1,f2,f3,f4,f5]); sell=sum([not f1,f2,price>float(last['BB_LOW'])*1.015,25<=k<=65,float(last['Close'])<float(last['Open'])])
    now=datetime.now(ITALY_TZ)
    if buy==5 and ema21>ema50: return {"score":95,"action":"BUY 95% SICURA","reason":f"5/5 + TREND {tf}","tf":tf,"time":now.strftime("%H:%M:%S"),"timestamp":now.timestamp()}
    if sell==5 and ema21<ema50: return {"score":95,"action":"SELL 95% SICURA","reason":f"5/5 + TREND {tf}","tf":tf,"time":now.strftime("%H:%M:%S"),"timestamp":now.timestamp()}
    if buy==5 or sell==5: return {"score":92,"action":"BUY 92%" if buy==5 else "SELL 92%","reason":f"5/5 PERFETTI {tf}","tf":tf,"time":now.strftime("%H:%M:%S"),"timestamp":now.timestamp()}
    return {"score":0,"action":"WAIT","reason":f"{buy}/5 sotto","tf":tf,"time":now.strftime("%H:%M:%S"),"timestamp":now.timestamp()}

def analyze_pinbar_1min_before(y, tf_label):
    try:
        df=yf.download(y, period="1d", interval="1m", progress=False, auto_adjust=False)
        if len(df)<10: return None
        if isinstance(df.columns,pd.MultiIndex): df.columns=df.columns.get_level_values(0)
        now = datetime.now(ITALY_TZ)
        sec_to_close = (5 - now.minute % 5)*60 - now.second
        if sec_to_close <=0: sec_to_close=300-now.second
        last5 = df.iloc[-5:]
        o=float(last5.iloc[0]['Open']); c=float(last5.iloc[-1]['Close'])
        h=float(last5['High'].max()); lo=float(last5['Low'].min())
        body=abs(c-o); rng=h-lo
        if rng==0: return None
        up=h-max(o,c); low=min(o,c)-lo
        almost_bull = low>1.9*body and low>rng*0.58 and body<rng*0.38 and c>o
        almost_bear = up>1.9*body and up>rng*0.58 and body<rng*0.38 and c<o
        perfect_bull = low>2.5*body and low>rng*0.65 and body<rng*0.25 and c>o
        perfect_bear = up>2.5*body and up>rng*0.65 and body<rng*0.25 and c<o
        if sec_to_close>=30 and sec_to_close<=110 and (almost_bull or almost_bear or perfect_bull or perfect_bear):
            action="BUY 1 MIN PRIMA 📌" if (almost_bull or perfect_bull) else "SELL 1 MIN PRIMA 📌"
            return {"price":round(c,5),"score":93,"action":action,"reason":f"PRE 1 MIN - mancano {sec_to_close}s | ENTRA ORA M5","tf":f"{tf_label} {sec_to_close}s","time":now.strftime("%H:%M:%S"),"timestamp":now.timestamp()}
        if perfect_bull or perfect_bear:
            action="BUY PINBAR 📌" if perfect_bull else "SELL PINBAR 📌"
            return {"price":round(c,5),"score":90,"action":action,"reason":f"CONFERMATA wick {max(up,low)/rng*100:.0f}%","tf":tf_label,"time":now.strftime("%H:%M:%S"),"timestamp":now.timestamp()}
        return None
    except: return None

HTML="""<!DOCTYPE html><html><head><meta name="viewport" content="width=device-width,initial-scale=1"><title>1 MIN PRIMA</title><style>body{background:#0a0a0a;color:#fff;font-family:system-ui;padding:12px}select{width:100%;padding:12px;border-radius:10px;background:#1a1a1f;color:#fff;border:1px solid #333;margin:6px 0}.row{display:flex;gap:8px}.row select{flex:1}.card{background:#1a1a1f;padding:14px;border-radius:14px;margin:10px 0;border-left:5px solid #333}.sbuy{border-left-color:gold;border:3px solid gold}.pre{background:#002a00;border:3px solid #00ff88;animation:blink 0.7s infinite}.pin{background:#0a1a2a;border:3px solid #00e5ff}.badge{padding:6px 12px;border-radius:20px;font-weight:bold}.sB{background:gold;color:#000}.lB{background:#00ff88;color:#000;animation:blink 0.7s infinite}.fresh{background:#00e676;color:#000;padding:3px 8px;border-radius:10px;font-size:11px}@keyframes blink{50%{opacity:0.5}}button{width:100%;padding:14px;background:gold;color:#000;border:none;border-radius:12px;font-weight:bold;font-size:17px}h3{margin-top:22px;border-top:1px solid #333;padding-top:10px}</style></head><body>
<h2>⚡ 1 MINUTO PRIMA - LIVE</h2><div class="row"><select id="pair"><option>EUR/USD-OTC</option><option>USD/CAD-OTC</option><option>BTC/USD-OTC</option><option>EUR/USD</option></select><select id="tf"><option value="5m" selected>5m</option><option value="15m">15m</option></select></div><button onclick="analyze()">ANALIZZA 92%+</button><div id="result"></div>
<h3>⚡ LAVORO 1 - 92%+</h3><div id="auto">...</div>
<h3>📌 LAVORO 2 - 1 MIN PRIMA</h3><div id="pin">...</div>
<audio id="beep" src="https://actions.google.com/sounds/v1/alarms/beep_short.ogg" preload="auto"></audio>
<script>
async function analyze(){let p=document.getElementById('pair').value;let tf=document.getElementById('tf').value;let r=await fetch('/api/analyze?pair='+p+'&tf='+tf);let d=await r.json();if(d.score<92){document.getElementById('result').innerHTML='<div class=card>⏳ '+d.reason+'</div>';return;}document.getElementById('result').innerHTML='<div class=card sbuy><b>'+p+'</b> <span class=badge sB>'+d.action+'</span> <span class=fresh>'+d.time+'</span><br>'+d.reason+'</div>';}
async function scan(){let tf=document.getElementById('tf').value;let r1=await fetch('/api/scan?tf='+tf);let d1=await r1.json();let h1='';d1.forEach(c=>{h1+='<div class=card sbuy><b>'+c.pair+'</b> <span class=badge sB>'+c.action+' '+c.score+'%</span> <span class=fresh>'+c.time+'</span><br>'+c.reason+'</div>'});if(h1=='')h1='<div class=card>⏳ Nessun 92%+</div>';document.getElementById('auto').innerHTML=h1;let r2=await fetch('/api/scan_pinbar?tf='+tf);let d2=await r2.json();let h2='';d2.forEach(c=>{let cls=c.action.includes('1 MIN')?'card pre':'card pin';let badge=c.action.includes('1 MIN')?'lB':'pB';h2+='<div class='+cls+'><b>'+c.pair+' ['+c.tf+']</b> <span class=badge '+badge+'>'+c.action+'</span> <span class=fresh>'+c.time+'</span><div style=font-size:12px>'+c.reason+' | '+c.price+'</div></div>';});if(h2=='')h2='<div class=card>⏳ Aspetto - quando manca 1 min ti avviso</div>';document.getElementById('pin').innerHTML=h2;if(d2.some(x=>x.action.includes('1 MIN')))document.getElementById('beep').play();}
scan();setInterval(scan,3000);
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
        d=analyze_pinbar_1min_before(y,tf)
        if d: res.append({"pair":lab,**d})
    return jsonify(res[:6])
if __name__=='__main__': app.run(host="0.0.0.0",port=10000)
