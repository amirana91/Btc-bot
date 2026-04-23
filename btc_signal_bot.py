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
]

def send_telegram(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    data = {"chat_id": CHAT_ID, "text": message, "parse_mode": "HTML"}
    try:
        requests.post(url, data=data, timeout=10)
    except Exception as e:
        print(f"Ошибка отправки: {e}")

def get_candles(symbol):
    url = "https://api.bybit.com/v5/market/kline"
    params = {
        "category": "linear",
        "symbol": symbol,
        "interval": "60",
        "limit": 100
    }
    try:
        r = requests.get(url, params=params, timeout=10)
        data = r.json()
        if data.get("retCode") == 0:
            candles = list(reversed(data["result"]["list"]))
            closes = [float(c[4]) for c in candles]
            timestamps = [int(c[0]) for c in candles]
            print(f"OK {symbol}: {closes[-1]:.4f}")
            return closes, timestamps
        else:
            print(f"Bybit error {symbol}: {data}")
            return None, None
    except Exception as e:
        print(f"Error {symbol}: {e}")
        return None, None

def wwma(prices, period):
    result = [None] * len(prices)
    result[period - 1] = sum(prices[:period]) / period
    k = 1.0 / period
    for i in range(period, len(prices)):
        result[i] = prices[i] * k + result[i-1] * (1 - k)
    return result

def calculate_ott(closes, period, percent):
    ma = wwma(closes, period)
    support = [None] * len(closes)
    for i in range(period - 1, len(closes)):
        if ma[i] is None:
            continue
        ls = ma[i] * (1 - percent / 100)
        ss = ma[i] * (1 + percent / 100)
        support[i] = ls if closes[i] >= ma[i] else ss
        if i > period - 1 and support[i-1] is not None:
            if closes[i] > support[i-1]:
                support[i] = max(support[i], support[i-1])
            else:
                support[i] = min(support[i], support[i-1])
    return ma, support

def get_signal(closes, ma, support):
    for i in range(len(closes) - 2, len(closes) - 12, -1):
        if i < 1:
            break
        if None in (support[i], support[i-1], ma[i], ma[i-1]):
            continue
        if ma[i-1] < support[i-1] and ma[i] > support[i]:
            return "BUY", i
        if ma[i-1] > support[i-1] and ma[i] < support[i]:
            return "SELL", i
    return None, None

def main():
    print("Bot started!")
    send_telegram(
        "🤖 <b>Бот запущен!</b>\n\n"
        "Мониторинг пар:\n"
        "• BTC/USDT\n• ZIL/USDT\n• GMT/USDT\n• RUNE/USDT\n• XRP/USDT\n• LTC/USDT\n\n"
        "Таймфрейм: 1H | OTT (7, 1.4)\n\nЖду сигналов... 👀"
    )

    last_signals = {s: (None, None) for s in SYMBOLS}
    first_run = True

    while True:
        now = datetime.now().strftime("%H:%M %d.%m.%Y")
        for symbol in SYMBOLS:
            try:
                closes, timestamps = get_candles(symbol)
                if not closes:
                    continue

                ma, support = calculate_ott(closes, OTT_PERIOD, OTT_PERCENT)
                signal, idx = get_signal(closes, ma, support)
                price = closes[-1]

                if signal:
                    sig_ts = timestamps[idx] if idx else None
                    last_sig, last_ts = last_signals[symbol]
                    send_it = (last_sig != signal) or (last_ts != sig_ts) or (first_run and last_sig is None)

                    if send_it:
                        pair = symbol.replace("USDT", "/USDT")
                        ctime = datetime.fromtimestamp(sig_ts/1000).strftime("%H:%M %d.%m") if sig_ts else "—"
                        emoji = "🟢" if signal == "BUY" else "🔴"
                        action = "LONG (BUY)" if signal == "BUY" else "SHORT (SELL)"
                        arrow = "↑" if signal == "BUY" else "↓"

                        msg = (
                            f"{emoji} <b>СИГНАЛ: {action}</b>\n\n"
                            f"📊 Пара: {pair}\n"
                            f"💰 Цена: <b>{price:.4f}$</b>\n"
                            f"🕯 Свеча: {ctime}\n"
                            f"⏰ Сейчас: {now}\n"
                            f"📈 OTT: MA {arrow} Support\n\n"
                            f"⚠️ Не забудь стоп-лосс!"
                        )
                        send_telegram(msg)
                        last_signals[symbol] = (signal, sig_ts)
                        print(f"Signal sent: {symbol} {signal}")

                time.sleep(2)
            except Exception as e:
                print(f"Error {symbol}: {e}")

        first_run = False
        time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    main()
