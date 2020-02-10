import re
from pandas import read_csv
from datetime import datetime

with open("training_data.csv", "r+", encoding="utf-8") as f:
    text = re.sub(r",", ".", f.read())
    f.seek(0)
    f.truncate()
    f.write(text)

def parse(x):
	return datetime.strptime(x, "%d.%m.%Y")
dataset = read_csv('training_data.csv', sep=";", index_col=0, parse_dates = ["Date"], date_parser=parse)
rows, cols = dataset.shape

#fill holes with linear interpolation
last_price = 0
last_row = 0
for row in range(1, rows+1):
    if dataset.at[row, "brent"]  == 0 and last_row == 0:
        last_price = dataset.loc[row-1, "brent"]
        last_row = row - 1
    elif dataset.at[row, "brent"]  != 0 and last_row != 0:
        step = (dataset.at[row, "brent"] - last_price)/(row - last_row)
        for i in range(last_row+1, row):
            dataset.at[i, "brent"] = last_price + step*(i-last_row)
        last_row = 0
        last_price = 0

dataset.to_csv('formatted_training_data.csv')

