import pandas as pd
from sklearn import preprocessing
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
y_headers = ["brent"]
x_headers = ["vader_average", "vader", "watson","count","brent"]
training_split = 0.80

project_name = "test"

def series_to_supervised(data, x, y, n_in=1, m_out=1, dropnan=True,):
    df = pd.DataFrame(data, copy=True)
    cols = {}

    # input sequence (t-n, ... t-1)
    for i in range(n_in, 0, -1):
        shifted = df.shift(i)
        for header in x:
            cols[f'{header}_t-{i}'] = shifted[header].to_numpy()
    # forecast sequence (t, t+1, ... t+m)
    for i in range(0, m_out):
        shifted = df.shift(-i)
        for header in y:
            cols[f'{header}_t{f"+{i}" if i > 0 else ""}'] = shifted[header].to_numpy()

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

prepared_dataset = series_to_supervised(dataset, x_headers, y_headers, n_in=n_in, m_out=m_out)
scaler = preprocessing.MinMaxScaler(feature_range=(0, 1))
scaled_dataset = scaler.fit_transform(prepared_dataset)

train_count = math.ceil(len(scaled_dataset)*0.8)
train_x = scaled_dataset[:train_count, :][:,:-len(y_headers)*m_out]
train_y = scaled_dataset[:train_count, :][:,-len(y_headers)*m_out:]

test_x = scaled_dataset[train_count:, :][:,:-len(y_headers)*m_out]
test_y = scaled_dataset[train_count:, :][:,-len(y_headers)*m_out:]

train_x = train_x.reshape((train_x.shape[0], n_in, len(x_headers)))
test_x = test_x.reshape((test_x.shape[0], n_in, len(x_headers)))

#model = models.Sequential()
#model.add(layers.LSTM(n_in*3, input_shape=(train_x.shape[1], train_x.shape[2])))
#model.add(layers.Dense(m_out))
#model.compile(loss='mae', optimizer='adam')

#es = callbacks.EarlyStopping(monitor='val_loss', mode='min', patience=200, verbose=1, restore_best_weights=True)
#history = model.fit(train_x, train_y, epochs=2, batch_size=len(train_x), validation_data=(test_x, test_y), verbose=2, shuffle=False, callbacks=[es])

#pyplot.plot(history.history['loss'], label='train')
#pyplot.plot(history.history['val_loss'], label='test')
#pyplot.legend()
#pyplot.show()

model = load_model("./out/test_1582339221333.h5")
scaler = joblib.load("./out/test_1582339221333.joblib")

x = np.concatenate((train_x, test_x)).reshape((train_x.shape[0]+test_x.shape[0], n_in, len(x_headers)))
y = np.concatenate((train_y, test_y))
y_hat = model.predict(x)
x = x.reshape(x.shape[0], n_in*x.shape[2])
y_hat = np.concatenate((x, y_hat), axis = 1)
y = np.concatenate((x, y), axis = 1)

y_hat = scaler.inverse_transform(y_hat.reshape((x.shape[0], prepared_dataset.shape[1])))[:,-m_out*len(y_headers):]
y = scaler.inverse_transform(y.reshape((x.shape[0], prepared_dataset.shape[1])))[:,-m_out*len(y_headers):]

pyplot.plot(y)
pyplot.plot(y_hat)
pyplot.show()


pd.DataFrame(np.concatenate((y,y_hat), axis=1)).to_csv("out_test.csv")

rmse = math.sqrt(metrics.mean_squared_error(y, y_hat))
print('Test RMSE: %.3f' % rmse)