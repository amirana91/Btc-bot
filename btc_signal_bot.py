import requests
import time
from datetime import datetime

# === НАСТРОЙКИ ===
TELEGRAM_TOKEN = "ТВОЙ_ТОКЕН"
CHAT_ID = "ТВОЙ_CHAT_ID"

OTT_PERIOD = 7
OTT_PERCENT = 1.4
CHECK_INTERVAL = 60 * 5  # 5 минут

# === ПАРЫ ===
SYMBOLS = [
    "BTCUSDT",
    "ZILUSDT",
    "GMTUSDT",
    "RUNEUSDT",
    "XRPUSDT",
    "LTCUSDT",
]

# === Binance API (только стабильные) ===
APIS = [
    "https://api.binance.com/api/v3/klines",
    "https://api1.binance.com/api/v3/klines",
]

# === Telegram ===
def send_telegram(message):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        requests.post(url, data={
            "chat_id": CHAT_ID,
            "text": message,
            "parse_mode": "HTML"
        }, timeout=10)
    except Exception as e:
        print(f"Ошибка Telegram: {e}")

# === Получение свечей ===
def get_candles(symbol):
    params = {"symbol": symbol, "interval": "1h", "limit": 100}

    for api_url in APIS:
        try:
            r = requests.get(api_url, params=params, timeout=10)

            if r.status_code != 200:
                print(f"❌ {api_url} статус {r.status_code}")
                continue

            data = r.json()

            # если Binance вернул ошибку
            if isinstance(data, dict):
                print(f"❌ Binance ошибка {symbol}: {data}")
                continue

            closes = [float(c[4]) for c in data]
            timestamps = [int(c[0]) for c in data]

            print(f"✅ {symbol} OK ({api_url})")
            return closes, timestamps

        except Exception as e:
            print(f"⚠️ Ошибка {api_url} {symbol}: {e}")

        time.sleep(1)  # защита от блокировки

    print(f"❌ Все API недоступны для {symbol}")
    return None, None

# === WWMA ===
def wwma(prices, period):
    result = [None] * len(prices)
    result[period - 1] = sum(prices[:period]) / period
    k = 1.0 / period

    for i in range(period, len(prices)):
        result[i] = prices[i] * k + result[i - 1] * (1 - k)

    return result

# === OTT ===
def calculate_ott(closes, period, percent):
    ma = wwma(closes, period)
    support = [None] * len(closes)

    for i in range(period - 1, len(closes)):
        if ma[i] is None:
            continue

        longstop = ma[i] * (1 - percent / 100)
        shortstop = ma[i] * (1 + percent / 100)

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

# === Сигнал ===
def get_signal(closes, ma, support):
    for i in range(len(closes) - 2, len(closes) - 12, -1):
        if i < 1:
            break

        if not all([support[i], support[i-1], ma[i], ma[i-1]]):
            continue

        if ma[i-1] < support[i-1] and ma[i] > support[i]:
            return "BUY", i

        if ma[i-1] > support[i-1] and ma[i] < support[i]:
            return "SELL", i

    return None, None

# === MAIN ===
def main():
    print("🤖 Бот запущен")

    send_telegram(
        "🤖 <b>Бот запущен</b>\n\n"
        "Пары:\nBTC, ZIL, GMT, RUNE, XRP, LTC\n"
        "ТФ: 1H | OTT (7, 1.4)\n\n"
        "Жду сигналы..."
    )

    last_signals = {s: (None, None) for s in SYMBOLS}

    while True:
        now = datetime.now().strftime("%H:%M %d.%m.%Y")

        for symbol in SYMBOLS:
            try:
                closes, timestamps = get_candles(symbol)
                if closes is None:
                    continue

                ma, support = calculate_ott(closes, OTT_PERIOD, OTT_PERCENT)
                signal, idx = get_signal(closes, ma, support)

                price = closes[-1]

                print(f"{symbol} | {price:.4f} | {signal}")

                if signal:
                    ts = timestamps[idx]
                    last_signal, last_ts = last_signals[symbol]

                    if last_signal != signal or last_ts != ts:
                        pair = symbol.replace("USDT", "/USDT")
                        candle_time = datetime.fromtimestamp(ts / 1000).strftime("%H:%M %d.%m")

                        if signal == "BUY":
                            msg = f"🟢 <b>LONG</b>\n{pair}\nЦена: {price}$\nСвеча: {candle_time}"
                        else:
                            msg = f"🔴 <b>SHORT</b>\n{pair}\nЦена: {price}$\nСвеча: {candle_time}"

                        send_telegram(msg)
                        last_signals[symbol] = (signal, ts)

                time.sleep(2)

            except Exception as e:
                print(f"Ошибка {symbol}: {e}")

        time.sleep(CHECK_INTERVAL)

# === START ===
if __name__ == "__main__":
    main()
