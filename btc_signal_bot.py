import requests
import numpy as np
import time
from datetime import datetime

# === НАСТРОЙКИ ===
TELEGRAM_TOKEN = "8633747198:AAGnMpqoX8TiX8ljbFAmfBF3YBE9YEKWWHI"
CHAT_ID = "6825257186"
SYMBOL = "BTCUSDT"
INTERVAL = "1h"
OTT_PERIOD = 7
OTT_PERCENT = 1.4
CHECK_INTERVAL = 60 * 5  # проверка каждые 5 минут

def send_telegram(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    data = {"chat_id": CHAT_ID, "text": message, "parse_mode": "HTML"}
    try:
        requests.post(url, data=data)
    except Exception as e:
        print(f"Ошибка отправки: {e}")

def get_candles():
    url = "https://api.binance.com/api/v3/klines"
    params = {"symbol": SYMBOL, "interval": INTERVAL, "limit": 100}
    try:
        r = requests.get(url, params=params)
        data = r.json()
        closes = [float(c[4]) for c in data]
        return closes
    except Exception as e:
        print(f"Ошибка получения данных: {e}")
        return None

def wwma(prices, period):
    """Weighted Wilder Moving Average"""
    result = [None] * len(prices)
    result[period - 1] = sum(prices[:period]) / period
    k = 1.0 / period
    for i in range(period, len(prices)):
        result[i] = prices[i] * k + result[i-1] * (1 - k)
    return result

def calculate_ott(closes, period, percent):
    """OTT - Optimized Trend Tracker"""
    ma = wwma(closes, period)
    
    # Убираем None значения
    valid_start = period - 1
    
    ott = [None] * len(closes)
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
        
        ott[i] = support[i]
    
    return ma, ott, support

def check_signal(closes, ma, ott, support):
    """Проверка сигнала на пересечение"""
    if len(closes) < 3:
        return None
    
    # Берём последние 2 свечи
    i = len(closes) - 2  # предыдущая (закрытая)
    
    if support[i] is None or support[i-1] is None:
        return None
    if ma[i] is None or ma[i-1] is None:
        return None
    
    # BUY: MA пересекает Support снизу вверх
    if ma[i-1] < support[i-1] and ma[i] > support[i]:
        return "BUY"
    
    # SELL: MA пересекает Support сверху вниз
    if ma[i-1] > support[i-1] and ma[i] < support[i]:
        return "SELL"
    
    return None

def main():
    print("🤖 Бот запущен! Мониторинг BTC/USDT...")
    send_telegram("🤖 <b>Бот запущен!</b>\n\nМониторинг BTC/USDT 1H\nИндикатор: OTT (Period=7, Percent=1.4)\n\nЖду сигналов... 👀")
    
    last_signal = None
    
    while True:
        try:
            closes = get_candles()
            if closes is None:
                time.sleep(60)
                continue
            
            ma, ott, support = calculate_ott(closes, OTT_PERIOD, OTT_PERCENT)
            signal = check_signal(closes, ma, ott, support)
            
            current_price = closes[-1]
            now = datetime.now().strftime("%H:%M %d.%m.%Y")
            
            print(f"[{now}] Цена: {current_price:.2f} | Сигнал: {signal}")
            
            if signal and signal != last_signal:
                if signal == "BUY":
                    msg = (
                        f"🟢 <b>СИГНАЛ: LONG (BUY)</b>\n\n"
                        f"📊 Пара: BTC/USDT\n"
                        f"💰 Цена: <b>{current_price:.2f}$</b>\n"
                        f"⏰ Время: {now}\n"
                        f"📈 OTT пересечение: MA ↑ Support\n\n"
                        f"⚠️ Не забудь поставить стоп-лосс!"
                    )
                else:
                    msg = (
                        f"🔴 <b>СИГНАЛ: SHORT (SELL)</b>\n\n"
                        f"📊 Пара: BTC/USDT\n"
                        f"💰 Цена: <b>{current_price:.2f}$</b>\n"
                        f"⏰ Время: {now}\n"
                        f"📉 OTT пересечение: MA ↓ Support\n\n"
                        f"⚠️ Не забудь поставить стоп-лосс!"
                    )
                
                send_telegram(msg)
                last_signal = signal
                print(f"✅ Сигнал отправлен: {signal}")
            
            time.sleep(CHECK_INTERVAL)
            
        except Exception as e:
            print(f"Ошибка: {e}")
            time.sleep(60)

if __name__ == "__main__":
    main()
