import pandas as pd
from sklearn import preprocessing
from sklearn import metrics
import math
import keras.models as models
import keras.layers as layers
import keras.callbacks as callbacks
from matplotlib import pyplot
import numpy as np
import time
import joblib

n_in, m_out = 4,1
m_offset = 0
y_headers = ["trend_WTI_1"]
x_headers = ["WTI", "henry", "Loughran-McDonald", "vader_average", "vader", "watson"]
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
scaler = preprocessing.MinMaxScaler(feature_range=(0, 1))
scaled_dataset = scaler.fit_transform(prepared_dataset)

x = scaled_dataset[:, :][:,:-len(y_headers)*m_out]
y = scaled_dataset[:, :][:,-len(y_headers)*m_out:]

x = x.reshape((x.shape[0], n_in, len(x_headers)))

def create_binary(optimizer="adam", init="glorot_uniform", layer_out=10):
    model = models.Sequential()
    model.add(layers.LSTM(layer_out, input_shape=(x.shape[1], x.shape[2]), kernel_initializer=init, activation='relu', dropout=0.2, recurrent_dropout=0.2))
    model.add(layers.Dense(m_out, activation="sigmoid",  kernel_initializer=init))
    model.compile(loss='binary_crossentropy', optimizer=optimizer, metrics=['accuracy'])
    return model

split= math.floor(len(prepared_dataset)*0.8)
train_x = scaled_dataset[:split, :][:, :-len(y_headers)*m_out]
test_x = scaled_dataset[split:, :][:, :-len(y_headers)*m_out]
train_x = train_x.reshape((train_x.shape[0], n_in, len(x_headers)))
test_x = test_x.reshape((test_x.shape[0], n_in, len(x_headers)))
train_y = scaled_dataset[:split, :][:, -len(y_headers)*m_out:]
test_y = scaled_dataset[split:, :][:, -len(y_headers)*m_out:]

model_results = pd.DataFrame()

for optimizer in ['adam', 'Adagrad', 'rmsprop']:
    for init in ['glorot_uniform', 'normal', 'uniform']:
        for layer_out in [len(x_headers), 8, 10, 12, 14, 16, 18, 20, 22, 24]:
            for patience in [100, 200, 300, 400, 500, 600, 700, 1000, 1100, 1200, 1300, 1400]:
                for batch_size in [len(train_x)]:
                    es = callbacks.EarlyStopping(monitor='val_loss', mode='min', patience=patience, verbose=1, restore_best_weights=True)
                    model = create_binary(optimizer=optimizer, init=init, layer_out=layer_out)
                    model.fit(train_x, train_y, epochs=20000, batch_size=batch_size, validation_data=(test_x, test_y), verbose = 2, callbacks=[es])
                    
                    row = np.array([0.0, 0.0, 0.0, {}])
                    row[0:2] = model.evaluate(test_x,test_y)
                    y_hat = model.predict(x)
                    x_temp = x.reshape(x.shape[0], n_in*x.shape[2])
                    y_hat = np.concatenate((x_temp, y_hat), axis = 1)
                    y_temp = np.concatenate((x_temp, y), axis = 1)

                    y_hat = scaler.inverse_transform(y_hat.reshape((x_temp.shape[0], prepared_dataset.shape[1])))[:,-m_out*len(y_headers):]
                    y_temp = scaler.inverse_transform(y_temp.reshape((x_temp.shape[0], prepared_dataset.shape[1])))[:,-m_out*len(y_headers):]
                    row[2] = math.sqrt(metrics.mean_squared_error(y_temp, y_hat))
                    row[3] = {
                        "optimizer":optimizer,
                        "init":init,
                        "layer_out":layer_out,
                        "patience":patience,
                        "batch_size":batch_size
                    }
                    row = row.reshape((1,4))
                    test = pd.DataFrame(row)
                    model_results = model_results.append(pd.DataFrame(row),)
                    model_results.to_csv("./params.csv")

model_results.sort_values(1, inplace=True, ascending=False)
model_results.reset_index(drop=True, inplace=True)
model_results.to_csv("./params.csv")

params = model_results.loc[0, 3]

es = callbacks.EarlyStopping(monitor='val_loss', mode='min', patience=params['patience'], verbose=1, restore_best_weights=True)
model = create_binary(optimizer=params['optimizer'], init=params['init'], layer_out=params['layer_out'])
model.fit(train_x, train_y, epochs=params['epochs'], batch_size=params['batch_size'], validation_data=(test_x, test_y), verbose = 2, callbacks=[es])

y_hat = model.predict(x)
x = x.reshape(x.shape[0], n_in*x.shape[2])
y_hat = np.concatenate((x, y_hat), axis = 1)
y = np.concatenate((x, y), axis = 1)

y_hat = scaler.inverse_transform(y_hat.reshape((x.shape[0], prepared_dataset.shape[1])))[:,-m_out*len(y_headers):]
y = scaler.inverse_transform(y.reshape((x.shape[0], prepared_dataset.shape[1])))[:,-m_out*len(y_headers):]

pd.DataFrame(np.concatenate((y,y_hat), axis=1)).to_csv("out_test.csv")

rmse = math.sqrt(metrics.mean_squared_error(y, y_hat))
print('Test RMSE: %.3f' % rmse)

now = int(time.time()*1000.0)

joblib.dump(scaler, f'./out/{project_name}_{now}.joblib')
model.save(f'./out/{project_name}_{now}.h5')
model.summary()
#TODO also save other paramters inouts outputs, etc.