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
    "BTCUSDT", "ZILUSDT", "GMTUSDT", 
    "RUNEUSDT", "XRPUSDT", "LTCUSDT",
]

def send_telegram(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    data = {"chat_id": CHAT_ID, "text": message, "parse_mode": "HTML"}
    try:
        # Добавлен timeout, чтобы скрипт не висел при сбое сети
        requests.post(url, data=data, timeout=10)
    except Exception as e:
        print(f"Ошибка отправки в Telegram: {e}")

def get_candles(symbol):
    url = "https://fapi.binance.com/fapi/v1/klines"
    params = {"symbol": symbol, "interval": "1h", "limit": 100}
    try:
        r = requests.get(url, params=params, timeout=10)
        r.raise_for_status() # Проверка на ошибки HTTP
        data = r.json()
        closes = [float(c[4]) for c in data]
        timestamps = [int(c[0]) for c in data]
        return closes, timestamps
    except Exception as e:
        print(f"Ошибка получения данных Binance для {symbol}: {e}")
        return None, None

def wwma(prices, period):
    if len(prices) < period:
        return [None] * len(prices)
    result = [None] * len(prices)
    result[period - 1] = sum(prices[:period]) / period
    alpha = 1.0 / period
    for i in range(period, len(prices)):
        result[i] = prices[i] * alpha + result[i-1] * (1 - alpha)
    return result

def calculate_ott(closes, period, percent):
    ma = wwma(closes, period)
    support = [None] * len(closes)
    valid_start = period - 1
    for i in range(valid_start, len(closes)):
        if ma[i] is None: continue
        fark = ma[i] * percent * 0.01
        longstop = ma[i] - fark
        shortstop = ma[i] + fark
        if i == valid_start:
            support[i] = longstop
        else:
            if ma[i] > support[i-1]:
                support[i] = max(longstop, support[i-1])
            else:
                support[i] = min(shortstop, support[i-1])
    return ma, support


def get_current_signal(closes, ma, support):
def get_current_signal(closes, ma, support):
    # Проверяем последние 3 свечи
    for i in range(len(closes) - 1, len(closes) - 4, -1):
        if i < 1 or ma[i] is None or support[i] is None or support[i-1] is None:
            continue
        # SELL: MA ушла под Support
        if ma[i-1] >= support[i-1] and ma[i] < support[i]:
            return "SELL", i
        # BUY: MA вышла над Support
        if ma[i-1] <= support[i-1] and ma[i] > support[i]:
            return "BUY", i
    return None, None





def main():
    print("🤖 Бот запущен!")
    send_telegram(
        "🤖 <b>Бот запущен!</b>\n\n"
        "Мониторинг пар: BTC, ZIL, GMT, RUNE, XRP, LTC\n"
        "Таймфрейм: 1H | OTT (7, 1.4)\n\n"
        "Жду сигналов... 👀"
    )

    last_signals = {symbol: (None, None) for symbol in SYMBOLS}
    first_run = True

    while True:
        now_str = datetime.now().strftime("%H:%M %d.%m.%Y")
        for symbol in SYMBOLS:
            try:
                closes, timestamps = get_candles(symbol)
                if closes is None or len(closes) < OTT_PERIOD:
                    continue

                ma, support = calculate_ott(closes, OTT_PERIOD, OTT_PERCENT)
                signal, signal_idx = get_current_signal(closes, ma, support)
                
                if signal:
                    signal_ts = timestamps[signal_idx]
                    last_signal, last_ts = last_signals[symbol]

                    # Условие отправки: сигнал изменился ИЛИ это новая свеча с тем же сигналом
                    if signal != last_signal or signal_ts != last_ts:
                        current_price = closes[-1]
                        pair_name = symbol.replace("USDT", "/USDT")
                        candle_time = datetime.fromtimestamp(signal_ts / 1000).strftime("%H:%M %d.%m")
                        
                        emoji = "🟢" if signal == "BUY" else "🔴"
                        side = "LONG (BUY)" if signal == "BUY" else "SHORT (SELL)"
                        trend_info = "MA ↑ Support" if signal == "BUY" else "MA ↓ Support"
                        
                        msg = (
                            f"{emoji} <b>СИГНАЛ: {side}</b>\n\n"
                            f"📊 Пара: {pair_name}\n"
                            f"💰 Цена: <b>{current_price:.4f}$</b>\n"
                            f"🕯 Свеча сигнала: {candle_time}\n"
                            f"⏰ Сейчас: {now_str}\n"
                            f"📈 OTT: {trend_info}\n\n"
                            f"⚠️ Не забудь стоп-лосс!"
                        )
                        
                        send_telegram(msg)
                        last_signals[symbol] = (signal, signal_ts)
                        print(f"[{now_str}] ✅ Сигнал отправлен: {symbol} {signal}")
                
                time.sleep(1) # Короткая пауза между парами
            except Exception as e:
                print(f"Ошибка в цикле для {symbol}: {e}")

        first_run = False
        time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    main(                ma, support = calculate_ott(closes, OTT_PERIOD, OTT_PERCENT)
                signal, signal_idx = get_current_signal(closes, ma, support)
                
                # ДОБАВЬ ЭТУ СТРОКУ:
                print(f"[{now}] {symbol} | Цена: {closes[-1]} | MA: {ma[-1]:.2f} | OTT: {support[-1]:.2f} | Diff: {ma[-1] - support[-1]:.2f}")
)
