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

def linear_interpolation(start, stop, steps):
    arr = np.zeros(steps-1)
    stepsize = (stop-start)/steps
    for i in range(steps-1):
        arr[i] = start + stepsize*(i+1)
    return arr


def fill_nan(df, column, interpolation_generator):
    last_price = 0
    last_row = -1
    for row in range(1, rows):
        if np.isnan(df.at[row, column]) and last_row == -1:
            last_price = dataset.loc[row-1, column]
            last_row = row - 1
        elif not np.isnan(dataset.at[row, column]) and last_row != -1:
            steps = interpolation_generator(last_price, dataset.at[row, column], row - last_row)
            dataset.loc[last_row+1:row-1, column] = steps
            last_row = -1
            last_price = 0

def remove_nan(df):
    df.dropna(inplace=True)
    df.reset_index(inplace=True)

def add_change(df, column, timespan):
    change = np.full(df.shape[0], np.nan, dtype=float)
    for i in range(df.shape[0]-timespan):
        now = df.loc[i,column]
        future = df.loc[i+timespan,column]
        change[i] = (future-now)/now

    df[f'change_{column}_{timespan}']= change

def add_future_trend(df, column, timespan):
    trend = np.full(df.shape[0], np.nan, dtype=float)  
    for i in range(df.shape[0]-timespan):
        now = df.loc[i,column]
        future = df.loc[i+timespan,column]
        if(future > now):
            trend[i] = 1
        else:
            trend[i] = 0
    df[f'trend_{column}_{timespan}'] = trend

#fill_nan(dataset, "WTI", linear_interpolation)
#fill_nan(dataset, "vader", linear_interpolation)
#fill_nan(dataset, "vader_average", linear_interpolation)
#fill_nan(dataset, "henry", linear_interpolation)
#fill_nan(dataset, "Loughran-McDonald", linear_interpolation)
#fill_nan(dataset, "average_sentiment", linear_interpolation)
#fill_nan(dataset, "count", linear_interpolation)
#fill_nan(dataset, "watson", linear_interpolation)
remove_nan(dataset)
print(dataset)
add_change(dataset, "WTI", 1)
add_change(dataset, "WTI", 2)
#add_change(dataset, "WTI", 3)
#add_change(dataset, "WTI", 5)
add_future_trend(dataset, "WTI", 1)
add_future_trend(dataset, "WTI", 2)
#add_future_trend(dataset, "WTI", 3)
#add_future_trend(dataset, "WTI", 5)


dataset.to_csv('formatted_training_data.csv')

