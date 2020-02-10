from pandas import read_csv, DataFrame, concat, Series
from sklearn import preprocessing
from keras.models import Sequential
from keras.layers import Dense
from keras.layers import LSTM
from keras.callbacks import EarlyStopping
from matplotlib import pyplot
from numpy import concatenate, append, array, nan
from sklearn.metrics import mean_squared_error
from math import sqrt

# convert series to supervised learning
def series_to_supervised(data, headers, n_in=1, n_out=1, dropnan=True,):
    n_vars = 1 if type(data) is list else data.shape[1]
    df = DataFrame(data)
    cols, names = list(), list()
	# input sequence (t-n, ... t-1)
    for i in range(n_in, 0, -1):
        cols.append(df.shift(i))
        names += [f'{headers[j]}_(t-{i})' for j in range(n_vars)]
	# forecast sequence (t, t+1, ... t+n)
    for i in range(0, n_out):
        cols.append(df.shift(-i))
        if i == 0:
            names += [f'{headers[j]}_t)' for j in range(n_vars)]
        else:
            names += [f'{headers[j]}_(t+{i})' for j in range(n_vars)]
	# put it all together
    agg = concat(cols, axis=1)
    agg.columns = names
	# drop rows with NaN values
    if dropnan:
        agg.dropna(inplace=True)
    return agg

# load dataset
dataset = read_csv('formatted_training_data.csv', header=0, index_col=0)
dataset.drop("Date", axis=1, inplace=True)
values = dataset.values
# ensure all data is float
values = values.astype('float32')
# normalize features
scaler = preprocessing.MinMaxScaler(feature_range=(0, 1))
scaled = scaler.fit_transform(values)
# frame as supervised learning
steps = 5
features = 4
reframed = series_to_supervised(scaled, dataset.columns.values, steps, 1)

# split into train and test sets
values = reframed.values
train = values[:710, :]
test = values[710:, :]

# split into input and outputs
train_X, train_y = train[:, :-features], train[:, -features:]
test_X, test_y = test[:, :-features], test[:, -features:]
# reshape input to be 3D [samples, timesteps, features]
train_X = train_X.reshape((train_X.shape[0], steps, features))
test_X = test_X.reshape((test_X.shape[0], steps, features))

# design network
model = Sequential()
model.add(LSTM(40, input_shape=(train_X.shape[1], train_X.shape[2])))
model.add(Dense(4))
model.compile(loss='mae', optimizer='adam')
# fit network
es = EarlyStopping(monitor='val_loss', mode='min', patience=1000, verbose=1, restore_best_weights=True)
history = model.fit(train_X, train_y, epochs=15000, batch_size=len(train_X), validation_data=(test_X, test_y), verbose=2, shuffle=False, callbacks=[es])
#plot history
pyplot.plot(history.history['loss'], label='train')
pyplot.plot(history.history['val_loss'], label='test')
pyplot.legend()
pyplot.show()

step_lines = 6
future_steps = 5

#pyplot.plot(dataset.loc[:,"brent"], label="brent")
cols = []
for i in range(0, len(values), step_lines):
    predictions = array(values[i].reshape((steps+1, features))[-1])
    frame = array(values[i, :-features].reshape((1, steps, features)), copy=True)
    for j in range(future_steps):
        prediction = model.predict(frame)
        intermediate = append(frame[0], prediction[0]).reshape((steps+1, features))
        frame[0] = intermediate[1:,:]
        predictions = append(predictions, prediction).reshape((j+2),4)
    predictions = scaler.inverse_transform(predictions)

    arr = array([nan for x in range(i)])
    arr = append(arr, predictions[:, 3])
    arr = append(arr, [nan for x in range(len(values)-len(predictions[:,3])-i*step_lines)])
    cols.append(DataFrame(arr))
    #pyplot.plot([i+k+steps for k in range(len(predictions))], predictions[:, 3])

df = concat(cols, axis=1)
df.to_csv("../predictions_out.csv")
#pyplot.show()

temp = dataset.loc[steps+1:,"brent"]
prediction = append(model.predict(train_X),model.predict(test_X))
prediction = prediction.reshape((int(len(prediction)/4),4))
prediction = scaler.inverse_transform(prediction)
prediction = prediction[:,3]

pyplot.plot(dataset.loc[:,"brent"], label="brent")
pyplot.plot([i for i in range(steps+1, steps+1+len(prediction))], prediction, label="predicted")
pyplot.legend()
pyplot.show()

df = DataFrame(prediction)
df.to_csv("../predicted_graph.csv")

#predict
yhat = model.predict(test_X)
test_X = test_X.reshape((test_X.shape[0], steps*features))
# invert scaling for forecast
#inv_yhat = concatenate((yhat, test_X[:, -4:]), axis=1)
inv_yhat = scaler.inverse_transform(yhat)
inv_yhat = inv_yhat[:,0]
# invert scaling for actual
test_y = test_y.reshape((len(test_y), 4))
#inv_y = concatenate((test_y, test_X[:, -3:]), axis=1)
inv_y = scaler.inverse_transform(test_y)
inv_y = inv_y[:,0]
# calculate RMSE
rmse = sqrt(mean_squared_error(inv_y, inv_yhat))
print('Test RMSE: %.3f' % rmse)