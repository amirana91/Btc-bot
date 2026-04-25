import requests
import time
from datetime import datetime

TELEGRAM_TOKEN = "8633747198:AAGnMpqoX8TiX8ljbFAmfBF3YBE9YEKWWHI"
CHAT_ID = "6825257186"
OTT_PERIOD = 7
OTT_PERCENT = 1.4
CHECK_INTERVAL = 60 * 5

SYMBOLS = [
    "BTCUSDT",
    "ZILUSDT",
    "GMTUSDT",
    "RUNEUSDT",
    "XRPUSDT",
    "LTCUSDT",
    "SOLUSDT",
    "BNBUSDT",
    "ETHUSDT",
    "DOGEUSDT",
    "PEPEUSDT",
    "WIFUSDT",
    "AVAXUSDT",
    "LINKUSDT",
    "DOTUSDT",
]

TIMEFRAMES = [
    {"interval": "30", "label": "30 минут", "key": "30m"},
    {"interval": "60", "label": "1 час",    "key": "1h"},
]

def send_telegram(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    data = {"chat_id": CHAT_ID, "text": message, "parse_mode": "HTML"}
    try:
        requests.post(url, data=data, timeout=10)
    except Exception as e:
        print(f"Ошибка отправки: {e}")

def get_candles(symbol, interval):
    url = "https://api.bybit.com/v5/market/kline"
    params = {
        "category": "linear",
        "symbol": symbol,
        "interval": interval,
        "limit": 150
    }
    try:
        r = requests.get(url, params=params, timeout=10)
        data = r.json()
        if data.get("retCode") == 0:
            candles = list(reversed(data["result"]["list"]))
            closes = [float(c[4]) for c in candles]
            timestamps = [int(c[0]) for c in candles]
            return closes, timestamps
        else:
            print(f"Bybit error {symbol} {interval}: {data}")
            return None, None
    except Exception as e:
        print(f"Error {symbol} {interval}: {e}")
        return None, None

def wwma(src, length):
    wwalpha = 1.0 / length
    WWMA = [0.0] * len(src)
    WWMA[0] = src[0]
    for i in range(1, len(src)):
        WWMA[i] = wwalpha * src[i] + (1 - wwalpha) * WWMA[i-1]
    return WWMA

def calculate_ott(closes, length, percent):
    n = len(closes)
    MAvg = wwma(closes, length)
    fark = [MAvg[i] * percent * 0.01 for i in range(n)]

    longStop = [MAvg[i] - fark[i] for i in range(n)]
    for i in range(1, n):
        longStopPrev = longStop[i-1]
        if MAvg[i] > longStopPrev:
            longStop[i] = max(longStop[i], longStopPrev)

    shortStop = [MAvg[i] + fark[i] for i in range(n)]
    for i in range(1, n):
        shortStopPrev = shortStop[i-1]
        if MAvg[i] < shortStopPrev:
            shortStop[i] = min(shortStop[i], shortStopPrev)

    dir_ = [1] * n
    for i in range(1, n):
        prev_dir = dir_[i-1]
        if prev_dir == -1 and MAvg[i] > shortStop[i-1]:
            dir_[i] = 1
        elif prev_dir == 1 and MAvg[i] < longStop[i-1]:
            dir_[i] = -1
        else:
            dir_[i] = prev_dir

    MT = [longStop[i] if dir_[i] == 1 else shortStop[i] for i in range(n)]

    OTT = []
    for i in range(n):
        if MAvg[i] > MT[i]:
            OTT.append(MT[i] * (200 + percent) / 200)
        else:
            OTT.append(MT[i] * (200 - percent) / 200)

    return MAvg, OTT

def get_signal(MAvg, OTT):
    n = len(MAvg)
    for i in range(n - 2, n - 7, -1):
        if i < 3:
            break
        ott2_curr = OTT[i - 2]
        ott2_prev = OTT[i - 3]
        mavg_curr = MAvg[i]
        mavg_prev = MAvg[i - 1]
        if mavg_prev <= ott2_prev and mavg_curr > ott2_curr:
            return "BUY", i
        if mavg_prev >= ott2_prev and mavg_curr < ott2_curr:
            return "SELL", i
    return None, None

def main():
    print("Bot started!")
    send_telegram(
        "🤖 <b>Бот запущен!</b>\n\n"
        "Мониторинг 15 пар:\n"
        "BTC • ZIL • GMT • RUNE • XRP • LTC\n"
        "SOL • BNB • ETH • DOGE • PEPE\n"
        "WIF • AVAX • LINK • DOT\n\n"
        "Таймфреймы: <b>30 минут</b> и <b>1 час</b>\n"
        "Индикатор: OTT (7, 1.4, WWMA)\n\nЖду сигналов... 👀"
    )

    # Храним сигналы для каждой пары и каждого таймфрейма
    last_signals = {
        f"{s}_{tf['key']}": (None, None)
        for s in SYMBOLS
        for tf in TIMEFRAMES
    }
    first_run = True

    while True:
        now = datetime.now().strftime("%H:%M %d.%m.%Y")

        for tf in TIMEFRAMES:
            for symbol in SYMBOLS:
                try:
                    closes, timestamps = get_candles(symbol, tf["interval"])
                    if not closes:
                        continue

                    MAvg, OTT = calculate_ott(closes, OTT_PERIOD, OTT_PERCENT)
                    signal, idx = get_signal(MAvg, OTT)
                    price = closes[-1]

                    key = f"{symbol}_{tf['key']}"
                    print(f"[{now}] {symbol} {tf['key']}: {price:.6f} | {signal}")

                    if signal:
                        sig_ts = timestamps[idx] if idx else None
                        last_sig, last_ts = last_signals[key]
                        send_it = (last_sig != signal) or (last_ts != sig_ts) or (first_run and last_sig is None)

                        if send_it:
                            pair = symbol.replace("USDT", "/USDT")
                            ctime = datetime.fromtimestamp(sig_ts/1000).strftime("%H:%M %d.%m") if sig_ts else "—"
                            emoji = "🟢" if signal == "BUY" else "🔴"
                            action = "LONG (BUY)" if signal == "BUY" else "SHORT (SELL)"
                            arrow = "↑" if signal == "BUY" else "↓"
                            tf_emoji = "⏱" if tf["key"] == "30m" else "🕐"

                            # Стоп-лосс 2% и тейк-профит 4%
                            if signal == "BUY":
                                stop_loss = price * 0.98
                                take_profit = price * 1.04
                            else:
                                stop_loss = price * 1.02
                                take_profit = price * 0.96

                            msg = (
                                f"{emoji} <b>СИГНАЛ: {action}</b>\n"
                                f"{tf_emoji} Таймфрейм: <b>{tf['label']}</b>\n\n"
                                f"📊 Пара: {pair}\n"
                                f"💰 Цена входа: <b>{price:.6f}$</b>\n"
                                f"🛑 Стоп-лосс: <b>{stop_loss:.6f}$</b> (-2%)\n"
                                f"🎯 Тейк-профит: <b>{take_profit:.6f}$</b> (+4%)\n"
                                f"🕯 Свеча: {ctime}\n"
                                f"⏰ Сейчас: {now}\n"
                                f"📈 OTT: MA {arrow} OTT\n"
                            )
                            send_telegram(msg)
                            last_signals[key] = (signal, sig_ts)
                            print(f"Signal sent: {symbol} {tf['key']} {signal}")

                    time.sleep(1)
                except Exception as e:
                    print(f"Error {symbol} {tf['key']}: {e}")

        first_run = False
        time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    main()
