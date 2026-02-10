"""
Stock Screener - Identifies stocks trading near their 52-week lows
Outputs results to data.json for the frontend to display
"""

import yfinance as yf
import json
from datetime import datetime
import concurrent.futures

# S&P 500 + popular stocks (~300 tickers)
TICKERS = [
    # Mega Cap Tech
    'AAPL', 'MSFT', 'GOOGL', 'GOOG', 'AMZN', 'META', 'NVDA', 'TSLA', 'AVGO', 'ORCL',
    # Financials
    'BRK-B', 'JPM', 'V', 'MA', 'BAC', 'WFC', 'GS', 'MS', 'SCHW', 'BLK',
    'AXP', 'C', 'USB', 'PNC', 'TFC', 'COF', 'BK', 'STT', 'FITB', 'KEY',
    'CFG', 'RF', 'HBAN', 'MTB', 'ZION', 'CMA', 'ALLY', 'DFS', 'SYF',
    # Healthcare
    'UNH', 'JNJ', 'LLY', 'PFE', 'MRK', 'ABBV', 'TMO', 'ABT', 'DHR', 'BMY',
    'AMGN', 'GILD', 'ISRG', 'CVS', 'CI', 'ELV', 'HUM', 'MCK', 'SYK', 'BDX',
    'ZTS', 'VRTX', 'REGN', 'MRNA', 'BIIB', 'ILMN', 'DXCM', 'IQV', 'MTD', 'A',
    'BSX', 'EW', 'IDXX', 'ALGN', 'HOLX', 'RMD', 'BAX', 'ZBH', 'TECH', 'MOH',
    # Consumer
    'HD', 'MCD', 'NKE', 'SBUX', 'TGT', 'LOW', 'TJX', 'COST', 'WMT', 'PG',
    'KO', 'PEP', 'PM', 'MO', 'MDLZ', 'CL', 'KMB', 'GIS', 'K', 'HSY',
    'DG', 'DLTR', 'ROST', 'BBY', 'ULTA', 'ORLY', 'AZO', 'EBAY', 'ETSY', 'W',
    'CMG', 'YUM', 'DPZ', 'DARDEN', 'MAR', 'HLT', 'WYNN', 'LVS', 'MGM', 'RCL',
    'CCL', 'NCLH', 'EXPE', 'BKNG', 'ABNB', 'LULU', 'GPS', 'ANF', 'DECK', 'CROX',
    # Tech & Software
    'CRM', 'ADBE', 'NOW', 'INTU', 'SNPS', 'CDNS', 'PANW', 'CRWD', 'FTNT', 'ZS',
    'WDAY', 'TEAM', 'DDOG', 'SNOW', 'MDB', 'NET', 'OKTA', 'ZM', 'DOCU', 'TWLO',
    'PLTR', 'PATH', 'U', 'RBLX', 'SHOP', 'SQ', 'COIN', 'HOOD', 'SOFI', 'AFRM',
    # Semiconductors
    'AMD', 'INTC', 'QCOM', 'TXN', 'MU', 'LRCX', 'AMAT', 'KLAC', 'ADI', 'NXPI',
    'MRVL', 'ON', 'SWKS', 'QRVO', 'MPWR', 'MCHP', 'ENTG', 'TER', 'COHR',
    # Industrial
    'CAT', 'DE', 'HON', 'UPS', 'UNP', 'RTX', 'LMT', 'BA', 'GE', 'MMM',
    'EMR', 'ITW', 'ETN', 'PH', 'ROK', 'CMI', 'PCAR', 'FAST', 'GWW', 'SWK',
    'IR', 'DOV', 'AME', 'OTIS', 'CARR', 'JCI', 'TT', 'GNRC', 'XYL', 'IEX',
    # Energy
    'XOM', 'CVX', 'COP', 'EOG', 'SLB', 'MPC', 'PSX', 'VLO', 'OXY', 'PXD',
    'DVN', 'FANG', 'HES', 'HAL', 'BKR', 'KMI', 'WMB', 'OKE', 'TRGP', 'ET',
    # Utilities
    'NEE', 'DUK', 'SO', 'D', 'AEP', 'EXC', 'SRE', 'XEL', 'ED', 'WEC',
    'ES', 'AWK', 'DTE', 'PPL', 'FE', 'AEE', 'CMS', 'CNP', 'NI', 'EVRG',
    # REITs
    'PLD', 'AMT', 'EQIX', 'CCI', 'PSA', 'SPG', 'O', 'WELL', 'DLR', 'AVB',
    'EQR', 'VTR', 'ARE', 'MAA', 'UDR', 'ESS', 'INVH', 'SUI', 'ELS', 'CPT',
    # Telecom & Media
    'DIS', 'CMCSA', 'NFLX', 'T', 'VZ', 'TMUS', 'CHTR', 'WBD', 'PARA', 'FOX',
    'FOXA', 'LYV', 'MTCH', 'EA', 'TTWO', 'ATVI',
    # Other
    'PYPL', 'FIS', 'FISV', 'GPN', 'ADP', 'PAYX', 'CTAS', 'SPGI', 'MCO', 'ICE',
    'CME', 'MSCI', 'NDAQ', 'CBOE', 'MKTX', 'TRV', 'CB', 'PGR', 'ALL', 'MET',
    'PRU', 'AFL', 'AIG', 'HIG', 'LNC', 'GL', 'FNF', 'CINF', 'WRB', 'L',
    'APD', 'LIN', 'SHW', 'ECL', 'DD', 'DOW', 'LYB', 'PPG', 'NEM', 'FCX',
    'GOLD', 'NUE', 'STLD', 'CLF', 'X', 'AA', 'ATI', 'RS', 'CMC'
]

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
