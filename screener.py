"""
Stock Screener - Identifies stocks trading near their 52-week lows
Outputs results to data.json for the frontend to display
"""

import yfinance as yf
import pandas as pd
import requests
import json
from io import StringIO
from datetime import datetime
import concurrent.futures

_WIKI_HEADERS = {'User-Agent': 'stock-screener/1.0 (https://github.com/RFrisch/stock-screener)'}


def _read_wiki_tables(url):
    resp = requests.get(url, headers=_WIKI_HEADERS, timeout=30)
    resp.raise_for_status()
    return pd.read_html(StringIO(resp.text))


def get_tickers():
    """Fetch S&P 500 constituents plus any Nasdaq 100 names not already in the S&P 500."""
    sp500 = _read_wiki_tables('https://en.wikipedia.org/wiki/List_of_S%26P_500_companies')[0]
    sp500_tickers = set(sp500['Symbol'].astype(str))

    nasdaq100 = _read_wiki_tables('https://en.wikipedia.org/wiki/List_of_NASDAQ-100_companies')[0]
    nasdaq100_tickers = set(nasdaq100['Ticker'].astype(str))

    combined = sp500_tickers | nasdaq100_tickers
    # yfinance uses '-' instead of '.' in class-share tickers (e.g., BRK.B -> BRK-B)
    return sorted(t.replace('.', '-') for t in combined)


TICKERS = get_tickers()

# Threshold: stock is "cheap" if within X% of 52-week low
THRESHOLD_PERCENT = 15


def fetch_stock_data(ticker):
    """Fetch stock data and calculate proximity to 52-week low."""
    try:
        stock = yf.Ticker(ticker)
        hist = stock.history(period="1y")

        if hist.empty or len(hist) < 20:
            return None

        current_price = hist['Close'].iloc[-1]
        low_52week = hist['Low'].min()
        high_52week = hist['High'].max()

        # Calculate how far above the 52-week low (as percentage)
        pct_above_low = ((current_price - low_52week) / low_52week) * 100

        # Calculate position in 52-week range (0% = at low, 100% = at high)
        range_position = ((current_price - low_52week) / (high_52week - low_52week)) * 100

        info = stock.info

        return {
            'ticker': ticker,
            'name': info.get('shortName', ticker),
            'sector': info.get('sector', 'N/A'),
            'current_price': round(current_price, 2),
            'low_52week': round(low_52week, 2),
            'high_52week': round(high_52week, 2),
            'pct_above_low': round(pct_above_low, 2),
            'range_position': round(range_position, 2),
            'pe_ratio': info.get('trailingPE'),
            'forward_pe': info.get('forwardPE'),
            'market_cap': info.get('marketCap'),
            'dividend_yield': info.get('dividendYield')
        }
    except Exception as e:
        print(f"Error fetching {ticker}: {e}")
        return None


def format_market_cap(value):
    """Format market cap for display."""
    if value is None:
        return 'N/A'
    if value >= 1e12:
        return f'${value/1e12:.2f}T'
    if value >= 1e9:
        return f'${value/1e9:.2f}B'
    if value >= 1e6:
        return f'${value/1e6:.2f}M'
    return f'${value:,.0f}'


def main():
    print(f"Fetching data for {len(TICKERS)} stocks...")

    # Fetch data in parallel
    results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        future_to_ticker = {executor.submit(fetch_stock_data, ticker): ticker for ticker in TICKERS}
        for future in concurrent.futures.as_completed(future_to_ticker):
            result = future.result()
            if result:
                results.append(result)

    # Filter stocks near 52-week low
    cheap_stocks = [s for s in results if s['pct_above_low'] <= THRESHOLD_PERCENT]
    cheap_stocks.sort(key=lambda x: x['pct_above_low'])

    # Format for output
    for stock in cheap_stocks:
        stock['market_cap_fmt'] = format_market_cap(stock['market_cap'])
        stock['pe_ratio_fmt'] = f"{stock['pe_ratio']:.2f}" if stock['pe_ratio'] else 'N/A'
        stock['forward_pe_fmt'] = f"{stock['forward_pe']:.2f}" if stock['forward_pe'] else 'N/A'
        stock['dividend_yield_fmt'] = f"{stock['dividend_yield']:.2f}%" if stock['dividend_yield'] else 'N/A'

    output = {
        'last_updated': datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC'),
        'threshold_percent': THRESHOLD_PERCENT,
        'total_screened': len(results),
        'stocks_found': len(cheap_stocks),
        'stocks': cheap_stocks
    }

    # Save to JSON in current directory
    with open('data.json', 'w') as f:
        json.dump(output, f, indent=2)

    print(f"Found {len(cheap_stocks)} stocks within {THRESHOLD_PERCENT}% of 52-week low")
    print(f"Results saved to data.json")


if __name__ == '__main__':
    main()
