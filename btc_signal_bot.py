import requests
import time
from datetime import datetime

# === НАСТРОЙКИ ===
TELEGRAM_TOKEN = "8633747198:AAGnMpqoX8TiX8ljbFAmfBF3YBE9YEKWWHI"
CHAT_ID = "6825257186"
OTT_PERIOD = 7
OTT_PERCENT = 1.4
CHECK_INTERVAL = 300

SYMBOLS = ["BTCUSDT","ZILUSDT","GMTUSDT","RUNEUSDT","XRPUSDT","LTCUSDT"]

API_URL = "https://api.binance.com/api/v3/klines"


def send_telegram(text):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        requests.post(url, data={"chat_id": CHAT_ID, "text": text}, timeout=10)
    except Exception as e:
        print("Telegram error:", e)


def get_candles(symbol):
    try:
        r = requests.get(API_URL, params={"symbol": symbol, "interval": "1h", "limit": 100}, timeout=10)
        data = r.json()
        if isinstance(data, list):
            closes = [float(c[4]) for c in data]
            times = [int(c[0]) for c in data]
            return closes, times
        else:
            print("Binance error:", data)
            return None, None
    except Exception as e:
        print("Request error:", e)
        return None, None


def wwma(prices, period):
    result = [None] * len(prices)
    result[period - 1] = sum(prices[:period]) / period
    k = 1.0 / period
    for i in range(period, len(prices)):
        result[i] = prices[i] * k + result[i - 1] * (1 - k)
    return result


def calculate_ott(closes):
    ma = wwma(closes, OTT_PERIOD)
    support = [None] * len(closes)

    for i in range(OTT_PERIOD - 1, len(closes)):
        if ma[i] is None:
            continue

        longstop = ma[i] * (1 - OTT_PERCENT / 100)
        shortstop = ma[i] * (1 + OTT_PERCENT / 100)

        if closes[i] >= ma[i]:
            support[i] = longstop
        else:
            support[i] = shortstop

        if i > 0 and support[i - 1] is not None:
            if closes[i] > support[i - 1]:
                support[i] = max(support[i], support[i - 1])
            else:
                support[i] = min(support[i], support[i - 1])

    return ma, support


# 👉 ищем ПОСЛЕДНЕЕ пересечение
def get_last_signal(closes, ma, support):
    for i in range(len(closes) - 1, 1, -1):
        if not all([ma[i], ma[i-1], support[i], support[i-1]]):
            continue

        if ma[i-1] < support[i-1] and ma[i] > support[i]:
            return "BUY", i

        if ma[i-1] > support[i-1] and ma[i] < support[i]:
            return "SELL", i

    return None, None


def main():
    print("BOT STARTED")

    last_signals = {}

    # 🔥 1. СРАЗУ отправляем последний сигнал
    for symbol in SYMBOLS:
        closes, times = get_candles(symbol)
        if closes is None:
            continue

        ma, support = calculate_ott(closes)
        signal, idx = get_last_signal(closes, ma, support)

        if signal:
            ts = times[idx]
            price = closes[-1]
            now = datetime.now().strftime("%H:%M %d.%m.%Y")
            candle_time = datetime.fromtimestamp(ts / 1000).strftime("%H:%M %d.%m")

            pair = symbol.replace("USDT", "/USDT")

            if signal == "BUY":
                msg = f"🟢 LONG\n{pair}\nЦена: {price}$\nСвеча: {candle_time}\nСейчас: {now}"
            else:
                msg = f"🔴 SHORT\n{pair}\nЦена: {price}$\nСвеча: {candle_time}\nСейчас: {now}"

            send_telegram(msg)
            last_signals[symbol] = (signal, ts)

        time.sleep(1)

    send_telegram("🤖 Бот запущен и мониторит новые сигналы")

    # 🔥 2. ДАЛЬШЕ только новые сигналы
    while True:
        for symbol in SYMBOLS:
            try:
                closes, times = get_candles(symbol)
                if closes is None:
                    continue

                ma, support = calculate_ott(closes)
                signal, idx = get_last_signal(closes, ma, support)

                if signal:
                    ts = times[idx]
                    last_signal, last_ts = last_signals.get(symbol, (None, None))

                    if ts != last_ts:
                        price = closes[-1]
                        now = datetime.now().strftime("%H:%M %d.%m.%Y")
                        candle_time = datetime.fromtimestamp(ts / 1000).strftime("%H:%M %d.%m")

                        pair = symbol.replace("USDT", "/USDT")

                        if signal == "BUY":
                            msg = f"🟢 LONG\n{pair}\nЦена: {price}$\nСвеча: {candle_time}\nСейчас: {now}"
                        else:
                            msg = f"🔴 SHORT\n{pair}\nЦена: {price}$\nСвеча: {candle_time}\nСейчас: {now}"

                        send_telegram(msg)
                        last_signals[symbol] = (signal, ts)

                time.sleep(2)

            except Exception as e:
                print("Error:", e)

        time.sleep(CHECK_INTERVAL)


if __name__ == "__main__":
    main()
