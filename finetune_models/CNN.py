import os

os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'
import tensorflow as tf
from sklearn.model_selection import KFold
import numpy as np
import csv
import pickle
import time
from datetime import timedelta

import utils

inp_dir, dataset_type, network, lr, batch_size, epochs, seed, write_file, embed, layer = utils.parse_args()
n_classes = 2
np.random.seed(seed)
tf.compat.v1.set_random_seed(seed)

start = time.time()

if (embed == 'bert-base'):
    pretrained_weights = 'bert-base-uncased'
    n_hl = 12
    hidden_dim = 768

elif (embed == 'bert-large'):
    pretrained_weights = 'bert-large-uncased'
    n_hl = 24
    hidden_dim = 1024

file = open(inp_dir + dataset_type + '-' + embed + '.pkl', 'rb')

data = pickle.load(file)
data_x, data_y = list(zip(*data))
file.close()

# alphaW is responsible for which BERT layer embedding we will be using
if (layer == 'all'):
    alphaW = np.full([n_hl], 1 / n_hl)

else:
    alphaW = np.zeros([n_hl])
    alphaW[int(layer) - 1] = 1

# just changing the way data is stored (tuples of minibatches) and getting the output for the required layer of BERT using alphaW
# data_x[ii].shape = (12, batch_size, 768)
inputs = []
targets = []

n_batches = len(data_y)

for ii in range(n_batches):
    inputs.extend(np.einsum('k,kij->ij', alphaW, data_x[ii]))
    targets.extend(data_y[ii])

# inputs = np.array(inputs)
inputs = np.reshape(inputs, (-1, hidden_dim, 1))
# convert targets to one-hot encoding
targets = tf.keras.utils.to_categorical(np.array(targets), num_classes=n_classes)

n_data = targets.shape[0]
kf = KFold(n_splits=10, shuffle=True, random_state=0)
k = 0
loss_list = []; acc_list = []; train_acc = []; train_loss = []; val_acc = []; val_loss = []

for train_index, test_index in kf.split(inputs):
    X_train, X_test = inputs[train_index], inputs[test_index]
    y_train, y_test = targets[train_index], targets[test_index]
    model = tf.keras.models.Sequential()
    #define the neural network architecture
    if (network == 'fc'):
        model.add(tf.keras.layers.Conv1D(64, 3, input_shape=(hidden_dim, 1), activation='relu'))
        model.add(tf.keras.layers.MaxPooling1D(2))
        model.add(tf.keras.layers.Conv1D(8, 3, activation='relu'))
        model.add(tf.keras.layers.MaxPooling1D(2))
        model.add(tf.keras.layers.Flatten())
        model.add(tf.keras.layers.Dense(n_classes))

    model.compile(optimizer=tf.keras.optimizers.Adam(learning_rate=lr),
                  loss=tf.keras.losses.BinaryCrossentropy(from_logits=True),
                  metrics=['mse', 'accuracy'])

    print(model.summary())
    validation_split = 0.15
    history = model.fit(X_train, y_train, epochs=epochs, batch_size=batch_size,
                        validation_split=validation_split, verbose = 1)
    result = model.evaluate(X_test, y_test, batch_size=batch_size)

    loss_list.append(result[0]); acc_list.append(result[1])
    train_acc.append(history.history['accuracy'])
    train_loss.append(history.history['loss'])
    val_acc.append(history.history['val_accuracy'])
    val_loss.append(history.history['val_loss'])

    print('acc: ', history.history['accuracy'])
    print('val acc: ', history.history['val_accuracy'])
    print('loss: ', history.history['loss'])
    print('val loss: ', history.history['val_loss'])
    print(timedelta(seconds=int(time.time()-start)), end=' ')

total_acc = np.mean(acc_list)
total_loss = np.mean(loss_list)
