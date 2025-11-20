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
        ('base_cash', 500),  # 每期基础投资金额
        ('ma_period', 120),  # 移动平均线周期
        ('investment_interval', 14),  # 投资间隔改为14天
        ('target_return', 50),  # 目标收益率50%止盈
        ('printlog', True),  # 打印交易日志
    )
    
    def __init__(self):
        # 计算120日移动平均线
        self.ma120 = bt.indicators.SMA(self.datas[0], period=self.params.ma_period)
        
        # 投资计数器
        self.investment_count = 0
        self.last_investment_date = None
        
        # 记录投资历史
        self.investment_history = []
        
        # 记录交易历史和收益率
        self.trade_history = []
        self.total_invested = 0  # 总投资金额
        self.total_shares = 0    # 总持有份额

    def next(self):
        # 检查止盈条件
        self.check_profit_taking()
        
        # 检查是否到了投资日（每14天投资一次）
        current_date = self.datas[0].datetime.date(0)
        
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
            # 计算购买数量
            size = investment_amount / current_price
            size = int(size)  # 取整
            
            if size > 0:
                self.buy(size=size)
                
                # 更新总投资信息
                self.total_invested += investment_amount
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
                    'amount': investment_amount,
                    'shares': size
                }
                self.investment_history.append(investment_info)
                
                if self.params.printlog:
                    self.log(f'第{self.investment_count}期投资: 价格${current_price:.2f}, '
                           f'偏离度{deviation:.1f}%, 乘数{multiplier:.1f}, '
                           f'金额${investment_amount:.2f}, 份额{size}')

    def check_profit_taking(self):
        """检查止盈条件"""
        if self.total_shares > 0:
            current_price = self.datas[0].close[0]
            current_value = self.total_shares * current_price
            
            # 计算当前收益率
            if self.total_invested > 0:
                current_return = (current_value - self.total_invested) / self.total_invested * 100
                
                # 如果收益率达到目标，卖出全部持仓
                if current_return >= self.params.target_return:
                    self.sell(size=self.total_shares)
                    
                    # 记录止盈信息
                    profit_info = {
                        'date': self.datas[0].datetime.date(0),
                        'price': current_price,
                        'return_percent': current_return,
                        'shares_sold': self.total_shares,
                        'amount_received': current_value
                    }
                    self.trade_history.append(profit_info)
                    
                    if self.params.printlog:
                        self.log(f'🎯 止盈卖出: 收益率{current_return:.1f}%, '
                               f'价格${current_price:.2f}, 份额{self.total_shares}, '
                               f'获得${current_value:.2f}')
                    
                    # 重置持仓信息
                    self.total_invested = 0
                    self.total_shares = 0

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
        print('DFA策略回测结果')
        print('='*60)
        print(f'总期数: {self.investment_count}')
        print(f'最终资产: ${self.broker.getvalue():.2f}')
        
        initial_value = 10000
        total_return = ((self.broker.getvalue() / initial_value) - 1) * 100
        print(f'总回报率: {total_return:.2f}%')
        
        # 显示投资历史
        if self.investment_history:
            df = pd.DataFrame(self.investment_history)
            print(f"\n投资历史概览:")
            print(f"平均偏离度: {df['deviation'].mean():.1f}%")
            print(f"平均投资乘数: {df['multiplier'].mean():.2f}")
            print(f"总投资金额: ${df['amount'].sum():.2f}")
        
        # 显示止盈历史
        if self.trade_history:
            print(f"\n🎯 止盈记录:")
            for trade in self.trade_history:
                print(f"  {trade['date']}: 收益率{trade['return_percent']:.1f}%, "
                      f"价格${trade['price']:.2f}, 获得${trade['amount_received']:.2f}")

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

def run_dfa_binance_backtest(symbol='SOLUSDT', timeframe='1d', data_limit=1000):
    """使用币安数据运行DFA策略回测"""
    
    # 创建cerebro引擎
    cerebro = bt.Cerebro()
    
    # 设置初始资金 (USDT)
    initial_cash = 10000
    cerebro.broker.setcash(initial_cash)
    
    # 添加策略
    cerebro.addstrategy(DFAStrategy)
    
    # 从币安获取数据
    data_df = fetch_binance_data(symbol, timeframe, data_limit)
    
    if data_df is None or data_df.empty:
        print(f"无法获取 {symbol} 数据，退出回测")
        return
    
    # 创建Backtrader数据源 - 确保时间显示正确
    data = bt.feeds.PandasData(
        dataname=data_df,
        datetime=None,  # 使用index作为日期
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
    cerebro.addanalyzer(bt.analyzers.TimeReturn, _name='timereturn')
    
    print(f'初始资金: ${cerebro.broker.getvalue():.2f}')
    
    # 运行回测
    print('开始回测...')
    results = cerebro.run()
    strat = results[0]
    
    # 输出分析结果
    print('\n' + '='*60)
    print('策略绩效分析')
    print('='*60)
    
    # 基本绩效
    final_value = cerebro.broker.getvalue()
    total_return = ((final_value / initial_cash) - 1) * 100
    print(f'初始资金: ${initial_cash:.2f}')
    print(f'最终资产: ${final_value:.2f}')
    print(f'总回报率: {total_return:.2f}%')
    print(f'投资期数: {strat.investment_count}')
    print(f'止盈次数: {len(strat.trade_history)}')
    
    # 分析器结果
    try:
        returns_analysis = strat.analyzers.returns.get_analysis()
        if 'rnorm100' in returns_analysis:
            print(f'年化回报: {returns_analysis["rnorm100"]:.2f}%')
    except:
        pass
        
    try:
        sharpe_analysis = strat.analyzers.sharpe.get_analysis()
        if 'sharperatio' in sharpe_analysis:
            print(f'夏普比率: {sharpe_analysis["sharperatio"]:.3f}')
    except:
        pass
        
    try:
        drawdown_analysis = strat.analyzers.drawdown.get_analysis()
        if 'max' in drawdown_analysis:
            print(f'最大回撤: {drawdown_analysis["max"]["drawdown"]:.2f}%')
    except:
        pass
    
    # 交易分析
    try:
        trade_analysis = strat.analyzers.trades.get_analysis()
        if 'total' in trade_analysis:
            print(f'总交易次数: {trade_analysis["total"]["total"]}')
        if 'won' in trade_analysis:
            print(f'盈利交易次数: {trade_analysis["won"]["total"]}')
    except:
        pass
    
    # 绘制图表 - 改进图表显示
    print('\n生成图表...')
    cerebro.plot(
        style='candlestick', 
        volume=False,
        barup='green', 
        bardown='red',
        plotdist=1.0,
        subtxtsize=8
    )

def test_multiple_crypto_assets():
    """测试多个加密货币资产"""
    crypto_assets = [
        ('SOLUSDT', 'Solana'),
        ('BTCUSDT', 'Bitcoin'),
        ('ETHUSDT', 'Ethereum'),
    ]
    
    for symbol, name in crypto_assets:
        print(f'\n{"="*60}')
        print(f'测试资产: {name} ({symbol})')
        print(f'{"="*60}')
        run_dfa_binance_backtest(symbol=symbol, data_limit=500)
        time.sleep(1)  # 避免请求过于频繁

# 运行示例
if __name__ == '__main__':
    print("开始DFA策略回测（14天定投，50%止盈）")
    print("=" * 60)
    
    # 方法1: 测试单个资产
    run_dfa_binance_backtest(symbol='SOLUSDT', data_limit=1000)
    
    # 方法2: 测试多个资产 (取消注释以下行)
    # test_multiple_crypto_assets()