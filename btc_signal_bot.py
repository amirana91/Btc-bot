import requests
import time
from datetime import datetime

# === НАСТРОЙКИ ===
TELEGRAM_TOKEN = "8633747198:AAGnMpqoX8TiX8ljbFAmfBF3YBE9YEKWWHI"
CHAT_ID = "6825257186"
OTT_PERIOD = 7
OTT_PERCENT = 1.4
CHECK_INTERVAL = 60 * 5 

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
    # Используем Bybit V5 API (Linear Futures)
    url = "https://api.bybit.com/v5/market/kline"
    params = {
        "category": "linear",
        "symbol": symbol,
        "interval": "60", 
        "limit": 200
    }
    try:
        r = requests.get(url, params=params, timeout=10)
        res = r.json()
        if res.get("retCode") == 0:
            # Bybit присылает данные от новых к старым, разворачиваем их
            list_candles = list(reversed(res["result"]["list"]))
            closes = [float(c[4]) for c in list_candles]
            timestamps = [int(c[0]) for c in list_candles]
            return closes, timestamps
        else:
            print(f"❌ Bybit Error {symbol}: {res.get('retMsg')}")
            return None, None
    except Exception as e:
        print(f"❌ Ошибка сети {symbol}: {e}")
        return None, None

def wwma(prices, period):
    if len(prices) < period: return [None] * len(prices)
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
            # Математика OTT (Trailing Stop на основе MA)
            if ma[i] > support[i-1]:
                support[i] = max(longstop, support[i-1])
            else:
                support[i] = min(shortstop, support[i-1])
    return ma, support

def get_current_signal(closes, ma, support):
    # Проверяем последние 5 свечей
    for i in range(len(closes) - 1, len(closes) - 6, -1):
        if i < 1 or ma[i] is None or ma[i-1] is None or support[i] is None or support[i-1] is None:
            continue
            
        if ma[i-1] >= support[i-1] and ma[i] < support[i]:
            return "SELL", i
        if ma[i-1] <= support[i-1] and ma[i] > support[i]:
            return "BUY", i
            
    return None, None

def main():
    print("🤖 Бот запущен (Bybit API)")
    send_telegram("🤖 <b>Бот запущен на Bybit!</b>\nМониторинг 1H | OTT (7, 1.4)")
    
    last_signals = {symbol: (None, None) for symbol in SYMBOLS}
    
    while True:
        now_str = datetime.now().strftime("%H:%M %d.%m.%Y")
        for symbol in SYMBOLS:
            try:
                closes, timestamps = get_candles(symbol)
                if not closes: continue
                
                ma, support = calculate_ott(closes, OTT_PERIOD, OTT_PERCENT)
                signal, signal_idx = get_current_signal(closes, ma, support)
                
                # Показываем в логах Railway, что бот живой
                diff = ma[-1] - support[-1]
                print(f"[{now_str}] {symbol}: {closes[-1]} | Diff: {diff:.2f} | Signal: {signal}")

                if signal:
                    signal_ts = timestamps[signal_idx]
                    last_s, last_ts = last_signals[symbol]
                    
                    if signal != last_s or signal_ts != last_ts:
                        pair = symbol.replace("USDT", "/USDT")
                        emoji = "🟢" if signal == "BUY" else "🔴"
                        msg = f"{emoji} <b>СИГНАЛ: {signal}</b>\n\n📊 Пара: {pair}\n💰 Цена: {closes[-1]}"
                        send_telegram(msg)
                        last_signals[symbol] = (signal, signal_ts)
                
                time.sleep(1) 
            except Exception as e:
                print(f"Ошибка {symbol}: {e}")
        
        time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    main()
