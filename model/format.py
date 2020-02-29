import re
from pandas import read_csv
from datetime import datetime
import numpy as np

with open("training_data.csv", "r+", encoding="utf-8") as f:
    text = re.sub(r",", ".", f.read())
    f.seek(0)
    f.truncate()
    f.write(text)

def parse(x):
	return datetime.strptime(x, "%d.%m.%Y")
dataset = read_csv('training_data.csv', sep=";", parse_dates = ["Date"], date_parser=parse)
rows, cols = dataset.shape

dataset.sort_values('Date')
dataset.reset_index(drop=True, inplace=True)

#fill holes with linear interpolation
last_price = 0
last_row = -1
for row in range(1, rows):
    if np.isnan(dataset.at[row, "WTI"]) and last_row == -1:
        last_price = dataset.loc[row-1, "WTI"]
        last_row = row - 1
    elif not np.isnan(dataset.at[row, "WTI"]) and last_row != -1:
        step = (dataset.at[row, "WTI"] - last_price)/(row - last_row)
        for i in range(last_row+1, row):
            dataset.loc[i, "WTI"] = last_price + step*(i-last_row)
        last_row = -1
        last_price = 0

def add_trend(df, column, timespan):
    print(df.shape)
    trend = np.array([0.0 for i in range(df.shape[0])])
    trend[811] = 5
    trend.fill(np.nan)
    for i in range(df.shape[0]-timespan):
        now = df.loc[i,column]
        future = df.loc[i+timespan,column]
        trend[i] = (future-now)/now

    df[f'trend_t+{timespan}']= trend
    print(df)

add_trend(dataset, "WTI", 1)
add_trend(dataset, "WTI", 2)
add_trend(dataset, "WTI", 3)
add_trend(dataset, "WTI", 5)


dataset.to_csv('formatted_training_data.csv')

