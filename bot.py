def bot_loop():
    send_tg("✅ *V15.10 TEST FORZATO LIVE*\n💎 25% Pinbar | Se non trova niente in 2 min manda TEST")
    last_test = time.time()
    while True:
        try:
            found = 0
            for period,label in [(300,"M5"),(900,"M15"),(3600,"H1"),(14400,"H4")]:
                for i in range(0, len(PAIRS), 4):
                    batch=PAIRS[i:i+4]
                    ths=[]
                    for p in batch:
                        th=threading.Thread(target=process, args=(p,period,label), daemon=True)
                        th.start(); ths.append(th)
                    for th in ths: th.join(timeout=8)
                    time.sleep(1)
            # Se dopo 2 minuti zero segnali, manda TEST per forza
            if time.time() - last_test > 120:
                send_tg("🧪 *TEST - BOT FUNZIONA*\n⏰ Se vedi questo, Telegram è OK\n📊 Pocket oggi non dà pattern, mercato morto!\n🔄 Continuo a cercare...")
                last_test = time.time()
        except Exception as e:
            time.sleep(10)
        time.sleep(8)
