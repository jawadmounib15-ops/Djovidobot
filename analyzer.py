import yfinance as yf, pandas as pd
from flask import Flask, jsonify, render_template_string, request
app = Flask(__name__)

PAIRS = {
    "EUR/USD-OTC":"EURUSD=X","GBP/USD-OTC":"GBPUSD=X","USD/JPY-OTC":"USDJPY=X",
    "AUD/USD-OTC":"AUDUSD=X","USD/CAD-OTC":"USDCAD=X","USD/CHF-OTC":"USDCHF=X",
    "EUR/JPY-OTC":"EURJPY=X","EUR/GBP-OTC":"EURGBP=X","GBP/JPY-OTC":"GBPJPY=X",
    "AUD/JPY-OTC":"AUDJPY=X","EUR/AUD-OTC":"EURAUD=X","NZD/USD-OTC":"NZDUSD=X",
    "BTC/USD-OTC":"BTC-USD","ETH/USD-OTC":"ETH-USD","SOL/USD-OTC":"SOL-USD",
    "BNB/USD-OTC":"BNB-USD","EUR/CAD-OTC":"EURCAD=X","GBP/CAD-OTC":"GBPCAD=X",
    "CAD/JPY-OTC":"CADJPY=X","CHF/JPY-OTC":"CHFJPY=X"
}

def analyze_pair(y):
    try:
        df=yf.download(y, period="3d", interval="5m", progress=False, auto_adjust=False)
        if len(df)<60: return None
        if isinstance(df.columns,pd.MultiIndex): df.columns=df.columns.get_level_values(0)
        c=df['Close']; h=df['High']; l=df['Low']; o=df['Open']
        df['EMA9']=c.ewm(9).mean(); df['EMA21']=c.ewm(21).mean(); df['EMA50']=c.ewm(50).mean()
        delta=c.diff(); g=delta.where(delta>0,0).ewm(14).mean(); ls=-delta.where(delta<0,0).ewm(14).mean()
        df['RSI']=100-(100/(1+g/ls))
        df['SMA20']=c.rolling(20).mean(); std=c.rolling(20).std()
        df['BB_UP']=df['SMA20']+2*std; df['BB_LOW']=df['SMA20']-2*std
        low14=l.rolling(14).min(); high14=h.rolling(14).max()
        df['STO_K']=100*(c-low14)/((high14-low14).replace(0,1)); df['STO_D']=df['STO_K'].rolling(3).mean()
        last=df.iloc[-1]
        price=float(last['Close']); ema9=float(last['EMA9']); ema21=float(last['EMA21']); ema50=float(last['EMA50'])
        rsi=float(last['RSI']); bb_up=float(last['BB_UP']); bb_low=float(last['BB_LOW'])
        k=float(last['STO_K']); d=float(last['STO_D']); open_c=float(last['Open']); close_c=float(last['Close'])

        # 5 FILTRI
        f1_buy = ema9 > ema21 and ema21 > ema50 and price > ema21
        f1_sell = ema9 < ema21 and ema21 < ema50 and price < ema21
        f2_buy = 40 <= rsi <= 58
        f2_sell = 42 <= rsi <= 65
        f3_buy = price < bb_up * 0.988  # anti-top
        f3_sell = price > bb_low * 1.012 # anti-bottom
        f4_buy = 28 <= k <= 68 and k > d
        f4_sell = 32 <= k <= 75 and k < d
        f5_buy = close_c > open_c
        f5_sell = close_c < open_c

        score=0; action="WAIT"; reason=""
        if f1_buy and f2_buy and f3_buy and f4_buy and f5_buy:
            score=95; action="BUY SICURA"; reason=f"5/5 PERFETTI | RSI {rsi:.1f} STO {k:.0f}"
        elif f1_sell and f2_sell and f3_sell and f4_sell and f5_sell:
            score=95; action="SELL SICURA"; reason=f"5/5 PERFETTI | RSI {rsi:.1f} STO {k:.0f}"
        else:
            buy_pass = sum([f1_buy,f2_buy,f3_buy,f4_buy,f5_buy])
            sell_pass = sum([f1_sell,f2_sell,f3_sell,f4_sell,f5_sell])
            if buy_pass==4: score=80; action="BUY"; reason=f"4/5 filtri - manca 1 | RSI {rsi:.1f}"
            elif sell_pass==4: score=80; action="SELL"; reason=f"4/5 filtri - manca 1 | RSI {rsi:.1f}"
            elif buy_pass==3 or sell_pass==3: score=60; action="WAIT"; reason=f"3/5 filtri - mercato sporco"
            else: score=0; action="WAIT"; reason="Mercato sporco - aspetta 95%"

        return {"price":round(price,5),"rsi":round(rsi,1),"k":round(k,0),"score":score,"action":action,"reason":reason}
    except Exception as e: return None

HTML = """
<!DOCTYPE html><html><head><meta name="viewport" content="width=device-width, initial-scale=1">
<title>5 FILTRI SICURA 95%</title>
<style>body{background:#0e0e10;color:#fff;font-family:system-ui;padding:12px}
select{width:100%;padding:12px;border-radius:10px;background:#1a1a1f;color:#fff;font-size:16px;border:1px solid #333;margin:8px 0}
.card{background:#1a1a1f;padding:14px;border-radius:14px;margin:10px 0;border-left:5px solid #444}
.buy{border-left-color:#00c853}.sell{border-left-color:#ff1744}.sbuy{border-left-color:gold;border:3px solid gold}.ssell{border-left-color:gold;border:3px solid gold}
.badge{padding:7px 14px;border-radius:20px;font-weight:bold}.buyB{background:#00c853;color:#000}.sellB{background:#ff1744}.waitB{background:#333}.sB{background:gold;color:#000;animation:blink 1s infinite}
@keyframes blink{50%{opacity:0.5}}
button{width:100%;padding:13px;background:gold;color:#000;border:none;border-radius:10px;font-weight:bold;font-size:17px}
</style></head><body>
<h2>💎 5 FILTRI - SOLO SICURA 95% SUONA</h2>
<select id="pair"><option>EUR/USD-OTC</option><option>USD/JPY-OTC</option><option>GBP/USD-OTC</option><option>BTC/USD-OTC</option><option>ETH/USD-OTC</option><option>SOL/USD-OTC</option><option>AUD/USD-OTC</option><option>EUR/JPY-OTC</option><option>GBP/JPY-OTC</option><option>EUR/GBP-OTC</option><option>NZD/USD-OTC</option><option>AUD/JPY-OTC</option></select>
<button onclick="analyze()">ANALIZZA 🔍</button>
<label style="display:flex;align-items:center;gap:8px;margin:10px 0"><input type="checkbox" id="sound" checked> 🔊 Suono + Vibrazione per 95% SICURA</label>
<div id="result"></div><hr><h3>Auto Scan - Solo 80%+</h3><div id="auto">Carico...</div>
<audio id="beep" src="https://actions.google.com/sounds/v1/alarms/beep_short.ogg" preload="auto"></audio>
<script>
async function analyze(){
 let p=document.getElementById('pair').value;
 document.getElementById('result').innerHTML='Analizzo '+p+'...';
 let r=await fetch('/api/analyze?pair='+p); let d=await r.json();
 if(!d){document.getElementById('result').innerHTML='Dati non disponibili - mercato chiuso'; return;}
 let cls='card '+(d.action.includes('BUY')?'buy':'')+(d.action.includes('SELL')?'sell':''); if(d.score>=95) cls=d.action.includes('BUY')?'card sbuy':'card ssell';
 let badge=d.action.includes('SICURA')?'sB':d.action=='BUY'?'buyB':d.action=='SELL'?'sellB':'waitB';
 let html=`<div class="${cls}"><b>${p}</b> - <span class="badge ${badge}">${d.action} ${d.score}%</span><br><small>${d.reason}</small><br><small>Prezzo ${d.price} | RSI ${d.rsi} STO ${d.k}</small></div>`;
 document.getElementById('result').innerHTML=html;
 if(d.score>=95 && document.getElementById('sound').checked){document.getElementById('beep').play(); if(navigator.vibrate) navigator.vibrate([400,100,400,100,400]);}
}
async function scanAuto(){
 try{let r=await fetch('/api/scan'); let data=await r.json(); let html=''; data.forEach(c=>{
  let cls='card '+(c.action.includes('BUY')?'buy':'sell'); if(c.score>=95) cls=c.action.includes('BUY')?'card sbuy':'card ssell'; let b=c.action.includes('SICURA')?'sB':c.action=='BUY'?'buyB':'sellB';
  html+=`<div class="${cls}"><b>${c.pair}</b> <span class="badge ${b}">${c.action} ${c.score}%</span><br><small>${c.reason}</small></div>`;
  if(c.score>=95 && document.getElementById('sound').checked){document.getElementById('beep').play();}
 }); if(html=='') html='<div class=card>⏳ Nessuna SICURA ora - i 5 filtri bloccano tutto. Aspetta il BEEP</div>'; document.getElementById('auto').innerHTML=html;}catch(e){}
}
analyze(); scanAuto(); setInterval(scanAuto,15000);
</script></body></html>
"""
@app.route('/')
def home(): return render_template_string(HTML)
@app.route('/api/analyze')
def api_analyze():
    label=request.args.get('pair','EUR/USD-OTC'); y=PAIRS.get(label)
    d=analyze_pair(y); return jsonify(d)
@app.route('/api/scan')
def api_scan():
    res=[]
    for lab,y in PAIRS.items():
        d=analyze_pair(y)
        if d and d['score']>=80: res.append({"pair":lab,**d})
    return jsonify(sorted(res,key=lambda x:x['score'],reverse=True)[:6])
if __name__=='__main__': app.run(host="0.0.0.0",port=10000)
