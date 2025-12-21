# Example Jupyter Notebook for Portfolio Analysis

This notebook is located at `notebooks/portfolio_analysis_example.ipynb` when you create it in Jupyter Lab.

## Cells to include:

### Cell 1: Setup

```python
import sys
sys.path.append('/opt/spark-apps')

from src.iceberg.catalog import IcebergCatalog
from src.analytics.portfolio_performance import PortfolioAnalyzer
from src.analytics.technical_indicators import TechnicalIndicators
from src.ingestion.stock_ingestion import StockDataIngestion
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

# Set plotting style
sns.set_style("darkgrid")
%matplotlib inline
```

### Cell 2: Query Stock Data

```python
# Query stock prices from PostgreSQL
from src.utils.supabase_client import get_postgres_engine
import pandas as pd
from sqlalchemy import text

engine = get_postgres_engine()

with engine.connect() as conn:
    result = conn.execute(text("""
        SELECT
            s.symbol,
            sp.timestamp,
            sp.close,
            sp.volume
        FROM stock_prices sp
        JOIN stocks s ON sp.stock_id = s.id
        WHERE s.symbol = 'AAPL'
        ORDER BY sp.timestamp DESC
        LIMIT 100
    """))
    df = pd.DataFrame(result.fetchall(),
                     columns=['symbol', 'timestamp', 'close', 'volume'])

print(f"Retrieved {len(df)} records")
df.head()
```

### Cell 3: Plot Price Chart

```python
import matplotlib.pyplot as plt

plt.figure(figsize=(12, 6))
plt.plot(df['timestamp'], df['close'])
plt.title('AAPL Stock Price')
plt.xlabel('Date')
plt.ylabel('Price ($)')
plt.grid(True)
plt.xticks(rotation=45)
plt.tight_layout()
plt.show()

# Convert to Pandas for visualization
df = stock_prices.toPandas()
df['timestamp'] = pd.to_datetime(df['timestamp'])
df = df.sort_values('timestamp')

# Plot
plt.figure(figsize=(12, 6))
plt.plot(df['timestamp'], df['close'])
plt.title('AAPL Stock Price')
plt.xlabel('Date')
plt.ylabel('Close Price ($)')
plt.xticks(rotation=45)
plt.tight_layout()
plt.show()
```

### Cell 4: Portfolio Analysis

```python
# Analyze a portfolio (replace with your portfolio ID)
portfolio_id = "your-portfolio-id"
analyzer = PortfolioAnalyzer(portfolio_id)

# Calculate current value
value = analyzer.calculate_portfolio_value()
print(f"Total Portfolio Value: ${value['total_value']:,.2f}")
print(f"Total Cost: ${value['total_cost']:,.2f}")
print(f"Unrealized Gain: ${value['unrealized_gain']:,.2f} ({value['unrealized_gain_pct']:.2f}%)")
```

### Cell 5: Holdings Breakdown

```python
# Get holdings details
if value['holdings']:
    holdings_df = pd.DataFrame([
        {
            'Symbol': h.stock_symbol,
            'Quantity': float(h.total_quantity),
            'Avg Cost': float(h.average_cost),
            'Current Price': float(h.current_price),
            'Market Value': float(h.market_value),
            'Gain/Loss': float(h.unrealized_gain),
            'Gain/Loss %': float(h.unrealized_gain_pct)
        }
        for h in value['holdings']
    ])

    print(holdings_df.to_string())

    # Pie chart of holdings
    plt.figure(figsize=(10, 6))
    plt.pie(holdings_df['Market Value'], labels=holdings_df['Symbol'], autopct='%1.1f%%')
    plt.title('Portfolio Allocation')
    plt.show()
```

### Cell 6: Risk Metrics

```python
# Calculate risk metrics
risk = analyzer.calculate_risk_metrics(
    start_date='2024-01-01'
)

print(f"Volatility: {risk['volatility']:.2f}%")
print(f"Sharpe Ratio: {risk['sharpe_ratio']:.2f}")
print(f"Avg Annual Return: {risk['avg_annual_return']:.2f}%")
```

### Cell 7: Technical Indicators

```python
# Calculate technical indicators for a stock
indicators_calc = TechnicalIndicators()
indicators = indicators_calc.calculate_all_indicators('AAPL')

# Display recent indicators
indicators_df = indicators.toPandas()
indicators_df = indicators_df.sort_values('timestamp', ascending=False).head(20)
print(indicators_df[['timestamp', 'close', 'sma_20', 'sma_50', 'rsi_14']].to_string())
```

## Usage

1. Start Jupyter Lab: `http://localhost:8888`
2. Create a new notebook
3. Copy these cells and execute them in order
4. Modify portfolio_id and stock symbols as needed
