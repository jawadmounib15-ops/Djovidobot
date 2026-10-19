import os, sys, subprocess, asyncio

# --- AUTO-INSTALL TUTTO PER RENDER (1 file unico) ---
def install_and_import(package, import_name=None):
    try:
        if import_name:
            __import__(import_name)
        else:
            __import__(package)
    except ImportError:
        print(f"Installo {package}...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", package])

install_and_import("ccxt")
install_and_import("python-telegram-bot", "telegram")

import ccxt
from telegram import Bot

TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

if not TOKEN or not CHAT_ID:
    print("ERRORE: Imposta TELEGRAM_TOKEN e CHAT_ID su Render > Environment")
    sys.exit(1)

exchange = ccxt.binance()

def is_pinbar_pulita(o,h,l,c):
    corpo = abs(c-o)
    rng = h-l
    if rng==0 or corpo > rng*0.35: return False,None,0,0
    up = h - max(o,c)
    low = min(o,c) - l
    forma_pct = (corpo/rng)*100
    wick_ratio = max(up,low) / (corpo if corpo!=0 else 0.001)
    if low > corpo*2.5 and low > up*1.5: return True,"BULLISH",forma_pct,wick_ratio
    if up > corpo*2.5 and up > low*1.5: return True,"BEARISH",forma_pct,wick_ratio
    return False,None,0,0

async def main():
    bot = Bot(token=TOKEN)
    print(f"Bot L1 PINBAR 80% avviato! Chat {CHAT_ID}")
    await bot.send_message(chat_id=CHAT_ID, text="✅ Bot Pinbar avviato su Render - cerco su 1H/4H/1D")
    
    coppie = [s for s in exchange.load_markets() if s.endswith('/USDT')][:25]
    TIMEFRAMES = ['1h', '4h', '1d']

    for tf in TIMEFRAMES:
        for sim in coppie:
            try:
                kl = exchange.fetch_ohlcv(sim, tf, limit=250)
                chiusure = [x[4] for x in kl]
                o,h,l,c = kl[-1][1], kl[-1][2], kl[-1][3], kl[-1][4]
                ema200 = sum(chiusure[-200:])/200
                gains=[max(chiusure[i]-chiusure[i-1],0) for i in range(1,len(chiusure))]
                losses=[max(-(chiusure[i]-chiusure[i-1]),0) for i in range(1,len(chiusure))]
                avg_gain = sum(gains[-14:])/14
                avg_loss = sum(losses[-14:])/14
                rsi = 100 - (100/(1+ (avg_gain/(avg_loss if avg_loss!=0 else 0.001))))
                is_pin,tipo,forma_pct,wick_ratio = is_pinbar_pulita(o,h,l,c)
                if not is_pin: continue
                if tipo=="BULLISH" and (c < ema200 or rsi>70): continue
                if tipo=="BEARISH" and (c > ema200 or rsi<30): continue
                max20 = max([x[2] for x in kl[-20:-1]])
                min20 = min([x[3] for x in kl[-20:-1]])
                if not (abs(c-max20)/c < 0.025 or abs(c-min20)/c < 0.025): continue

                if tf == '1h': scadenza = "2-3H"
                elif tf == '4h': scadenza = "8-12H"
                else: scadenza = "2-3 Giorni"

                if tipo=="BULLISH":
                    sl = l - (h-l)*0.1
                    tp1 = c + (c-sl)*2
                else:
                    sl = h + (h-l)*0.1
                    tp1 = c - (sl-c)*2

                msg = (
                    f"💎 L1 PINBAR 80% {tipo} {sim} {tf.upper()}\n\n"
                    f"📍 Prezzo: {c:.2f}\n"
                    f"📊 EMA200: {ema200:.2f} | RSI: {rsi:.1f}\n"
                    f"📈 Forma: {forma_pct:.1f}% | Wick {wick_ratio:.1f}x\n\n"
                    f"⏰ Scadenza: {scadenza}\n"
                    f"🛡️ SL: {sl:.2f}\n🎯 TP: {tp1:.2f}"
                )
                await bot.send_message(chat_id=CHAT_ID,text=msg)
                await asyncio.sleep(1)
            except Exception as e:
                print(f"{sim} {tf} {e}")
                continue

if __name__=="__main__":
    asyncio.run(main())
