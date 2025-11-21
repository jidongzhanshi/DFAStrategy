import backtrader as bt
import pandas as pd
import ccxt
from datetime import datetime, timedelta
import time

class DFAStrategy(bt.Strategy):
    """
    动态定投策略 (Dynamic Fund Averaging)
    基于价格与移动平均线的偏离度来动态调整投资金额
    """
    
    params = (
        ('base_cash', 70),  # 每期基础投资金额
        ('ma_period', 120),  # 移动平均线周期
        ('investment_interval', 14),  # 投资间隔为14天
        ('target_return', 75),  # 目标收益率75%减仓
        ('sell_ratio', 0.5),  # 减仓比例50%
        ('profit_taking_cooldown', 30),  #减仓冷却天数
        ('printlog', True),  # 打印交易日志
    )
    
    def __init__(self):
        # 计算120日移动平均线
        self.ma120 = bt.indicators.SMA(self.datas[0], period=self.params.ma_period)
        
        # 投资计数器
        self.investment_count = 0
        self.last_investment_date = None
        
        # 减仓冷却控制
        self.last_profit_taking_date = None
        
        # 记录投资历史
        self.investment_history = []
        
        # 持仓统计
        self.total_invested = 0.0  # 总投资成本
        self.total_shares = 0.0    # 总持有份额
        self.profit_history = []   # 利润记录
        self.total_sell_amount = 0.0  # 总卖出金额

    def next(self):
        current_date = self.datas[0].datetime.date(0)
        
        # 检查减仓条件
        self.check_profit_taking()
        
        if self.last_investment_date is None:
            # 第一次投资
            self.execute_investment()
            return
            
        days_since_last = (current_date - self.last_investment_date).days
        if days_since_last >= self.params.investment_interval:
            self.execute_investment()

    def execute_investment(self):
        """执行动态投资决策"""
        current_price = self.datas[0].close[0]
        ma120_value = self.ma120[0]
        
        # 检查数据是否准备好
        if ma120_value == 0 or pd.isna(ma120_value):
            return
            
        # 计算偏离度
        deviation = (current_price - ma120_value) / ma120_value * 100
        
        # 根据偏离度确定投资乘数
        multiplier = self.get_investment_multiplier(deviation)
        
        # 计算本次投资金额
        investment_amount = self.params.base_cash * multiplier
        
        # 确保有足够现金
        if investment_amount > self.broker.getcash():
            investment_amount = self.broker.getcash()
            
        if investment_amount > 0:
            # 计算购买数量（允许小数，保留4位）
            size = round(investment_amount / current_price, 4)
            
            if size > 0:
                # 计算实际使用的金额（避免因小数精度损失）
                actual_invested = size * current_price
                
                self.buy(size=size)
                
                # 使用实际买入金额记录成本
                self.total_invested += actual_invested
                self.total_shares += size
                
                # 记录投资信息
                self.investment_count += 1
                self.last_investment_date = self.datas[0].datetime.date(0)
                
                investment_info = {
                    'date': self.last_investment_date,
                    'price': current_price,
                    'ma120': ma120_value,
                    'deviation': deviation,
                    'multiplier': multiplier,
                    'amount': actual_invested,  # 记录实际使用金额
                    'shares': size
                }
                self.investment_history.append(investment_info)
                
                if self.params.printlog:
                    self.log(f'第{self.investment_count}期投资: 价格${current_price:.2f}, '
                           f'偏离度{deviation:.1f}%, 乘数{multiplier:.1f}, '
                           f'金额${actual_invested:.2f}, 份额{size:.4f}')

    def check_profit_taking(self):
        """检查减仓条件（带冷却机制）"""
        if self.total_shares > 0:
            current_date = self.datas[0].datetime.date(0)
            current_price = self.datas[0].close[0]
            current_value = self.total_shares * current_price
            
            # 计算当前收益率
            if self.total_invested > 0:
                current_return = (current_value - self.total_invested) / self.total_invested * 100
                
                # 检查减仓冷却期
                if self.last_profit_taking_date is not None:
                    days_since_last_taking = (current_date - self.last_profit_taking_date).days
                    if days_since_last_taking < self.params.profit_taking_cooldown:
                        return  # 还在冷却期内，不执行减仓
                
                # 如果收益率达到目标，减仓指定比例
                if current_return >= self.params.target_return:
                    # 允许小数份额卖出
                    sell_shares = round(self.total_shares * self.params.sell_ratio, 4)
                    
                    if sell_shares > 0:
                        self.sell(size=sell_shares)
                        
                        # 计算卖出部分的成本和利润
                        sell_amount = sell_shares * current_price
                        cost_of_sold = (sell_shares / self.total_shares) * self.total_invested
                        profit = sell_amount - cost_of_sold
                        
                        # 更新持仓信息
                        self.total_shares -= sell_shares
                        self.total_invested -= cost_of_sold
                        self.total_sell_amount += sell_amount
                        
                        # 记录本次减仓日期
                        self.last_profit_taking_date = current_date
                        
                        # 记录利润信息
                        profit_info = {
                            'date': current_date,
                            'price': current_price,
                            'return_percent': current_return,
                            'shares_sold': sell_shares,
                            'amount_received': sell_amount,
                            'cost_of_sold': cost_of_sold,
                            'profit': profit
                        }
                        self.profit_history.append(profit_info)
                        
                        if self.params.printlog:
                            self.log(f'🎯 减仓卖出: 收益率{current_return:.1f}%, '
                                   f'价格${current_price:.2f}, 卖出{sell_shares:.4f}份额, '
                                   f'获得${sell_amount:.2f}, 利润${profit:.2f}')

    def get_investment_multiplier(self, deviation):
        """根据偏离度返回投资乘数"""
        if deviation <= -20:    # 极度低估
            return 2.2
        elif deviation <= -10:  # 显著低估
            return 1.8
        elif deviation <= 0:    # 正常偏低
            return 1.4
        elif deviation <= 5:    # 正常估值
            return 1.0
        elif deviation <= 15:   # 正常偏高
            return 0.5
        elif deviation <= 25:   # 显著高估
            return 0.2
        else:                   # 极度高估
            return 0.0

    def log(self, txt, dt=None):
        '''日志函数'''
        dt = dt or self.datas[0].datetime.date(0)
        print(f'{dt.isoformat()}: {txt}')

    def stop(self):
        """策略结束时的分析"""
        print('\n' + '='*60)
        print('📊 DFA策略回测详细报告 (基于实际投资成本)')
        print('='*60)
        
        # 计算基于实际投资成本的财务数据
        current_holdings_value = round(self.total_shares * self.datas[0].close[0], 2)
        total_realized_profit = sum([p['profit'] for p in self.profit_history])
        total_assets_from_investment = current_holdings_value + self.total_sell_amount
        total_investment = sum([inv['amount'] for inv in self.investment_history])
        
        # 基于实际投资的总回报率
        if total_investment > 0:
            total_return_percent = ((total_assets_from_investment - total_investment) / total_investment) * 100
        else:
            total_return_percent = 0
        
        print(f'总定投期数: {self.investment_count}')
        print(f'当前持仓价值: ${current_holdings_value:.2f}')
        
        print(f'\n💰 财务概览 (基于实际投资):')
        print(f'  实际总投资: ${total_investment:.2f}')
        print(f'  当前持仓成本: ${self.total_invested:.2f}')
        print(f'  当前持仓价值: ${current_holdings_value:.2f}')
        print(f'  已实现利润: ${total_realized_profit:.2f}')
        print(f'  总卖出金额: ${self.total_sell_amount:.2f}')
        print(f'  总资产(投资产生): ${total_assets_from_investment:.2f}')
        print(f'  基于投资的总回报率: {total_return_percent:.2f}%')
        
        # 计算年化回报率
        if self.investment_history:
            first_date = self.investment_history[0]['date']
            last_date = self.datas[0].datetime.date(0)
            days_total = (last_date - first_date).days
            years_total = days_total / 365.25
            
            if years_total > 0:
                annual_return = ((1 + total_return_percent/100) ** (1/years_total) - 1) * 100
                print(f'  年化回报率: {annual_return:.2f}%')
        
        # 投资历史概览
        if self.investment_history:
            df = pd.DataFrame(self.investment_history)
            print(f"\n📈 投资历史概览:")
            print(f"  平均偏离度: {df['deviation'].mean():.1f}%")
            print(f"  平均投资乘数: {df['multiplier'].mean():.2f}")
            print(f"  总投资金额: ${df['amount'].sum():.2f}")
            print(f"  最大单次投资: ${df['amount'].max():.2f}")
            print(f"  最小单次投资: ${df['amount'].min():.2f}")
        
        # 减仓记录
        if self.profit_history:
            print(f"\n🎯 减仓记录 (冷却期{self.params.profit_taking_cooldown}天):")
            total_sold_amount = 0
            total_profit = 0
            
            for i, profit in enumerate(self.profit_history, 1):
                print(f"  第{i}次减仓: {profit['date']}")
                print(f"    └─ 收益率: {profit['return_percent']:.1f}%")
                print(f"    └─ 价格: ${profit['price']:.2f}")
                print(f"    └─ 卖出金额: ${profit['amount_received']:.2f}")
                print(f"    └─ 对应成本: ${profit['cost_of_sold']:.2f}")
                print(f"    └─ 利润: ${profit['profit']:.2f}")
                
                total_sold_amount += profit['amount_received']
                total_profit += profit['profit']
            
            print(f"\n  💰 减仓统计:")
            print(f"    总减仓次数: {len(self.profit_history)}")
            print(f"    总卖出金额: ${total_sold_amount:.2f}")
            print(f"    总实现利润: ${total_profit:.2f}")
            if total_investment > 0:
                profit_ratio = (total_profit / total_investment) * 100
                print(f"    利润/投资比: {profit_ratio:.2f}%")

def run_dfa_binance_backtest(symbol='SOLUSDT', timeframe='1d', data_limit=1000):
    """使用币安数据运行DFA策略回测"""
    
    # 创建cerebro引擎
    cerebro = bt.Cerebro()
    
    # 设置更合理的初始资金（基于预计投资）
    estimated_periods = 30
    initial_cash = 70 * estimated_periods * 3  # 预留足够现金
    cerebro.broker.setcash(initial_cash)
    
    # 添加策略
    cerebro.addstrategy(DFAStrategy)
    
    # 从币安获取数据
    data_df = fetch_binance_data(symbol, timeframe, data_limit)
    
    if data_df is None or data_df.empty:
        print(f"无法获取 {symbol} 数据，退出回测")
        return
    
    # 创建Backtrader数据源
    data = bt.feeds.PandasData(
        dataname=data_df,
        datetime=None,
        open='open',
        high='high', 
        low='low',
        close='close',
        volume='volume',
        openinterest=None
    )
    
    cerebro.adddata(data)
    
    # 添加分析器
    cerebro.addanalyzer(bt.analyzers.Returns, _name='returns')
    cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name='sharpe')
    cerebro.addanalyzer(bt.analyzers.DrawDown, _name='drawdown')
    cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name='trades')
    
    print(f'初始现金储备: ${cerebro.broker.getvalue():.2f}')
    
    # 运行回测
    print('开始回测...')
    results = cerebro.run()
    strat = results[0]
    
    # 输出基于实际投资的结果
    print('\n' + '='*60)
    print('DFA策略回测结果 (基于实际投资成本)')
    print('='*60)
    
    # 从策略中获取实际投资数据
    total_investment = sum([inv['amount'] for inv in strat.investment_history])
    total_assets_from_investment = (strat.total_shares * strat.datas[0].close[0]) + strat.total_sell_amount
    
    if total_investment > 0:
        actual_return = ((total_assets_from_investment - total_investment) / total_investment) * 100
    else:
        actual_return = 0
    
    print(f'实际总投资: ${total_investment:.2f}')
    print(f'投资产生总资产: ${total_assets_from_investment:.2f}')
    print(f'基于投资的总回报率: {actual_return:.2f}%')
    print(f'总定投期数: {strat.investment_count}')
    print(f'减仓次数: {len(strat.profit_history)}')
    print(f'已实现利润: ${sum([p["profit"] for p in strat.profit_history]):.2f}')
    
    # 绘制图表
    print('\n生成图表...')
    cerebro.plot(style='candlestick', volume=False)

def fetch_binance_data(symbol='SOLUSDT', timeframe='1d', limit=1000):
    """
    从币安获取K线数据
    symbol: 交易对，如 SOLUSDT, BTCUSDT, ETHUSDT
    timeframe: 时间周期 1d=日线, 1h=1小时, 1w=周线
    limit: 获取的数据条数
    """
    print(f"正在从币安获取 {symbol} 数据...")

    exchange = ccxt.binance({
        'enableRateLimit': True,
        'proxies': {
            'http': 'http://10.48.175.246:7897',
            'https': 'http://10.48.175.246:7897',
        },
        'timeout': 30000,
    })
    try:
        # 获取K线数据
        ohlcv = exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
        
        if not ohlcv:
            print("未获取到数据")
            return None
            
        # 转换为DataFrame
        df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        df.set_index('timestamp', inplace=True)
        
        print(f"成功获取 {len(df)} 条 {symbol} 数据，时间范围: {df.index[0]} 到 {df.index[-1]}")
        return df
        
    except Exception as e:
        print(f"获取数据失败: {e}")
        return None

# 运行示例
if __name__ == '__main__':
    print("开始DFA策略回测（14天定投70美元，75%收益率减仓50%，冷却期30天）")
    print("=" * 60)
    
    run_dfa_binance_backtest(symbol='SUIUSDT', data_limit=1000)
    #run_dfa_binance_backtest(symbol='SOLUSDT', data_limit=1000)