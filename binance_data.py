from binance.client import Client

API_KEY = "UJcsGnr8pMPpENtDnBEkJRRrnM16otXTJMzHfVZmzKqjFIPmz0KKd8Dg7gX0yL46"
API_SECRET = "ZIylSO5Z40Gb59j7ALfLwEmdauJUZBtbE0chv6zZLNXzxzcunwQyk7M5Dq4ibQ1Z"

client = Client(API_KEY, API_SECRET)

def get_price(symbol="BTCUSDT"):
    ticker = client.get_symbol_ticker(symbol=symbol)
    return float(ticker["price"])


def get_klines(symbol="BTCUSDT", interval="5m", limit=100):
    klines = client.get_klines(
        symbol=symbol,
        interval=interval,
        limit=limit
    )
    
    closes = [float(k[4]) for k in klines]
    return closes
