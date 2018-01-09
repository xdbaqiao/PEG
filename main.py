#!/usr/bin/env python2
# coding: utf-8
# 彼得林奇修正 PEG
# https://www.joinquant.com/post/3347

import sys
import pandas as pd
from trader import do_trade
from Context import Context
from lowPEG_algo import lowPEG_algo
from datetime import datetime

def fun_main(context, day_info_df):
    lowPEG_trade_ratio = lowPEG_algo(context, context.lowPEG_ratio, context.portfolio.portfolio_value, day_info_df)
    # 调仓，执行交易
    do_trade().fun_do_trade(context, lowPEG_trade_ratio, context.lowPEG_moneyfund)

def judge_run():
    sdate = '20170913'
    dtes = []
    with open('tradeday.txt') as f:
        for i in f:
            dtes.append(i.strip())
    dtes.sort()
    idx = dtes.index(sdate)
    today = datetime.today().strftime('%Y%m%d')
    if today in dtes:
        idx2 = dtes.index(today)
        if (idx2 - idx) % 5 == 0:
            # 5个交易日一调仓
            return True
    return False

if __name__ == '__main__':
    judge = judge_run()
    if not judge:
        sys.exit()
    # Context对象, 存放有当前的账户/股票持仓信息
    context = Context()
    # 持仓股数量
    context.lowPEG_hold_num = 5
    # 风险
    context.lowPEG_risk_ratio = 0.03 / context.lowPEG_hold_num
    context.lowPEG_ratio = 1.0 
    context.lowPEG_confidencelevel = 1.96
    # 调仓天数
    context.lowPEG_hold_periods, context.lowPEG_hold_cycle = 0, 5
    context.lowPEG_stock_list = []
    context.lowPEG_position_price = {}

    df = pd.read_csv('./info.csv', dtype={'code':object})
    df = df.set_index('code')
    
    fun_main(context, df)
