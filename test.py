#!/usr/bin/env python2
# coding: utf-8

import re
import pandas as pd


df = pd.read_csv('info.csv', dtype={'code':object})
df = df.set_index('code')

tmpDict = df.to_dict()
pe_dict = {}
tmp_dict = {}

for i in df.index:
    pe_dict[i] = tmpDict['pe_ttm'][i]
    print pe_dict[i]
