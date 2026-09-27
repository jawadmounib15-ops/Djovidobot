import yfinance as yf, pandas as pd
from flask import Flask, jsonify, render_template_string, request
app = Flask(__name__)
PAIRS = {"BTC/USD-OTC":"BTC-USD","ETH/USD-OTC":"ETH-USD","SOL/USD-OTC":"SOL-USD","EUR/USD-OTC":"EURUSD=X","GBP/USD-OTC":"GBPUSD=X","USD/JPY-OTC":"USDJPY=X","AUD/USD-OTC":"AUDUSD=X","EUR/JPY-OTC":"EURJPY=X","GBP/JPY-OTC":"GBPJPY=X","EUR/GBP-OTC":"EURGBP=X"}

def analyze_pair(y):
    try:
        df=yf.download(y, period="2d", interval="5m", progress=False, auto_adjust=False)
        if len(df)<50: return None
        if isinstance(df.columns,pd.MultiIndex): df.columns=df.columns.get_level_values(0)
        c=df['Close']; h=df['High']; l=df['Low']
        df['EMA9']=c.ewm(9).mean(); df['EMA21']=c.ewm(21).mean()
        delta=c.diff(); g=delta.where(delta>0,0).ewm(14).mean(); ls=-delta.where(delta<0,0).ewm(14).mean()
        df['RSI']=100-(100/(1+g/ls))
        df['SMA20']=c.rolling(20).mean(); std=c.rolling(20).std()
        df['BB_UP']=df['SMA20']+2*std; df['BB_LOW']=df['SMA20']-2*std
        low14=l.rolling(14).min(); high14=h.rolling(14).max()
        df['STO_K']=100*(c-low14)/(high14-low14); df['STO_D']=df['STO_K'].rolling(3).mean()
        last=df.iloc[-1]
        price=float(last['Close']); ema9=float(last['EMA9']); ema21=float(last['EMA21']); rsi=float(last['RSI'])
        bb_up=float(last['BB_UP']); bb_low=float(last['BB_LOW']); k=float(last['STO_K']); d=float(last['STO_D'])
        
        # FILTRI
        filters=[]
        #1 Trend
        f1_buy = ema9>ema21 and price>ema21
        f1_sell = ema9<ema21 and price<ema21
        #2 RSI zona safe
        f2_buy = 35 <= rsi <= 60
        f2_sell = 40 <= rsi <= 70
        #3 Bollinger non sul bordo (anti-top come prima)
        f3_buy = price < bb_up*0.995
        f3_sell = price > bb_low*1.005
        #4 Stochastic
        f4_buy = k < 78 and k > d
        f4_sell = k > 22 and k < d

        score=0; action="WAIT"; reason=""
        if f1_buy and f2_buy and f3_buy and f4_buy:
            score=90; action="BUY"; reason=f"Tutti 4 filtri OK | RSI {rsi:.1f} STO {k:.0f}"
            if 40<=rsi<=55 and 30<=k<=60: score=95
        elif f1_sell and f2_sell and f3_sell and f4_sell:
            score=90; action="SELL"; reason=f"Tutti 4 filtri OK | RSI {rsi:.1f} STO {k:.0f}"
            if 45<=rsi<=60 and 40<=k<=70: score=95
        else:
            # punteggio parziale
            passed = sum([f1_buy or f1_sell, f2_buy or f2_sell, f3_buy or f3_sell, f4_buy or f4_sell])
            if passed==3: score=75; action="BUY" if f1_buy else "SELL" if f1_sell else "WAIT"; reason=f"3/4 filtri | RSI {rsi:.1f}"
            elif passed==2: score=60; action="WAIT"; reason=f"Solo 2/4 filtri"
            else: score=0; action="WAIT"; reason=f"Mercato sporco"
        
        return {"price":round(price,5),"rsi":round(rsi,1),"k":round(k,0),"score":score,"action":action,"reason":reason,"ema9":round(ema9,5),"ema21":round(ema21,5)}
    except: return None

HTML = """
<!DOCTYPE html><html><head><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Analyzer 4 FILTRI + SOUND</title>
<style>body{background:#0e0e10;color:#fff;font-family:system-ui;padding:12px}
select{width:100%;padding:12px;border-radius:10px;background:#1a1a1f;color:#fff;font-size:16px;border:1px solid #333;margin:8px 0}
.card{background:#1a1a1f;padding:14px;border-radius:14px;margin:10px 0;border-left:5px solid #444}
.buy{border-left-color:#00c853}.sell{border-left-color:#ff1744}.high{border:3px solid gold}
.badge{padding:7px 14px;border-radius:20px;font-weight:bold}.buyB{background:#00c853;color:#000}.sellB{background:#ff1744;color:#fff}.waitB{background:#333}
button{width:100%;padding:13px;background:#00c853;border:none;border-radius:10px;font-weight:bold;font-size:16px}
</style></head><body>
<h2>💎 4 FILTRI + SOUND 90%+</h2>
<select id="pair"><option>USD/JPY-OTC</option><option>EUR/USD-OTC</option><option>GBP/USD-OTC</option><option>BTC/USD-OTC</option><option>ETH/USD-OTC</option><option>SOL/USD-OTC</option><option>AUD/USD-OTC</option><option>EUR/JPY-OTC</option><option>GBP/JPY-OTC</option><option>EUR/GBP-OTC</option></select>
<button onclick="analyze()">ANALIZZA ORA 🔍</button>
<label style="display:flex;align-items:center;gap:8px;margin:10px 0"><input type="checkbox" id="sound" checked> Suono attivo per 90%+</label>
<div id="result"></div>
<hr><h3>Auto Scan 90%+</h3><div id="auto">...</div>
<audio id="beep" src="https://actions.google.com/sounds/v1/alarms/beep_short.ogg" preload="auto"></audio>
<script>
async function analyze(){
 let p=document.getElementById('pair').value;
 document.getElementById('result').innerHTML='Analizzo '+p+'...';
 let r=await fetch('/api/analyze?pair='+p); let d=await r.json();
 if(!d){document.getElementById('result').innerHTML='Dati non disponibili ora'; return;}
 let cls='card '+(d.action=='BUY'?'buy':d.action=='SELL'?'sell':''); if(d.score>=90) cls+=' high';
 let badge=d.action=='BUY'?'buyB':d.action=='SELL'?'sellB':'waitB';
 let html=`<div class="${cls}"><b>${p}</b> - <span class="badge ${badge}">${d.action} ${d.score}%</span><br><small>${d.reason}</small><br><small>Prezzo ${d.price} | EMA9 ${d.ema9} / EMA21 ${d.ema21} | RSI ${d.rsi} STO ${d.k}</small></div>`;
 document.getElementById('result').innerHTML=html;
 if(d.score>=90 && document.getElementById('sound').checked){document.getElementById('beep').play(); if(navigator.vibrate) navigator.vibrate([300,100,300]);}
}
async function scanAuto(){
 try{let r=await fetch('/api/scan'); let data=await r.json(); let html=''; data.forEach(c=>{
  let cls='card '+(c.action=='BUY'?'buy':'sell')+(c.score>=90?' high':''); let b=c.action=='BUY'?'buyB':'sellB';
  html+=`<div class="${cls}"><b>${c.pair}</b> <span class="badge ${b}">${c.action} ${c.score}%</span><br><small>${c.reason}</small></div>`;
  if(c.score>=90 && document.getElementById('sound').checked){document.getElementById('beep').play();}
 }); if(html=='') html='<div class=card>Nessun 90%+ ora - i filtri bloccano i fake come prima</div>'; document.getElementById('auto').innerHTML=html;}catch(e){}
}
analyze(); scanAuto(); setInterval(scanAuto,15000);
</script></body></html>
"""
@app.route('/')
def home(): return render_template_string(HTML)
@app.route('/api/analyze')
def api_analyze():
    label=request.args.get('pair','USD/JPY-OTC'); y=PAIRS.get(label)
    return jsonify(analyze_pair(y))
@app.route('/api/scan')
def api_scan():
    res=[]
    for lab,y in PAIRS.items():
        d=analyze_pair(y)
        if d and d['score']>=75: res.append({"pair":lab,**d})
    return jsonify(sorted(res,key=lambda x:x['score'],reverse=True)[:6])
if __name__=='__main__': app.run(host="0.0.0.0",port=10000)
