import os
import ccxt
import pandas as pd
import ta
import requests

# Telegram config from environment variables
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

def send_telegram_message(text):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("Telegram token or chat ID not set. Skipping alert.")
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    data = {"chat_id": TELEGRAM_CHAT_ID, "text": text, "parse_mode": "Markdown"}
    try:
        response = requests.post(url, data=data)
        if response.status_code == 200:
            print("Alert sent!")
        else:
            print(f"Failed to send alert: {response.text}")
    except Exception as e:
        print(f"Error sending telegram message: {e}")

def analyze_symbol(exchange, symbol):
    try:
        bars = exchange.fetch_ohlcv(symbol, '5m', limit=200)
        df = pd.DataFrame(bars, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['EMA50'] = ta.trend.ema_indicator(df['close'], window=50)
        df['EMA200'] = ta.trend.ema_indicator(df['close'], window=200)
        df['RSI'] = ta.momentum.rsi(df['close'], window=14)
        df['MACD'] = ta.trend.macd(df['close'])
        df['MACD_SIGNAL'] = ta.trend.macd_signal(df['close'])
        latest = df.iloc[-1]
        avg_volume = df['volume'].mean()

        RSI_LONG = 40
        RSI_SHORT = 60
        VOLUME_MULTIPLIER = 1.2

        if (
            latest['EMA50'] > latest['EMA200'] and
            latest['RSI'] < RSI_LONG and
            latest['MACD'] > latest['MACD_SIGNAL'] and
            latest['volume'] > VOLUME_MULTIPLIER * avg_volume
        ):
            return 'LONG', latest['volume'] / avg_volume
        elif (
            latest['EMA50'] < latest['EMA200'] and
            latest['RSI'] > RSI_SHORT and
            latest['MACD'] < latest['MACD_SIGNAL'] and
            latest['volume'] > VOLUME_MULTIPLIER * avg_volume
        ):
            return 'SHORT', latest['volume'] / avg_volume
        return None
    except Exception as e:
        print(f"Error analyzing {symbol}: {e}")
        return None

def main():
    exchange = ccxt.binance()
    markets = exchange.load_markets()
    usdt_pairs = sorted(
        [s for s, m in markets.items() if s.endswith('/USDT') and m.get('active', False)],
        key=lambda s: float(markets[s]['info'].get('quoteVolume', 0)),
        reverse=True
    )[:30]  # top 30 pairs for faster run

    signals = []
    for pair in usdt_pairs:
        result = analyze_symbol(exchange, pair)
        if result:
            signals.append((pair, result[0], result[1]))

    if signals:
        signals.sort(key=lambda x: x[2], reverse=True)
        message_lines = ["🚀 *Crypto Signal Alert* 🚀\n"]
        for pair, signal, strength in signals[:10]:
            message_lines.append(f"{pair}: {signal} (Strength: {strength:.2f})")
        message = "\n".join(message_lines)
        send_telegram_message(message)
    else:
        print("No signals found this run.")

if __name__ == "__main__":
    main()
