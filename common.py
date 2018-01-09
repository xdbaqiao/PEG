#!/usr/bin/env python2
# coding: utf-8
# todo 周期股问题

import re
import csv
import json
import requests
import pandas as pd
import numpy as np
from download import download

def get_stock_prefix(stock_code):
    """判断股票ID对应的证券市场
    匹配规则
    ['50', '51', '60', '90', '110'] 为 sh
    ['00', '13', '18', '15', '16', '18', '20', '30', '39', '115'] 为 sz
    ['5', '6', '9'] 开头的为 sh， 其余为 sz
    :param stock_code:股票ID, 若以 'sz', 'sh' 开头直接返回对应类型，否则使用内置规则判断
    :return 'sh' or 'sz'"""
    assert type(stock_code) is str, 'stock code need str type'
    if stock_code.startswith(('sh', 'sz')):
        return stock_code[:2]
    if stock_code.startswith(('50', '51', '60', '90', '110', '113', '132', '204')):
        return 'sh'
    if stock_code.startswith(('00', '13', '18', '15', '16', '18', '20', '30', '39', '115', '1318')):
        return 'sz'
    if stock_code.startswith(('5', '6', '9')):
        return 'sh'
    return 'sz'

def get_all_stock_codes(is_A=True, include_paused=True):
    """默认获取所有A股股票 ID"""
    result = []
    stock_codes = []
    url = 'http://nufm.dfcfw.com/EM_Finance2014NumericApplication/JS.aspx?type=CT&cmd=C._A&sty=FCOIATA&sortType=K&sortRule=-1&page=1&pageSize=5000&js=[(x)]&token=7bc05d0d4c3c22ef9fca8c2a912d779c&jsName=quote_123'
    html = download().get(url)
    for i in html.split('","'):
        if not include_paused:
            if i.split(',')[3] != '-':
                stock_codes.append(i.split(',')[1])
        else:
            stock_codes.append(i.split(',')[1])
    stock_codes = list(set(stock_codes))

    if not is_A:
        return stock_codes
    else:
        for i in stock_codes:
            if i.startswith('0') or i.startswith('3') or i.startswith('6'):
                result.append(i)
        return result

def get_stock_prefix_codes(is_A=False):
    return [get_stock_prefix(str(i))+str(i)  for i in get_all_stock_codes(is_A)]

def get_all_securities(include_paused=True, include_cycle_industry=True):
    # todo: 查询数据库，获取当日全部股票id
    # include_paused 是否包括停牌
    # include_cycle_industry 是否包括周期类
    
    lst = get_all_stock_codes(is_A=True, include_paused=include_paused)
    if not include_cycle_industry:
        # 处理周期股, 参考证监会行业分类
        # 直接从聚宽手动下载 周期性行业
        cycle_industry =  []
        for inum, i in enumerate(open('cycle_industry.csv')):
            if inum != 0:
                break
            cycle_industry = i.strip().replace('[', '').replace(']', '').replace('\'','').split(', ')
        return [i for i in lst if i not in cycle_industry]
    else:
        return lst

def history_180(stock, start, end):
    # 获取个股180天, 前复权数据，只能用于计算波动率
    # 注意不能用于取 当日股价
    # stock 是sz300014或者sh000001格式
    url = ''' http://vip.stock.finance.sina.com.cn/api/json.php/BasicStockSrv.getStockFuQuanData?symbol=%s&type=qfq ''' % stock
    text = download().get(url)
    if text:
        text = text[1:len(text)-1]
        text = text.replace('{_', '{"')
        text = text.replace('total', '"total"')
        text = text.replace('data', '"data"')
        text = text.replace(':"', '":"')
        text = text.replace('",_', '","')
        text = text.replace('_', '-')
        text = json.loads(text)
        df = pd.DataFrame({'date':list(text['data'].keys()), 'factor':list(text['data'].values())})
        df['date'] = df['date'].map(_fun_except) # for null case
        if df['date'].dtypes == np.object:
            df['date'] = pd.to_datetime(df['date'])
        df = df.drop_duplicates('date')
        df['factor'] = df['factor'].astype(float)
        df = df[(df.date >= start) & (df.date <= end)]
        df = df.set_index('date')
        df = df.sort_index(ascending=False)
        return df

def _fun_except(x):
    if len(x) > 10:
        return x[-10:]
    else:
        return x


if __name__ == '__main__':
    #print get_all_stock_codes(True)
    h = history_180('sz300014', '20161209', '20170901')
    print h.resample('D',how='last').pct_change().fillna(value=0, method=None, axis=0).values
    #p = get_all_securities(False, False)
