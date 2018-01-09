#!/usr/bin/env python2
# coding: utf-8

from datetime import datetime, timedelta
from common import history_180
import datetime as dt
import numpy as np

class quantlib():
    def __init__(self, _period = '1d'):
        self.tradeday = [i.strip() for i in open('tradeday.txt')]
        self.tradeday.sort()

        self.end = datetime.today().strftime('%Y%m%d')
        idx = self.tradeday.index(self.end) if self.end in self.tradeday else -1
        idx2 = idx - 179 if idx>=179 else 0
        self.start = self.tradeday[idx2] 

    def fun_getEquity_value(self, equity_ratio, risk_money, maxrisk_money, confidence_ratio):
        def __fun_getdailyreturn(stock, freq):
            hStocks = history_180(stock, self.start, self.end)
            dailyReturns = hStocks.resample('D').last().pct_change().fillna(value=0, method=None, axis=0).values

            return dailyReturns

        def __fun_get_portfolio_dailyreturn(ratio, freq):
            __portfolio_dailyreturn = []
            for stock in ratio.keys():
                if ratio[stock] != 0:
                    __dailyReturns = __fun_getdailyreturn(stock, freq)
                    __tmplist = []
                    for i in range(len(__dailyReturns)):
                        __tmplist.append(__dailyReturns[i] * ratio[stock])
                    if __portfolio_dailyreturn:
                        __tmplistB = []
                        for i in range(len(__portfolio_dailyreturn)):
                            __tmplistB.append(__portfolio_dailyreturn[i]+__tmplist[i])
                        __portfolio_dailyreturn = __tmplistB
                    else:
                        __portfolio_dailyreturn = __tmplist
    
            return __portfolio_dailyreturn
    
        def __fun_get_portfolio_ES(ratio, freq, confidencelevel):
            if confidencelevel == 1.96:
                a = (1 - 0.95)
            elif confidencelevel == 2.06:
                a = (1 - 0.96)
            elif confidencelevel == 2.18:
                a = (1 - 0.97)
            elif confidencelevel == 2.34:
                a = (1 - 0.98)
            elif confidencelevel == 2.58:
                a = (1 - 0.99)
            else:
                a = (1 - 0.95)
            dailyReturns = __fun_get_portfolio_dailyreturn(ratio, freq)
            dailyReturns_sort =  sorted(dailyReturns)
    
            count = 0
            sum_value = 0
            for i in range(len(dailyReturns_sort)):
                if i < (180 * a):
                    sum_value += dailyReturns_sort[i]
                    count += 1
            if count == 0:
                ES = 0
            else:
                ES = -(sum_value / (180 * a))

            return ES

        def __fun_get_portfolio_VaR(ratio, freq, confidencelevel):
            __dailyReturns = __fun_get_portfolio_dailyreturn(ratio, freq)
            __portfolio_VaR = 1.0 * confidencelevel * np.std(__dailyReturns)

            return __portfolio_VaR

        # 每元组合资产的 VaR
        __portfolio_VaR = __fun_get_portfolio_VaR(equity_ratio, '1d', confidence_ratio)

        __equity_value_VaR = 0
        if __portfolio_VaR:
            __equity_value_VaR = risk_money / __portfolio_VaR

        __portfolio_ES = __fun_get_portfolio_ES(equity_ratio, '1d', confidence_ratio)

        __equity_value_ES = 0
        if __portfolio_ES:
            __equity_value_ES = maxrisk_money / __portfolio_ES

        if __equity_value_VaR == 0:
            equity_value = __equity_value_ES
        elif __equity_value_ES == 0:
            equity_value = __equity_value_VaR
        else:
            equity_value = min(__equity_value_VaR, __equity_value_ES)

        return equity_value

    def fun_get_Divid_by_year(self, context, stocks, df):
        df = df[df.index.isin(stocks)]
        # 删除 股价为0的标的
        df = df[df['price'] * df['totals'] != 0]
        #计算股息率 = 股息*股本/股票价格*股本
        df['divpercent'] = (df['fh_1'] + df['fh_2'] + df['fh_3'] + df['fh_4'] + df['fh_5']) /(df['price'] * df['totals'])
        df = df.fillna(value=0)
        return df

    def fun_calStockWeight_by_risk(self, context, confidencelevel, stocklist):
        def __fun_calstock_risk_ES(stock, confidencelevel):
            hStocks = history_180(stock, self.start, self.end)
            dailyReturns = hStocks.resample('D').last().pct_change().fillna(value=0, method=None, axis=0).values
            if confidencelevel == 1.96:
                a = (1 - 0.95)
            elif confidencelevel == 2.06:
                a = (1 - 0.96)
            elif confidencelevel == 2.18:
                a = (1 - 0.97)
            elif confidencelevel == 2.34:
                a = (1 - 0.98)
            elif confidencelevel == 2.58:
                a = (1 - 0.99)
            elif confidencelevel == 5:
                a = (1 - 0.9999)
            else:
                a = (1 - 0.95)

            dailyReturns_sort = sorted(dailyReturns)

            count = 0
            sum_value = 0
            length = len(dailyReturns_sort)
            for i in range(len(dailyReturns_sort)):
                if i < (length * a):
                    sum_value += dailyReturns_sort[i]
                    count += 1
            if count == 0:
                ES = 0
            else:
                if sum_value > 0:
                    ES = 0
                else:
                    ES = -(sum_value / count)

            if ES > 0.1: #A股有跌停板限制
                ES = 0.1

            return ES

        def __fun_calstock_risk_VaR(stock):
            hStocks = history_180(stock, self.start, self.end)
            dailyReturns = hStocks.resample('D',how='last').pct_change().fillna(value=0, method=None, axis=0).values
            VaR = 1 * 2.58 * np.std(dailyReturns)

            return VaR
            
        __risk = {}

        stock_list = []
        for stock in stocklist:
            curRisk = __fun_calstock_risk_ES(stock, confidencelevel)

            if curRisk <> 0.0:
                __risk[stock] = curRisk

        __position = {}
        for stock in __risk.keys():
            __position[stock] = 1.0 / __risk[stock]

        total_position = 0
        for stock in __position.keys():
            total_position += __position[stock]

        __ratio = {}
        for stock in __position.keys():
            tmpRatio = __position[stock] / total_position if total_position else 0
            __ratio[stock] = round(tmpRatio, 4)
    
        return __ratio
