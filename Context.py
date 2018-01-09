#!/usr/bin/env python2
# coding: utf-8
# 获取账户的持仓信息

from trader import trader
from datetime import datetime

class Portfolio:
    def __init__(self):
        t = trader()
        # 总资金
        self.portfolio_value = t.balance.get('asset_balance')
        # 可用资金
        self.available_cash = t.balance.get('enable_balance')
        self.positions_value = t.balance.get('market_value')
        self.positions = self.Positions(t.holding)

    def Positions(self, t):
        # 获取持仓数据，key是股票id，value 是position
        bag = {}
        for i in t:
            tmp = dict(
                    security = i ,
                    # 总仓位
                    total_amount = t[i].get('current_amount'),
                    #  可卖出的仓位
                    closeable_amount = t[i].get('enable_amount'),
                    # 仓位比例
                    weight = t[i].get('weight'),
                    # 标的价值
                    value = t[i].get('market_value')                    
                    )
            bag[i] =  tmp
        return bag

class Context:
    # Context对象, 存放有当前的账户/股票持仓信息
    portfolio = Portfolio()
    current_dt = datetime.today()
    lowPEG_stock_list = []

if __name__ == '__main__':
    context = Context()
    print context.current_dt
    print context.portfolio.portfolio_value
    print context.portfolio.positions
