# DFA Dynamic Fund Averaging Strategy

## Strategy Overview

DFA (Dynamic Fund Averaging) is an intelligent dollar-cost averaging strategy based on technical indicators. The strategy dynamically adjusts investment amounts based on price deviation from moving averages and automatically takes profits by reducing positions when target returns are achieved.

## Strategy Features

### 🎯 Core Characteristics
- **Dynamic Investment**: Adjusts investment amount based on price deviation
- **Auto Profit-Taking**: Automatically reduces 50% position at 75% return target
- **Cooling Mechanism**: 30-day cooldown period prevents overtrading
- **Precision Calculation**: Supports fractional shares with accurate cost and profit tracking

### 📊 Investment Logic
- **Regular Investment**: Invest every 14 days with $70 base amount
- **Deviation Adjustment**: Increase investment when price is below MA120, decrease when above
- **Risk Control**: Pause investment during extreme overvaluation

## Strategy Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| base_cash | 70 | Base investment amount per period (USD) |
| ma_period | 120 | Moving average period |
| investment_interval | 14 | Investment interval in days |
| target_return | 75 | Target return rate (%) |
| sell_ratio | 0.5 | Position reduction ratio |
| profit_taking_cooldown | 30 | Profit-taking cooldown days |

## Investment Multiplier Rules

| Deviation Range | Multiplier | Market Condition |
|-----------------|------------|------------------|
| ≤ -20% | 2.2 | Extreme Undervaluation |
| -20% ~ -10% | 1.8 | Significant Undervaluation |
| -10% ~ 0% | 1.4 | Normal Low |
| 0% ~ 5% | 1.0 | Normal Valuation |
| 5% ~ 15% | 0.5 | Normal High |
| 15% ~ 25% | 0.2 | Significant Overvaluation |
| > 25% | 0.0 | Extreme Overvaluation |

## File Structure

```
dfa_strategy/
├── dfa_strategy.py      # Main strategy code
├── README.md           # Documentation
└── requirements.txt    # Dependencies
```

## Installation

```bash
pip install backtrader pandas ccxt
```

## Usage

### Basic Usage
```python
# Run SOLUSDT backtest
python dfa_strategy.py

# Run other cryptocurrency backtests
run_dfa_binance_backtest(symbol='BTCUSDT', data_limit=1000)
run_dfa_binance_backtest(symbol='ETHUSDT', data_limit=1000)
```

### Custom Parameters
```python
# Modify in DFAStrategy params
params = (
    ('base_cash', 100),      # Change base investment amount
    ('investment_interval', 7),  # Change to weekly investment
    ('target_return', 50),   # Modify target return rate
    # ... other parameters
)
```

## Output Report

The strategy generates detailed backtest reports:

Backtest results for 1000 days of SOLUSDT data:

<img width="640" height="480" alt="Figure_0" src="https://github.com/user-attachments/assets/d3bac171-a646-4bef-94ec-51224da0f7e6" />

### 📊 Financial Overview
- Actual total investment amount
- Current position cost and value
- Realized profits and total sell amount
- Total return rate and annualized return based on actual investment

### 📈 Investment History
- Average deviation and investment multiplier
- Total investment statistics
- Maximum and minimum single investments

### 🎯 Profit-Taking Records
- Detailed records of each position reduction
- Profit-taking statistics and profit/investment ratio

## Strategy Advantages

### ✅ High Capital Efficiency
- Increase investment only during undervaluation
- Reduce or pause investment during overvaluation
- Automatically lock in profits

### ✅ Risk Control
- Avoid chasing rallies and selling in panic
- Cooling mechanism prevents excessive trading
- Accurate profit calculation based on actual investment cost

### ✅ Strong Adaptability
- Suitable for various cryptocurrencies
- Flexible parameter adjustment
- Supports different market environments

## Performance Metrics

The strategy calculates the following key metrics:
- **Total Return Rate**: Return based on actual investment cost
- **Annualized Return**: Annualized investment return
- **Profit/Investment Ratio**: Realized profit as percentage of total investment
- **Profit-Taking Count**: Number of position reduction operations

## Important Notes

1. **Applicable Scenarios**: This strategy employs a dollar-cost averaging approach, making it suitable primarily for spot market long-term investments
2. **Data Source**: Strategy uses Binance API for data, requires stable internet connection
3. **Proxy Settings**: Code includes proxy settings, adjust according to your network environment
4. **Backtest Limitations**: Historical data may not include all market conditions, actual performance may vary
5. **Risk Warning**: Cryptocurrency investment carries high risks, use only after fully understanding the risks

## Customization Suggestions

### 🎨 Parameter Optimization
- Adjust `target_return` based on different cryptocurrency volatility
- Modify `investment_interval` according to investment frequency
- Customize investment multiplier rules based on risk preference

### 🔧 Feature Extensions
- Add stop-loss mechanisms
- Support multiple cryptocurrency simultaneous investment
- Add email/SMS notification functionality

## Version History
- v1.0: Basic DFA strategy implementation
- v1.1: Added profit-taking cooling mechanism, optimized share calculation and financial reporting

## Future Development Plans

### Phase 1: Technical Indicator Enhancement (Short-term Goals)
1. RSI indicator integration
2. Multiple timeframe MA indicators
3. MACD indicator implementation

### Phase 2: Risk Management Enhancement (Medium-term Goals)
1. Dynamic stop-loss mechanisms
2. Position management optimization
3. Market regime identification

## Technical Support

For issues or suggestions, please submit an Issue or contact the development team.

---

**Disclaimer**: This strategy is for learning and research purposes only and does not constitute investment advice. Users should bear investment risks independently.
