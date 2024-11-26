# Taylor Trading Technique (TTT) Calculator

A Python-based calculator implementing George Douglas Taylor's trading technique for market analysis and trading signals.

## Features

- Fetch and display real-time market data
- Identify trading cycle days (Buy Day, Sell Day, Short Sale Day)
- Calculate objective points for trading decisions
- Track and display trading signals
- Historical data analysis capabilities

## Installation

1. Clone this repository
2. Install required dependencies:
```bash
pip install -r requirements.txt
```

## Usage

Run the application:
```bash
python ttt_calculator.py
```

1. Enter a stock symbol in the input field
2. Click "Fetch Data" to load market data
3. The application will display:
   - Price data (Open, High, Low, Close)
   - Trading day classification
   - Trading signals
   - Objective points for trading decisions

## Trading Day Classifications

- **Buy Day**: Market tends to make a low and rally
- **Sell Day**: Market tends to make a high and decline
- **Short Sale Day**: Market tends to continue lower

## Dependencies

- pandas: Data manipulation and analysis
- PyQt6: GUI framework
- yfinance: Market data fetching
- matplotlib: Data visualization
- numpy: Numerical computations
