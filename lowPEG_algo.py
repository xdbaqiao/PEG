#!/usr/bin/env python2
# coding: utf-8

from lowPEG_lib import lowPEG_lib
from common import get_all_securities 

def lowPEG_algo(context, lowPEG_ratio, portfolio_value, day_info_df):
    '''
    low PEG algorithms
    '''

    lowPEG = lowPEG_lib(day_info_df)
    lowPEG.fun_initialize(context)

    recal_flag = False
    if lowPEG.fun_needRebalance(context):
        recal_flag = True

    # 配仓，分配持股比例
    equity_ratio = {}
    if recal_flag:
        context.lowPEG_stock_list = lowPEG.fun_get_stock_list(context)
        equity_ratio, bonds_ratio = lowPEG.fun_assetAllocationSystem(context, context.lowPEG_stock_list)
    else:
        equity_ratio = context.lowPEG_equity_ratio
        bonds_ratio = context.lowPEG_bonds_ratio

    context.lowPEG_equity_ratio = equity_ratio
    context.lowPEG_bonds_ratio = bonds_ratio

    # 分配头寸，配置市值
    trade_ratio = {}
    if recal_flag:
        trade_ratio = lowPEG.fun_calPosition(context, equity_ratio, bonds_ratio, lowPEG_ratio, portfolio_value)

        stock_list = get_all_securities(False, False)
        for stock in context.portfolio.positions.keys():
            if stock not in trade_ratio and stock in stock_list:
                trade_ratio[stock] = 0
    else:
        trade_ratio = context.lowPEG_trade_ratio

    context.lowPEG_trade_ratio = trade_ratio

    return trade_ratio
