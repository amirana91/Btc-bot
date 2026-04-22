import requests
import time
from datetime import datetime

# === НАСТРОЙКИ ===
TELEGRAM_TOKEN = "8633747198:AAGnMpqoX8TiX8ljbFAmfBF3YBE9YEKWWHI"
CHAT_ID = "6825257186"
OTT_PERIOD = 7
OTT_PERCENT = 1.4
CHECK_INTERVAL = 60 * 5  # проверка каждые 5 минут

# === СПИСОК ПАР ===
SYMBOLS = [
    "BTCUSDT",
    "ZILUSDT",
    "GMTUSDT",
    "RUNEUSDT",
    "XRPUSDT",
    "LTCUSDT",
]

def send_telegram(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    data = {"chat_id": CHAT_ID, "text": message, "parse_mode": "HTML"}
    try:
        requests.post(url, data=data)
    except Exception as e:
        print(f"Ошибка отправки: {e}")

def get_candles(symbol):
    url = "https://api.binance.com/api/v3/klines"
    params = {"symbol": symbol, "interval": "1h", "limit": 100}
    try:
        r = requests.get(url, params=params)
        data = r.json()
        closes = [float(c[4]) for c in data]
        return closes
    except Exception as e:
        print(f"Ошибка получения данных {symbol}: {e}")
        return None

def wwma(prices, period):
    result = [None] * len(prices)
    result[period - 1] = sum(prices[:period]) / period
    k = 1.0 / period
    for i in range(period, len(prices)):
        result[i] = prices[i] * k + result[i-1] * (1 - k)
    return result

def calculate_ott(closes, period, percent):
    ma = wwma(closes, period)
    valid_start = period - 1
    support = [None] * len(closes)

    for i in range(valid_start, len(closes)):
        if ma[i] is None:
            continue
        longstop = ma[i] * (1 - percent / 100)
        shortstop = ma[i] * (1 + percent / 100)
        if closes[i] >= ma[i]:
            support[i] = longstop
        else:
            support[i] = shortstop
        if i > valid_start and support[i-1] is not None:
            if closes[i] > support[i-1]:
                support[i] = max(support[i], support[i-1])
            else:
                support[i] = min(support[i], support[i-1])

    return ma, support

def check_signal(closes, ma, support):
    i = len(closes) - 2
    if support[i] is None or support[i-1] is None:
        return None
    if ma[i] is None or ma[i-1] is None:
        return None
    if ma[i-1] < support[i-1] and ma[i] > support[i]:
        return "BUY"
    if ma[i-1] > support[i-1] and ma[i] < support[i]:
        return "SELL"
    return None

def main():
    print("🤖 Бот запущен!")
    send_telegram(
        "🤖 <b>Бот запущен!</b>\n\n"
        "Мониторинг пар:\n"
        "• BTC/USDT\n• ZIL/USDT\n• GMT/USDT\n• RUNE/USDT\n• XRP/USDT\n• LTC/USDT\n\n"
        "Таймфрейм: 1H | OTT (7, 1.4)\n\nЖду сигналов... 👀"
    )

    last_signals = {symbol: None for symbol in SYMBOLS}

    while True:
        now = datetime.now().strftime("%H:%M %d.%m.%Y")
        for symbol in SYMBOLS:
            try:
                closes = get_candles(symbol)
                if closes is None:
                    continue

                ma, support = calculate_ott(closes, OTT_PERIOD, OTT_PERCENT)
                signal = check_signal(closes, ma, support)
                current_price = closes[-1]

                print(f"[{now}] {symbol}: {current_price:.4f} | Сигнал: {signal}")

                if signal and signal != last_signals[symbol]:
                    pair_name = symbol.replace("USDT", "/USDT")
                    if signal == "BUY":
                        msg = (
                            f"🟢 <b>СИГНАЛ: LONG (BUY)</b>\n\n"
                            f"📊 Пара: {pair_name}\n"
                            f"💰 Цена: <b>{current_price:.4f}$</b>\n"
                            f"⏰ Время: {now}\n"
                            f"📈 OTT: MA ↑ Support\n\n"
                            f"⚠️ Не забудь стоп-лосс!"
                        )
                    else:
                        msg = (
                            f"🔴 <b>СИГНАЛ: SHORT (SELL)</b>\n\n"
                            f"📊 Пара: {pair_name}\n"
                            f"💰 Цена: <b>{current_price:.4f}$</b>\n"
                            f"⏰ Время: {now}\n"
                            f"📉 OTT: MA ↓ Support\n\n"
                            f"⚠️ Не забудь стоп-лосс!"
                        )
                    send_telegram(msg)
                    last_signals[symbol] = signal
                    print(f"✅ Сигнал отправлен: {symbol} {signal}")

                time.sleep(2)

            except Exception as e:
                print(f"Ошибка {symbol}: {e}")

        time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    main()
