import requests
import time
from datetime import datetime

# === НАСТРОЙКИ ===
# Замени токен, если создашь новый, но пока оставляю твой
TELEGRAM_TOKEN = "8633747198:AAGnMpqoX8TiX8ljbFAmfBF3YBE9YEKWWHI"
CHAT_ID = "6825257186"
OTT_PERIOD = 7
OTT_PERCENT = 1.4
CHECK_INTERVAL = 60 * 5  # проверка каждые 5 минут

# === СПИСОК ПАР ===
SYMBOLS = ["BTCUSDT", "ZILUSDT", "GMTUSDT", "RUNEUSDT", "XRPUSDT", "LTCUSDT"]

def send_telegram(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    data = {"chat_id": CHAT_ID, "text": message, "parse_mode": "HTML"}
    try:
        requests.post(url, data=data, timeout=10)
    except Exception as e:
        print(f"Ошибка ТГ: {e}")

def get_candles(symbol):
    # ИСПОЛЬЗУЕМ FAPI (ФЬЮЧЕРСЫ), как на твоем графике
    url = "https://fapi.binance.com/fapi/v1/klines"
    params = {"symbol": symbol, "interval": "1h", "limit": 300}
    try:
        r = requests.get(url, params=params, timeout=10)
        data = r.json()
        closes = [float(c[4]) for c in data]
        timestamps = [int(c[0]) for c in data]
        return closes, timestamps
    except Exception as e:
        print(f"Ошибка данных {symbol}: {e}")
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
    for i in range(len(closes) - 1, len(closes) - 4, -1):
        if i < 1 or ma[i] is None or support[i] is None or support[i-1] is None:
            continue
        if ma[i-1] >= support[i-1] and ma[i] < support[i]:
            return "SELL", i
        if ma[i-1] <= support[i-1] and ma[i] > support[i]:
            return "BUY", i
    return None, None

def main():
    print("🤖 Бот запущен на фьючерсах!")
    send_telegram("🤖 <b>Бот запущен!</b>\nМониторинг фьючерсов Binance\nТаймфрейм: 1H | OTT (7, 1.4)")
    
    last_signals = {symbol: (None, None) for symbol in SYMBOLS}
    
    while True:
        now = datetime.now().strftime("%H:%M %d.%m.%Y")
        for symbol in SYMBOLS:
            try:
                closes, timestamps = get_candles(symbol)
                if closes is None: continue
                
                ma, support = calculate_ott(closes, OTT_PERIOD, OTT_PERCENT)
                signal, signal_idx = get_current_signal(closes, ma, support)
                
                # ТУТ ПРОВЕРКА В КОНСОЛИ
                diff = ma[-1] - support[-1]
                print(f"[{now}] {symbol} | Цена: {closes[-1]} | Diff: {diff:.2f} | Signal: {signal}")

                if signal:
                    signal_ts = timestamps[signal_idx]
                    last_s, last_ts = last_signals[symbol]
                    
                    if signal != last_s or signal_ts != last_ts:
                        pair = symbol.replace("USDT", "/USDT")
                        emoji = "🟢" if signal == "BUY" else "🔴"
                        msg = f"{emoji} <b>СИГНАЛ: {signal}</b>\n\n📊 Пара: {pair}\n💰 Цена: {closes[-1]}\n⏰ Время: {now}"
                        send_telegram(msg)
                        last_signals[symbol] = (signal, signal_ts)
                
                time.sleep(1)
            except Exception as e:
                print(f"Ошибка {symbol}: {e}")
        
        time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    main()
