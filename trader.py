#!/usr/bin/env python2
# coding: utf-8

import re
import easytrader
from download import download

PLATFORM = 'xq'
CONFIG_FILE = 'account.json'

class do_trade:
    def __init__(self):
        pass

    def fun_do_trade(self, context, trade_ratio, moneyfund):
        # 如果持仓股里 有调仓股，如果回撤大于25%或者盈利大于25%，则调仓，否则不交易
        t = trader()
        def __fun_tradeStock(context, stock, ratio, t):
            m = int(ratio*100)
            holds = context.portfolio.positions.keys()
            portfolio_value = context.portfolio.portfolio_value
            if m>=0 and m <= 100:
                if stock in holds:
                    new_ratio = context.portfolio.positions[stock]['value'] / portfolio_value
                    if abs(new_ratio - ratio) / new_ratio >= 0.25:
                        if ratio > new_ratio:
                            cash = context.portfolio.available_cash / portfolio_value
                            if cash  >= ratio * 0.25:
                                t.user.adjust_weight(stock, ratio)
                        else:
                            t.user.adjust_weight(stock, ratio)
                elif m != 0:
                    t.user.adjust_weight(stock, m)

        tmp = sorted(trade_ratio.items(), key=lambda d:d[1], reverse=False)
        for stock in tmp:
            print stock[0], trade_ratio[stock[0]]
            __fun_tradeStock(context, stock[0], trade_ratio[stock[0]], t)

class trader:
    def __init__(self):
        self.user = easytrader.use(PLATFORM)
        self.user.prepare(CONFIG_FILE)
        self.holding = {i['stock_code'][2:]:i for i in self.user.position}
        self.balance = self.user.balance[0]
        self.enable_balance = self.balance['enable_balance']

    def buy(self, stock, weight):
        print 'Buy stock: %s, weight: %s' % (stock, weight)
        result = self.user.buy(stock_code=stock, volume=weight)

    def sell(self, stock, weight):
        print 'Sell stock: %s, weight: %s' % (stock, weight)
        result = self.user.sell(stock_code=stock, volume=weight)

