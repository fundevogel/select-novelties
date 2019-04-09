#!/usr/bin/env python

import pandas as pd
import glob

dfs = glob.glob('*.csv')

result = pd.concat([pd.read_csv(df, sep=';') for df in dfs], ignore_index=True)

result.to_csv('merge.csv')
