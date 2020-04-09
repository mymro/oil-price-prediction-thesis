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

#n_in, m_out = 3,1
##m_offset = 0
#relative = False
#y_headers = ["WTI"]
#x_headers = ["WTI","henry","Loughran-McDonald","vader_average","vader","watson"]
#training_split = 0.80

tasks = [
    {
        'n_in':3, 
        'm_out':1,
        'm_offset':0,
        'relative':False,
        'y_headers':["WTI"],
        'x_headers':["WTI","henry","Loughran-McDonald","vader_average","vader","watson"],
        'training_split':0.80,
        'rounds':100,
    },
    {
        'n_in':3, 
        'm_out':1,
        'm_offset':0,
        'relative':False,
        'y_headers':["WTI"],
        'x_headers':["WTI","vader_average","vader"],
        'training_split':0.80,
        'rounds':100,
    },
    {
        'n_in':3, 
        'm_out':1,
        'm_offset':0,
        'relative':False,
        'y_headers':["WTI"],
        'x_headers':["WTI","henry","Loughran-McDonald"],
        'training_split':0.80,
        'rounds':100,
    },
    {
        'n_in':3, 
        'm_out':1,
        'm_offset':0,
        'relative':False,
        'y_headers':["WTI"],
        'x_headers':["WTI","watson"],
        'training_split':0.80,
        'rounds':100,
    },
    {
        'n_in':3, 
        'm_out':1,
        'm_offset':0,
        'relative':False,
        'y_headers':["WTI"],
        'x_headers':["WTI"],
        'training_split':0.80,
        'rounds':100,
    },
    {
        'n_in':3, 
        'm_out':1,
        'm_offset':0,
        'relative':True,
        'y_headers':["change_WTI_1"],
        'x_headers':["WTI"],
        'training_split':0.80,
        'rounds':100,
    },
    {
        'n_in':3, 
        'm_out':1,
        'm_offset':0,
        'relative':True,
        'y_headers':["change_WTI_1"],
        'x_headers':["WTI","henry","Loughran-McDonald","vader_average","vader","watson"],
        'training_split':0.80,
        'rounds':100,
    },
    {
        'n_in':3, 
        'm_out':1,
        'm_offset':0,
        'relative':True,
        'y_headers':["change_WTI_1"],
        'x_headers':["WTI","vader_average","vader"],
        'training_split':0.80,
        'rounds':100,
    },
    {
        'n_in':3, 
        'm_out':1,
        'm_offset':0,
        'relative':True,
        'y_headers':["change_WTI_1"],
        'x_headers':["WTI","henry","Loughran-McDonald"],
        'training_split':0.80,
        'rounds':100,
    },
    {
        'n_in':3, 
        'm_out':1,
        'm_offset':0,
        'relative':True,
        'y_headers':["change_WTI_1"],
        'x_headers':["WTI","watson"],
        'training_split':0.80,
        'rounds':100,
    },
]

project_name = "batch_3"

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

def calculate_profit(prepared_dataset,y_hat, relative):
    barrels = 0.0
    value = 0.0
    profit = 0.0
    max_money = 0.0
    for i in range(len(y_hat)):
        price = prepared_dataset["WTI_t-1"][i]
        prediction = y_hat[i][0]
        if(((not relative) and prediction > price) or (relative and prediction > 0)):
            barrels += 1
            value += price
            if(value > max_money):
                max_money = value
        else:
            profit += price * barrels - value
            barrels = 0.0
            value = 0.0
    
    return({'profit':profit, 'max_money':max_money})


dataset = pd.read_csv('formatted_training_data.csv', header=0, index_col=0)
dataset.drop("Date", axis=1, inplace=True)
dataset.astype('float32')

for task in tasks:
    n_in = task['n_in']
    m_out = task['m_out']
    m_offset = task['m_offset']
    relative = task['relative']
    y_headers = task['y_headers']
    x_headers = task['x_headers']
    training_split = task['training_split']
    rounds = task['rounds']

    print(task)

    prepared_dataset = series_to_supervised(dataset, x_headers, y_headers, n_in=n_in, m_out=m_out, m_offset=m_offset)
    scaler = preprocessing.MinMaxScaler(feature_range=(0, 1))
    scaled_dataset = scaler.fit_transform(prepared_dataset)

    def create_model(optimizer="adam", init="glorot_uniform", layer_out=10, dropout=0.2):
        model = models.Sequential()
        model.add(layers.LSTM(layer_out, input_shape=(n_in, len(x_headers)), kernel_initializer=init, activation='relu', dropout=dropout, recurrent_dropout=dropout))
        model.add(layers.Dense(m_out, kernel_initializer=init))
        model.compile(loss='mse', optimizer=optimizer, metrics=['accuracy'])
        return model

    def find_best():

        split= math.floor(len(prepared_dataset)*training_split)
        train_x = scaled_dataset[:split, :][:, :-len(y_headers)*m_out]
        test_x = scaled_dataset[split:, :][:, :-len(y_headers)*m_out]
        train_x = train_x.reshape((train_x.shape[0], n_in, len(x_headers)))
        test_x = test_x.reshape((test_x.shape[0], n_in, len(x_headers)))
        train_y = scaled_dataset[:split, :][:, -len(y_headers)*m_out:]
        test_y = scaled_dataset[split:, :][:, -len(y_headers)*m_out:]

        model_results = pd.DataFrame()
        for optimizer in ['adam', 'Adagrad', 'rmsprop']:
            for init in ['glorot_uniform', 'normal', 'uniform']:
                for layer_out in [10, 12, 14, 16, 18, 20, 22, 24]:
                    for patience in [1000, 1200, 1400,1700, 2000]:
                        for batch_size in [len(train_x)]:
                            for dropout in [0, 0.05, 0.1, 0.15, 0.2, 0.25, 0.3, 0.35]:
                                es = callbacks.EarlyStopping(monitor='val_loss', mode='min', patience=patience, verbose=1, restore_best_weights=True)
                                model = create_binary(optimizer=optimizer, init=init, layer_out=layer_out, dropout=dropout)
                                model.fit(train_x, train_y, epochs=40000, batch_size=batch_size, validation_data=(test_x, test_y), verbose=0, callbacks=[es])
                                
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
                                    "batch_size":batch_size,
                                    "dropout":dropout
                                }
                                row = row.reshape((1,4))
                                model_results = model_results.append(pd.DataFrame(row),)
                                model_results.to_csv("./params.csv")

        model_results.sort_values(2, inplace=True, ascending=False)
        model_results.reset_index(drop=True, inplace=True)
        model_results.to_csv("./params.csv")

        return model_results.loc[0, 3]

    params = {
        "optimizer":"adam",
        "init":"normal",
        "layer_out":12,
        "patience":2500,
        "batch_size":scaled_dataset.shape[0],
        "dropout":0
    }

    np.random.seed(7)
    rmse = 0
    profit = 0
    max_money = 0

    best_model = {
        "model":None,
        "rmse":float("inf"),
        "profit":0,
        "max_money":0
    }

    for i in range(rounds):

        print(i)
        shuffeled_dataset = np.random.permutation(scaled_dataset)
        split= math.floor(len(shuffeled_dataset)*training_split)
        train_x = shuffeled_dataset[:split, :][:, :-len(y_headers)*m_out]
        test_x = shuffeled_dataset[split:, :][:, :-len(y_headers)*m_out]
        train_x = train_x.reshape((train_x.shape[0], n_in, len(x_headers)))
        test_x = test_x.reshape((test_x.shape[0], n_in, len(x_headers)))
        train_y = shuffeled_dataset[:split, :][:, -len(y_headers)*m_out:]
        test_y = shuffeled_dataset[split:, :][:, -len(y_headers)*m_out:]

        es = callbacks.EarlyStopping(monitor='val_loss', mode='min', patience=params['patience'], verbose=0, restore_best_weights=True)
        model = create_model(optimizer=params['optimizer'], init=params['init'], layer_out=params['layer_out'], dropout=params['dropout'])
        model.fit(train_x, train_y, epochs=40000, batch_size=params['batch_size'], validation_data=(test_x, test_y), verbose = 0, callbacks=[es])

        x = scaled_dataset[:, :][:,:-len(y_headers)*m_out]
        y = scaled_dataset[:, :][:,-len(y_headers)*m_out:]
        x = x.reshape((x.shape[0], n_in, len(x_headers)))

        y_hat = model.predict(x)
        x = x.reshape(x.shape[0], n_in*x.shape[2])
        y_hat = np.concatenate((x, y_hat), axis = 1)
        y = np.concatenate((x, y), axis = 1)

        y_hat = scaler.inverse_transform(y_hat.reshape((x.shape[0], prepared_dataset.shape[1])))[:,-m_out*len(y_headers):]
        y = scaler.inverse_transform(y.reshape((x.shape[0], prepared_dataset.shape[1])))[:,-m_out*len(y_headers):]

        model_rmse = math.sqrt(metrics.mean_squared_error(y, y_hat))
        if model_rmse < best_model["rmse"]:
            best_model["model"] = model
            best_model["rmse"] = model_rmse
        
        value = calculate_profit(prepared_dataset, y_hat, relative)
        profit += value["profit"]
        max_money += value["max_money"]
        rmse += model_rmse

    print('Test average RMSE: %.5f' % (rmse/rounds))
    print('Test average profit: %.5f' % (profit/rounds))
    print('Test average max_money: %.5f' % (max_money/rounds))
    print('Best RMSE: %.5f' % best_model["rmse"])

    x = scaled_dataset[:, :][:,:-len(y_headers)*m_out]
    y = scaled_dataset[:, :][:,-len(y_headers)*m_out:]
    x = x.reshape((x.shape[0], n_in, len(x_headers)))

    y_hat = best_model["model"].predict(x)
    x = x.reshape(x.shape[0], n_in*x.shape[2])
    y_hat = np.concatenate((x, y_hat), axis = 1)
    y = np.concatenate((x, y), axis = 1)

    y_hat = scaler.inverse_transform(y_hat.reshape((x.shape[0], prepared_dataset.shape[1])))[:,-m_out*len(y_headers):]
    y = scaler.inverse_transform(y.reshape((x.shape[0], prepared_dataset.shape[1])))[:,-m_out*len(y_headers):]

    pd.DataFrame(np.concatenate((y,y_hat), axis=1)).to_csv("out_test.csv")

    now = int(time.time()*1000.0)

    joblib.dump(scaler, f'./out/{project_name}_{now}.joblib')
    best_model["model"].save(f'./out/{project_name}_{now}.h5')
    with open(f'./out/{project_name}_{now}.txt', "w") as f:
        f.write('Test average RMSE: %.5f \n' % (rmse/rounds))
        f.write('Test average profit: %.5f \n' % (profit/rounds))
        f.write('Test average max_money: %.5f \n' % (max_money/rounds))
        for key, value in task.items():
            f.write(f'{key}:{value}\n')
        f.close()
    best_model["model"].summary()