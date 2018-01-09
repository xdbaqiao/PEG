#!/usr/bin/env python2
# coding: utf-8

import pandas as pd
import numpy as np
from quantlib import quantlib
from common import get_all_securities

class lowPEG_lib():
    def __init__(self, df):
        self.gquantlib = quantlib()
        self.df = df
        self.df_index = list(self.df.index)
        #self.df_index = list(self.df['code'])
    
    def fun_initialize(self, context):
        # 定义股票池
        lowPEG_equity = context.lowPEG_stock_list

        lowPEG_moneyfund = ['511880']

        # 上市不足 60 天的剔除掉
        context.lowPEG_equity    = []
        context.lowPEG_moneyfund = lowPEG_moneyfund

    def fun_needRebalance(self, context):
        if len(context.lowPEG_stock_list) == 0:
            context.lowPEG_hold_periods = context.lowPEG_hold_cycle
            return True
        
        if context.lowPEG_hold_periods == 0:
            context.lowPEG_hold_periods = context.lowPEG_hold_cycle
            return True
        else:
            context.lowPEG_hold_periods -= 1
            return False

    # 取得过去4个季度的平均增长，最后1个季度的增长，增长标准差
    def fun_get_inc(self, context, stock_list):
        # 对净利润增长率进行处理, 约束在 +- 100 之内，避免失真
        def __cal_net_profit_inc(stock):
            inc_list = []
            if stock in self.df_index:
                for k in self.df.loc[stock, 'inc_1':'inc_5']:
                    if k > 100:
                        k = 100
                    elif k< -100:
                        k = -100
                    inc_list.append(k)

            inc_list = inc_list if inc_list else [0, 0, 0, 0]
            last_inc = inc_list[0]
            inc_std = np.std(inc_list)
            avg_inc = np.mean(inc_list[:4])
            return avg_inc, last_inc, inc_std

        stock_dict = {}
        for stock in stock_list:
            avg_inc, last_inc, inc_std = __cal_net_profit_inc(stock)

            stock_dict[stock] = {}
            stock_dict[stock]['avg_inc'] = avg_inc
            stock_dict[stock]['last_inc'] = last_inc
            stock_dict[stock]['inc_std'] = inc_std
        return stock_dict

    def fun_cal_stock_PEG(self, context, stock_list, stock_dict):
        # 计算 PEG
        if not stock_list:
            PEG = {}
            return PEG

        df = self.df[self.df.index.isin(stock_list)]
        tmpDict = df.to_dict()
        pe_dict = {}
        tmp_dict = {}
        #for i in range(len(tmpDict['code'].keys())):
        #    pe_dict[tmpDict['code'][i]] = tmpDict['pe_ttm'][i]
        for i in df.index:
            pe_dict[i] = tmpDict['pe_ttm'][i]

        # 获取股息率
        df = self.gquantlib.fun_get_Divid_by_year(context, stock_list, self.df)
        tmpDict = df.to_dict()

        stock_interest = {}
        for stock in tmpDict['divpercent']:
            stock_interest[stock] = tmpDict['divpercent'][stock]

        PEG = {}
        for stock in stock_list:
            avg_inc  = stock_dict[stock]['avg_inc']
            last_inc = stock_dict[stock]['last_inc']
            inc_std  = stock_dict[stock]['inc_std']

            pe = -1            
            if stock in pe_dict:
                pe = pe_dict[stock]

            interest = 0
            if stock in stock_interest:
                interest = stock_interest[stock]

            PEG[stock] = -1
            '''
            原话大概是：
            1、增长率 > 50 的公司要小心，高增长不可持续，一旦转差就要卖掉；实现的时候，直接卖掉增长率 > 50 个股票
            2、增长平稳，不知道该怎么表达，用了 inc_std < last_inc。有思路的同学请告诉我
            '''
            if pe > 0 and last_inc <= 50 and last_inc > 0 and inc_std < last_inc:
                PEG[stock] = (pe / (last_inc + interest*100))
            if stock == '601515':
                print avg_inc, last_inc, inc_std, pe, interest

        print PEG.get('601515')
        return PEG

    def fun_get_stock_list(self, context):
        
        def fun_get_stock_market_cap(stock_list):
            df = self.df[self.df.index.isin(stock_list)]
            tmpDict = df.to_dict()
            stock_dict = {}
            #for i in range(len(tmpDict['code'].keys())):
            #    # 取得每个股票的 market_cap
            #    stock_dict[tmpDict['code'][i]] = tmpDict['market_value'][i]
            for i in df.index:
                # 取得每个股票的 market_cap
                stock_dict[i] = tmpDict['market_value'][i]
                
            return stock_dict
        
        today = context.current_dt
        # 全部股票、剔除停牌、剔除周期性行业
        stock_list = get_all_securities(False, False)
        
        stock_dict = self.fun_get_inc(context, stock_list)
        old_stocks_list = []
        for stock in context.portfolio.positions.keys():
            if stock in stock_list:
                old_stocks_list.append(stock)

        stock_PEG = self.fun_cal_stock_PEG(context, stock_list, stock_dict)
        
        stock_list = []
        buydict = {}
    
        for stock in stock_PEG.keys():
            if stock_PEG[stock] < 0.5 and stock_PEG[stock] > 0:
                stock_list.append(stock)
                buydict[stock] = stock_PEG[stock]
        cap_dict = fun_get_stock_market_cap(stock_list)
        buydict = sorted(cap_dict.items(), key=lambda d:d[1], reverse=False)

        buylist = []
        i = 0
        for idx in buydict:
            if i < context.lowPEG_hold_num:
                stock = idx[0]
                buylist.append(stock) # 候选 stocks
                print stock + ", PEG = "+ str(stock_PEG[stock])
                i += 1
        
        if len(buylist) < context.lowPEG_hold_num:
            old_stocks_PEG = self.fun_cal_stock_PEG(context, old_stocks_list, stock_dict)
            tmpDict = {}
            tmpList = []
            for stock in old_stocks_PEG.keys():
                if old_stocks_PEG[stock] < 1.0 and old_stocks_PEG[stock] > 0:
                    tmpDict[stock] = old_stocks_PEG[stock]
            tmpDict = sorted(tmpDict.items(), key=lambda d:d[1], reverse=False)
            i = len(buylist)
            for idx in tmpDict:
                if i < context.lowPEG_hold_num and idx[0] not in buylist:
                    buylist.append(idx[0])
                    i += 1

        print str(len(stock_list)) + " / " + str(len(buylist))
        print buylist

        return buylist

    def fun_assetAllocationSystem(self, context, buylist):
        def __fun_getEquity_ratio(context, __stocklist):
            __ratio = {}
            # 按风险平价配仓
            if __stocklist:
                __ratio = self.gquantlib.fun_calStockWeight_by_risk(context, 2.58, __stocklist)

            return __ratio

        equity_ratio = __fun_getEquity_ratio(context, buylist)
        print equity_ratio
        #bonds_ratio  = __fun_getEquity_ratio(context, context.lowPEG_moneyfund)
        bonds_ratio = {context.lowPEG_moneyfund[0]: 1}
        return equity_ratio, bonds_ratio

    def fun_calPosition(self, context, equity_ratio, bonds_ratio, lowPEG_ratio, portfolio_value):

        risk_ratio = len(equity_ratio.keys())
        risk_money = context.portfolio.portfolio_value * risk_ratio * context.lowPEG_ratio * context.lowPEG_risk_ratio
        maxrisk_money = risk_money * 1.7

        equity_value = 0
        if equity_ratio:
            equity_value = self.gquantlib.fun_getEquity_value(equity_ratio, risk_money, maxrisk_money, context.lowPEG_confidencelevel)

        value_ratio = 0
        total_value = portfolio_value * lowPEG_ratio

        print portfolio_value
        print '------------------'

        if equity_value > total_value:
            bonds_value = 0
            value_ratio = 1.0 * lowPEG_ratio
        else:
            value_ratio = (equity_value / total_value) * lowPEG_ratio
            bonds_value = total_value - equity_value
        
        trade_ratio = {}
        equity_list = equity_ratio.keys()
        for stock in equity_list:
            if stock in trade_ratio:
                trade_ratio[stock] += round((equity_ratio[stock] * value_ratio), 3)
            else:
                trade_ratio[stock] = round((equity_ratio[stock] * value_ratio), 3)
    
        for stock in bonds_ratio.keys():
            if stock in trade_ratio:
                trade_ratio[stock] += round((bonds_ratio[stock] * bonds_value / total_value) * lowPEG_ratio, 3)
            else:
                trade_ratio[stock] = round((bonds_ratio[stock] * bonds_value / total_value) * lowPEG_ratio, 3)
    
        return trade_ratio
