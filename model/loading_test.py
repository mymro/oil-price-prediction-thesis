import pandas as pd
#from sklearn import preprocessing
from sklearn import metrics
import math
#import keras.models as models
#import keras.layers as layers
#import keras.callbacks as callbacks
from matplotlib import pyplot
import numpy as np
import time
from keras.models import load_model
import joblib

n_in, m_out = 3,1
m_offset = 1
y_headers = ["change_WTI_1"]
x_headers = ["WTI","watson"]
training_split = 0.80

project_name = "test"

def series_to_supervised(data, x, y, n_in=1, m_out=1, m_offset=0, dropnan=True,):
    df = pd.DataFrame(data, copy=True)
    cols = {}

    # input sequence (t-n, ... t-1)
    for i in range(n_in, 0, -1):
        shifted = df.shift(i)
        for header in x:
            cols[f'{header}_t-{i}'] = shifted[header].to_numpy()
    # forecast sequence (t, t+1, ... t+m)
    for i in range(0-m_offset, m_out-m_offset):
        shifted = df.shift(-i)
        for header in y:
            if i >= 0:
                cols[f'{header}_t{f"+{i}" if i > 0 else ""}'] = shifted[header].to_numpy()
            else:
                cols[f'{header}_t{i}'] = shifted[header].to_numpy()

    df_out = pd.DataFrame(cols)
    if dropnan:
        df_out.dropna(inplace=True)
        df_out.reset_index(inplace=True)
        df_out.drop(labels="index", axis=1, inplace=True)
    
    df_out.reset_index()
    return df_out          

dataset = pd.read_csv('formatted_training_data.csv', header=0, index_col=0)
dataset.drop("Date", axis=1, inplace=True)
dataset.astype('float32')

prepared_dataset = series_to_supervised(dataset, x_headers, y_headers, n_in=n_in, m_out=m_out, m_offset=m_offset)
scaler = joblib.load("./out/test_1584014594241.joblib")
scaled_dataset = scaler.transform(prepared_dataset)

model = load_model("./out/test_1584014594241.h5")

x = scaled_dataset[:, :][:,:-len(y_headers)*m_out]
y = scaled_dataset[:, :][:,-len(y_headers)*m_out:]
x = x.reshape((x.shape[0], n_in, len(x_headers)))
prepared_dataset.to_csv("test.csv")
y_hat = model.predict(x)
x = x.reshape(x.shape[0], n_in*x.shape[2])
y_hat = np.concatenate((x, y_hat), axis = 1)
y = np.concatenate((x, y), axis = 1)

y_hat = scaler.inverse_transform(y_hat.reshape((x.shape[0], prepared_dataset.shape[1])))[:,-m_out*len(y_headers):]
y = scaler.inverse_transform(y.reshape((x.shape[0], prepared_dataset.shape[1])))[:,-m_out*len(y_headers):]

pyplot.plot(y)
pyplot.plot(y_hat)
#pyplot.show()


pd.DataFrame(np.concatenate((y,y_hat), axis=1)).to_csv("predict_test.csv")

rmse = math.sqrt(metrics.mean_squared_error(y, y_hat))
print('Test RMSE: %.3f' % rmse)