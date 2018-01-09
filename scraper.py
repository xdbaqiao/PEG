#!/usr/bin/env python2
# coding: utf-8
# 数据采集程序， 入库
# 采集前一天所有股票
# code，价格、market_cap市值、是否停牌、所属行业、上市时间、pe_ratio市盈率(PE, TTM)
# 分红(取两年中，最近一年的分红)、股本
# 财报 统计时间statDate, inc_net_profit_year_on_year：净利润同比增长率 

#  净利润同比增长  http://data.10jqka.com.cn/financial/yjgg/ 
#  分红, 股本, 每股分红(税前), 每10股派现税前/10, 股息率 http://data.eastmoney.com/yjfp/
#  市值, 当日股价: http://qt.gtimg.cn/q=sh603778
#  上市时间, PE TTM : file.tushare.org/tsdata/all.csv
#  证监会行业: 每个季度从聚宽手动补 存放在cycle_industry.csv


import json
import decimal
import urllib2
import pandas as pd
import threading
from datetime import datetime
from common import *
from collections import deque
from download import download

THREADS_NUM = 20
SRC = 'http://qt.gtimg.cn/q=%s'
BLACK_LIST = ['300126', '000033', '300372']

def muilt_thread(target, num_threads, wait=True):
    threads = [threading.Thread(target=target) for i in range(num_threads)]
    for thread in threads:
        thread.start()
    if wait:
        for thread in threads:
            thread.join()

def get_prices():
    uniq_list = []
    bag_price = []
    names = deque()
    for i in get_stock_prefix_codes(is_A=True):
        names.append(SRC % i)

    def worker():
        while True:
            try:
                url = names.popleft()
            except IndexError:
                break
            try:
                html = download().get(url)
            except Exception, e:
                names.append(url)
                continue
            stock = html.split('~')
            if len(stock) <= 49:
                continue
            bag = {
                'name': stock[1],
                'code': stock[2],
                'now': float(stock[3]),
                'close': float(stock[4]),
                'open': float(stock[5]),
                'pe': float(stock[39]) if stock[39] != '' else None,
                'market_value': float(stock[45]) if stock[44] != '' else None
            }
            if '*' not in bag['name'] and 'S' not in bag['name'] and bag['market_value']:
                #filter stock with ST or risk notification
                if bag['code'] not in uniq_list and bag['code'] not in BLACK_LIST:
                    # not limit up and suspended
                    uniq_list.append(bag['code'])
                    bag_price.append(bag)
    muilt_thread(worker, THREADS_NUM)
    bag_price = sorted(bag_price, key = lambda x:x['market_value'])
    df = pd.DataFrame({'code':[i['code'] for i in bag_price], 'price':[i['close'] for i in bag_price], 'market_value':[i['market_value'] for i in bag_price], 'pe_ttm':[i['pe'] for i in bag_price]})
    #df = df.set_index('code')
    df = df.fillna(value=0)
    return df 

def PE_TTM():
    #  上市时间, PE TTM , 股本
    url = 'http://file.tushare.org/tsdata/all.csv'
    f = urllib2.urlopen(url) 
    data = f.read() 
    with open('all.csv', 'wb') as code:     
        code.write(data)

    codes = []
    market_time = []
    #pe_ttm = []
    totals = []

    with open('all.csv') as f:
        for inum, i in enumerate(f):
            if inum == 0:
                continue
            m = i.strip().split(',')
            codes.append(m[0])
            market_time.append(m[15])
            #pe_ttm.append(m[4])
            totals.append(m[6])
    #df = pd.DataFrame({'code':codes, 'market_time':market_time, 'pe_ttm':pe_ttm, 'totals':totals})
    df = pd.DataFrame({'code':codes, 'market_time':market_time,  'totals':totals})
    #df = df.set_index('code')
    df = df.fillna(value=0)
    return df

def get_inc():
    # 净利润同比增长, 注意是单季度值
    # 前五个季度
    url = 'http://data.10jqka.com.cn/financial/yjgg/'
    html = download().get(url)
    dates = re.compile(r'a\shref\="javascript\:void\(0\);"\sdate\="([^"]+)"').findall(html)

    year = int(datetime.today().strftime('%Y%m%d')[:4])
    names = deque()
    src = 'http://money.finance.sina.com.cn/corp/view/vFD_FinanceSummaryHistory.php?stockid=%s&type=NETPROFIT&cate=liru0'
    for i in get_all_stock_codes(True, True):
        names.append(src % i )

    bag = {}
    def worker():
        while True:
            try:
                url = names.popleft()
            except IndexError:
                break
            try:
                html = download().get(url)
            except Exception, e:
                print e
                names.append(url)
                continue
            m = re.compile(r'stockid\=([^\&]+)\&').search(url)
            if html and m:
                html = html.decode('gb2312')
                code = m.groups()[0]

                html = html.split('id="Table1">')[1] if 'id="Table1">' in html else ''
                html = html.split('</tbody>') [0] if '</tbody>' in html else ''

                ms = html.split('</tr>') if '</tr>' in html else [] 
                for i in ms:
                    tmp = re.compile(r'text\-align\:center">(\d{4}-\d{2}-\d{2})<').findall(i)
                    tim = tmp[0] if tmp else ''
                    tmp = re.compile(r'text\-align\:center">([\d\.\,]+)<').findall(i)
                    profit = tmp[0] if tmp else ''
                    tmp = re.compile(r'font>([\d\.\,]+)<').findall(i)
                    profit_tb = tmp[0] if tmp else ''
                    if tim and profit and profit_tb:
                        if '-03-31' in tim:
                            profit_tb = profit
                        inc = decimal.Decimal(profit_tb.replace(',', ''))
                        if code not in bag:
                            bag[code] = {}
                        bag[code][tim] = inc 
                    # 计算同比增长率
                bag_copy = bag[code].copy()
                for i in bag[code]:
                    last_i = str(int(i[:4]) - 1) +  i[4:]
                    inc = bag_copy[i]
                    if last_i in bag_copy:
                        last_inc = bag_copy[last_i]
                        bag[code][i] = (inc - last_inc) * 100 / last_inc if last_inc != 0 else 0
                    else:
                        bag[code][i] = 0

    muilt_thread(worker, THREADS_NUM)
    res = [[i, bag[i].get(dates[0]),  bag[i].get(dates[1]),  bag[i].get(dates[2]),  bag[i].get(dates[3]), bag[i].get(dates[4])] for i in bag]
    # inc_1 最近一个季度， inc_2 前两个季度
    df = pd.DataFrame({'code':[i[0] for i in res], 'inc_1':[i[1] for i in res], 'inc_2': [i[2] for i in res], \
            'inc_3':[i[3] for i in res], 'inc_4':[i[4] for i in res], 'inc_5':[i[5] for i in res]})
    #df = df.set_index('code')
    df = df.fillna(value=0)
    return df

def get_divid():
    # 分红, 股本, 每股分红(税前), 每10股派现税前/10, 股息率 http://data.eastmoney.com/yjfp/
    # 取最近四个季度的分红
    url = 'http://data.eastmoney.com/yjfp/'
    html = download().get(url)
    dates = re.compile(r'<option\s\svalue\="20[^>]+>([^<]+)').findall(html)
    names = deque()
    for i in dates[:5]:
        src = 'http://data.eastmoney.com/DataCenter_V3/yjfp/getlist.ashx?pagesize=200&page=1&sr=-1&sortType=SZZBL&filter=(ReportingPeriod=^%s^)'\
                %  i
        html = download().get(src)
        m = re.compile(r'"pages":([^,]+),').search(html)
        num = int(m.groups()[0]) if m else 1
        #num = num if num < 25 else 25
        for j in range(1, num+1):
            url = 'http://data.eastmoney.com/DataCenter_V3/yjfp/getlist.ashx?pagesize=200&page=%s&sr=-1&sortType=SZZBL&filter=(ReportingPeriod=^%s^)'\
                    %  (str(j), i)
            names.append(url)

    bag = {}
    def worker():
        while True:
            try:
                url = names.popleft()
            except IndexError:
                break
            try:
                html = download().get(url)
            except Exception, e:
                print e
                names.append(url)
                continue
            m = re.compile(r'ReportingPeriod\=\^([^\^]+)\^').search(url)
            if m:
                tim = str(m.groups()[0])
                html = html.decode('gbk')
                jl = json.loads(html)
                for info in jl['data']:
                    # 分红比例
                    fh = info.get('AllocationPlan')
                    fh2 = re.compile(u'派([\d\.]+)元').search(fh)
                    fh3 = decimal.Decimal(fh2.groups()[0]) if fh2 else 0
                    # 总股本
                    tmp = info.get('TotalEquity')
                    zgb = decimal.Decimal(tmp) / 100000000 if tmp and tmp != '-' else 0
                    code = info.get('Code')
                    if code and  code not in bag:
                        bag[code] = {}
                    # 股本数 乘以 每股分红
                    bag[code][tim] = zgb * fh3 / 10
    muilt_thread(worker, THREADS_NUM)
    if '-12-31' in dates[0]:
        # 当年所有股票分红、去年所有股票年度分红、去年所有股票非年度分红、去年未年度分红股票且前年年度分红
        res = [[i, bag[i].get(dates[0]),  bag[i].get(dates[1]),  bag[i].get(dates[2]),  bag[i].get(dates[3]),\
                bag[i].get(dates[4]) if not bag[i].get(dates[2]) else 0 ] for i in bag]
    else:
        res = [[i, bag[i].get(dates[0]),  bag[i].get(dates[1]),  bag[i].get(dates[2]),  bag[i].get(dates[3])\
                if not bag[i].get(dates[1]) else 0, 0] for i in bag]

    # inc_1 最近一个季度， inc_2 前两个季度
    df = pd.DataFrame({'code':[i[0] for i in res], 'fh_1':[i[1] for i in res], 'fh_2': [i[2] for i in res], \
            'fh_3':[i[3] for i in res], 'fh_4':[i[4] for i in res], 'fh_5':[i[5] for i in res]})

    #df = df.set_index('code')
    df = df.fillna(value=0)
    return df

def scraper():
    # 上市时间, PE TTM , 总股本
    result2 = PE_TTM()
    # 市值, 当日股价: http://qt.gtimg.cn/q=sh603778
    result = get_prices()
    # 净利润同比增长  , 注意是单季度值
    result3 = get_inc()
    # 分红, 股本, 每股分红(税前), 每10股派现税前/10, 股息率 http://data.eastmoney.com/yjfp/
    result4 = get_divid()
    
    tmp1 = pd.merge(result, result2, how='outer', on='code')
    tmp2 = pd.merge(tmp1, result3, how='outer', on='code')
    tmp3 = pd.merge(tmp2, result4, how='outer', on='code')
    tmp3 = tmp3.fillna(value=0)
    tmp3.to_csv('./info.csv')

def test():
    print get_divid()

if __name__ == '__main__':
    scraper()
    #test()
