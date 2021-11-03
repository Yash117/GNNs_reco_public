# -*- coding: utf-8 -*-
"""GNNs for Energy Reconstruction.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1rMO5ggPIG-fWrfRPndWJx3JXuCEVFmes

# Energy Reconstruction using Graph Regression in the Spektral library of python

# Importing libraries:
"""

# Commented out IPython magic to ensure Python compatibility.
# %%time
#!pip install spektral

import numpy as np
import itertools
import os
import shutil;
import random
import glob
import matplotlib.pyplot as plt
import warnings
import subprocess
import pandas as pd
import scipy 
from scipy.stats import norm
from matplotlib.patches import Rectangle
import scipy
from scipy.stats import norm
from keras.callbacks import EarlyStopping

from spektral.data import DisjointLoader
from spektral.datasets import QM9
from spektral.layers import ECCConv, GlobalSumPool
from spektral import datasets
from spektral.data import Dataset, DisjointLoader, Graph
from spektral.layers import GCSConv, GlobalAvgPool
from spektral.layers.pooling import TopKPool
from spektral.transforms.normalize_adj import NormalizeAdj

import scipy.sparse as sp
import tensorflow as tf
from tensorflow.keras.layers import Dense
from tensorflow.keras.losses import MeanAbsoluteError
from tensorflow.keras.metrics import categorical_accuracy
from tensorflow.keras.models import Model
from tensorflow.keras.optimizers import Adam



"""# Loading data:"""

DF_training_input = pd.DataFrame(np.load('/content/drive/MyDrive/SKKU_JSNS^2/v6_250k_samples_JSNS^2/training_input.npy'))
DF_training_output = pd.DataFrame(np.load('/content/drive/MyDrive/SKKU_JSNS^2/v6_250k_samples_JSNS^2/training_output.npy'))
DF_test_input = pd.DataFrame(np.load('/content/drive/MyDrive/SKKU_JSNS^2/v6_250k_samples_JSNS^2/test_input.npy'))
DF_test_output = pd.DataFrame(np.load('/content/drive/MyDrive/SKKU_JSNS^2/v6_250k_samples_JSNS^2/test_output.npy'))

DF_training_input = DF_training_input/(500)

for i in range(len(DF_training_input)):
  for j in range(96):
    if DF_training_input[j][i] > 1.0:
      DF_training_input[j][i] = 1.0

DF_test_input = DF_test_input/(500)

for i in range(len(DF_test_input)):
  for j in range(96):
    if DF_test_input[j][i] > 1.0:
      DF_test_input[j][i] = 1.0

"""# Extracting coordinates:"""

d_coordinates = pd.read_csv('/content/drive/MyDrive/SKKU_JSNS^2/PMT_coordinates.csv')

"""# Defining some variables:"""

learning_rate = 1e-2  # Learning rate
epochs = 10  # Number of training epochs
es_patience = 10  # Patience for early stopping
batch_size = 32  # Batch size
max_no_of_graphs_training = DF_training_input.shape[0] 
max_no_of_graphs_test = DF_test_input.shape[0]

"""# Creating dataset (function):

##Creating the adjacency matrix (remains same for all graphs, only node features change):
"""

adj = np.zeros((96,96)) 

for k1 in range(96): 
  for k2 in range(96): 
    dist = ((d_coordinates['x'][k1] - d_coordinates['x'][k2])**2 + (d_coordinates['y'][k1] - d_coordinates['y'][k2])**2 + (d_coordinates['z'][k1] - d_coordinates['z'][k2])**2)**0.5 
    inv_sq = 0 
    if dist != 0: 
      inv_sq = 1 / (dist**2) 
    adj[k1][k2] = inv_sq

"""Max-min normalization:"""

min_adj = adj.min()
max_adj = adj.max()
for i in range(96):
  for j in range(96):
    adj[i][j] = (adj[i][j] - min_adj) / (max_adj - min_adj)

"""Making the diagonal elements = 1:"""

for i in range(96):
  for j in range(96):
    if i == j:
      adj[i][j] = 1

"""Adjacency matrix is symmetric:"""

adj == adj.T

"""##Classes to create datasets:

Training dataset:
"""

class MyDataset(Dataset):
    def __init__(self, n_samples, **kwargs): 
        self.n_samples = n_samples 
        
        super().__init__(**kwargs) 

    def read(self): 
      all_graphs = [] 
      for i in range(len(DF_training_output[:max_no_of_graphs_training])): 
        # Node features 
        x = np.array(DF_training_input.loc[i]).reshape(96,1) 

        # Edges 
        a = adj 

        # Labels 
        y = np.zeros(1) 
        y[0] = DF_training_output[0][i] 

        all_graphs.append(Graph(x=x, a=a, y=y)) 

      # We must return a list of Graph objects 
      return [all_graphs[i] for i in range(self.n_samples)]

"""Test dataset:"""

class MyTestDataset(Dataset):
    def __init__(self, n_samples, **kwargs):
        self.n_samples = n_samples
        
        super().__init__(**kwargs)

    def read(self):
      all_graphs = []
      for i in range(len(DF_test_output[:max_no_of_graphs_test])): 
        # Node features 
        x = np.array(DF_test_input.loc[i]).reshape(96,1) 

        # Edges 
        a = adj 

        # Labels 
        y = np.zeros(1) 
        y[0] = DF_test_output[0][i] 

        all_graphs.append(Graph(x=x, a=a, y=y)) 

      # We must return a list of Graph objects 
      return [all_graphs[i] for i in range(self.n_samples)]

"""Mono energetic data imports:"""

D_mono_input1 = pd.read_csv('/content/drive/MyDrive/SKKU_JSNS^2/Mono-energetic_clean_data/1MeV_input.csv')
D_mono_output1 = pd.read_csv('/content/drive/MyDrive/SKKU_JSNS^2/Mono-energetic_clean_data/1MeV_output.csv')
D_mono_output1.columns = [0] 
#cleaning the mono-energetic data 
D_mono_input1 = D_mono_input1/(500) 
D_mono_input1.columns = np.arange(96) 
for k1 in range(len(D_mono_input1)): 
  for k2 in range(96): 
    if D_mono_input1[k2][k1] > 1.0: 
      D_mono_input1[k2][k1] = 1.0 


D_mono_input5 = pd.read_csv('/content/drive/MyDrive/SKKU_JSNS^2/Mono-energetic_clean_data/5MeV_input.csv')
D_mono_output5 = pd.read_csv('/content/drive/MyDrive/SKKU_JSNS^2/Mono-energetic_clean_data/5MeV_output.csv')
D_mono_output5.columns = [0] 
#cleaning the mono-energetic data 
D_mono_input5 = D_mono_input5/(500) 
D_mono_input5.columns = np.arange(96) 
for k1 in range(len(D_mono_input5)): 
  for k2 in range(96): 
    if D_mono_input5[k2][k1] > 1.0: 
      D_mono_input5[k2][k1] = 1.0 


D_mono_input8 = pd.read_csv('/content/drive/MyDrive/SKKU_JSNS^2/Mono-energetic_clean_data/8MeV_input.csv')
D_mono_output8 = pd.read_csv('/content/drive/MyDrive/SKKU_JSNS^2/Mono-energetic_clean_data/8MeV_output.csv')
D_mono_output8.columns = [0] 
#cleaning the mono-energetic data 
D_mono_input8 = D_mono_input8/(500) 
D_mono_input8.columns = np.arange(96) 
for k1 in range(len(D_mono_input8)): 
  for k2 in range(96): 
    if D_mono_input8[k2][k1] > 1.0: 
      D_mono_input8[k2][k1] = 1.0 


D_mono_input10 = pd.read_csv('/content/drive/MyDrive/SKKU_JSNS^2/Mono-energetic_clean_data/10MeV_input.csv')
D_mono_output10 = pd.read_csv('/content/drive/MyDrive/SKKU_JSNS^2/Mono-energetic_clean_data/10MeV_output.csv')
D_mono_output10.columns = [0] 
#cleaning the mono-energetic data 
D_mono_input10 = D_mono_input10/(500) 
D_mono_input10.columns = np.arange(96) 
for k1 in range(len(D_mono_input10)): 
  for k2 in range(96): 
    if D_mono_input10[k2][k1] > 1.0: 
      D_mono_input10[k2][k1] = 1.0 


D_mono_input20 = pd.read_csv('/content/drive/MyDrive/SKKU_JSNS^2/Mono-energetic_clean_data/20MeV_input.csv')
D_mono_output20 = pd.read_csv('/content/drive/MyDrive/SKKU_JSNS^2/Mono-energetic_clean_data/20MeV_output.csv')
D_mono_output20.columns = [0] 
#cleaning the mono-energetic data 
D_mono_input20 = D_mono_input20/(500) 
D_mono_input20.columns = np.arange(96) 
for k1 in range(len(D_mono_input20)): 
  for k2 in range(96): 
    if D_mono_input20[k2][k1] > 1.0: 
      D_mono_input20[k2][k1] = 1.0 


D_mono_input30 = pd.read_csv('/content/drive/MyDrive/SKKU_JSNS^2/Mono-energetic_clean_data/30MeV_input.csv')
D_mono_output30 = pd.read_csv('/content/drive/MyDrive/SKKU_JSNS^2/Mono-energetic_clean_data/30MeV_output.csv')
D_mono_output30.columns = [0] 
#cleaning the mono-energetic data 
D_mono_input30 = D_mono_input30/(500) 
D_mono_input30.columns = np.arange(96) 
for k1 in range(len(D_mono_input30)): 
  for k2 in range(96): 
    if D_mono_input30[k2][k1] > 1.0: 
      D_mono_input30[k2][k1] = 1.0 


D_mono_input40 = pd.read_csv('/content/drive/MyDrive/SKKU_JSNS^2/Mono-energetic_clean_data/40MeV_input.csv')
D_mono_output40 = pd.read_csv('/content/drive/MyDrive/SKKU_JSNS^2/Mono-energetic_clean_data/40MeV_output.csv')
D_mono_output40.columns = [0] 
#cleaning the mono-energetic data 
D_mono_input40 = D_mono_input40/(500) 
D_mono_input40.columns = np.arange(96) 
for k1 in range(len(D_mono_input40)): 
  for k2 in range(96): 
    if D_mono_input40[k2][k1] > 1.0: 
      D_mono_input40[k2][k1] = 1.0

"""Mono-energetic dataset classes:

1 MeV:
"""

class MyMonoEnergeticDataset1(Dataset):

    def __init__(self, n_samples, **kwargs):
        self.n_samples = n_samples
        
        super().__init__(**kwargs)

    def read(self):
      all_graphs = []
      for i in range(len(D_mono_output1)): 
        # Node features 
        x = np.array(D_mono_input1.loc[i]).reshape(96,1) 

        # Edges 
        a = adj 

        # Labels 
        y = np.zeros(1) 
        y[0] = D_mono_output1[0][i] 

        all_graphs.append(Graph(x=x, a=a, y=y)) 

      # We must return a list of Graph objects 
      return [all_graphs[i] for i in range(self.n_samples)]

"""5 MeV:"""

class MyMonoEnergeticDataset5(Dataset):
  def __init__(self, n_samples, **kwargs):
    self.n_samples = n_samples
    
    super().__init__(**kwargs)

  def read(self):
    all_graphs = []
    for i in range(len(D_mono_output5)): 
      # Node features 
      x = np.array(D_mono_input5.loc[i]).reshape(96,1) 

      # Edges 
      a = adj 

      # Labels 
      y = np.zeros(1) 
      y[0] = D_mono_output5[0][i] 

      all_graphs.append(Graph(x=x, a=a, y=y)) 

    # We must return a list of Graph objects 
    return [all_graphs[i] for i in range(self.n_samples)]

"""8 MeV:"""

class MyMonoEnergeticDataset8(Dataset):
  def __init__(self, n_samples, **kwargs):
    self.n_samples = n_samples
    
    super().__init__(**kwargs)

  def read(self):
    all_graphs = []
    for i in range(len(D_mono_output8)): 
      # Node features 
      x = np.array(D_mono_input8.loc[i]).reshape(96,1) 

      # Edges 
      a = adj 

      # Labels 
      y = np.zeros(1) 
      y[0] = D_mono_output8[0][i] 

      all_graphs.append(Graph(x=x, a=a, y=y)) 

    # We must return a list of Graph objects 
    return [all_graphs[i] for i in range(self.n_samples)]

"""10 MeV:"""

class MyMonoEnergeticDataset10(Dataset):
  def __init__(self, n_samples, **kwargs):
    self.n_samples = n_samples
    
    super().__init__(**kwargs)

  def read(self):
    all_graphs = []
    for i in range(len(D_mono_output10)): 
      # Node features 
      x = np.array(D_mono_input10.loc[i]).reshape(96,1) 

      # Edges 
      a = adj 

      # Labels 
      y = np.zeros(1) 
      y[0] = D_mono_output10[0][i] 

      all_graphs.append(Graph(x=x, a=a, y=y)) 

    # We must return a list of Graph objects 
    return [all_graphs[i] for i in range(self.n_samples)]

"""20 MeV:"""

class MyMonoEnergeticDataset20(Dataset):
  def __init__(self, n_samples, **kwargs):
    self.n_samples = n_samples
    
    super().__init__(**kwargs)

  def read(self):
    all_graphs = []
    for i in range(len(D_mono_output20)): 
      # Node features 
      x = np.array(D_mono_input20.loc[i]).reshape(96,1) 

      # Edges 
      a = adj 

      # Labels 
      y = np.zeros(1) 
      y[0] = D_mono_output20[0][i] 

      all_graphs.append(Graph(x=x, a=a, y=y)) 

    # We must return a list of Graph objects 
    return [all_graphs[i] for i in range(self.n_samples)]

"""30 MeV:"""

class MyMonoEnergeticDataset30(Dataset):
  def __init__(self, n_samples, **kwargs):
    self.n_samples = n_samples
    
    super().__init__(**kwargs)

  def read(self):
    all_graphs = []
    for i in range(len(D_mono_output30)): 
      # Node features 
      x = np.array(D_mono_input30.loc[i]).reshape(96,1) 

      # Edges 
      a = adj 

      # Labels 
      y = np.zeros(1) 
      y[0] = D_mono_output30[0][i] 

      all_graphs.append(Graph(x=x, a=a, y=y)) 

    # We must return a list of Graph objects 
    return [all_graphs[i] for i in range(self.n_samples)]

"""40 MeV:"""

class MyMonoEnergeticDataset40(Dataset):
  def __init__(self, n_samples, **kwargs):
    self.n_samples = n_samples
    
    super().__init__(**kwargs)

  def read(self):
    all_graphs = []
    for i in range(len(D_mono_output40)): 
      # Node features 
      x = np.array(D_mono_input40.loc[i]).reshape(96,1) 

      # Edges 
      a = adj 

      # Labels 
      y = np.zeros(1) 
      y[0] = D_mono_output40[0][i] 

      all_graphs.append(Graph(x=x, a=a, y=y)) 

    # We must return a list of Graph objects 
    return [all_graphs[i] for i in range(self.n_samples)]

"""## Creating dataset:

Training data:
"""

data = MyDataset(max_no_of_graphs_training)

data

idxs = np.random.permutation(len(data))
loader_tr = DisjointLoader(data, batch_size=batch_size, epochs=epochs)

"""# Defining train step:"""

def train_step(inputs, target):
    with tf.GradientTape() as tape:
        predictions = model(inputs, training=True)
        loss = loss_fn(target, predictions) + sum(model.losses)
    gradients = tape.gradient(loss, model.trainable_variables)
    optimizer.apply_gradients(zip(gradients, model.trainable_variables))
    
    return loss, predictions

"""# Model definition:"""

class Net(Model):
    def __init__(self):
        super().__init__()
        self.conv1 = GCSConv(32, activation="relu")
        self.pool1 = TopKPool(ratio=0.5)
        self.conv2 = GCSConv(32, activation="relu")
        self.pool2 = TopKPool(ratio=0.5)
        self.conv3 = GCSConv(32, activation="relu")
        self.global_pool = GlobalAvgPool()
        self.dense = Dense(data.n_labels, activation="linear")

    def call(self, inputs):
        x, a, i = inputs
        x = self.conv1([x, a])
        x1, a1, i1 = self.pool1([x, a, i])
        x1 = self.conv2([x1, a1])
        x2, a2, i2 = self.pool1([x1, a1, i1])
        x2 = self.conv3([x2, a2])
        output = self.global_pool([x2, i2])
        output = self.dense(output)

        return output

model = Net()
optimizer = Adam(lr=learning_rate)
loss_fn = MeanAbsoluteError()

epoch = step = 0
best_val_loss = np.inf
best_weights = None
patience = es_patience
results = []

"""#Training:"""

combined_predictions = []
for batch in loader_tr:
    step += 1
    loss, prediction = train_step(*batch)
    combined_predictions.append(prediction)
    results.append((loss))
    if step == loader_tr.steps_per_epoch:
        step = 0
        epoch += 1

        # Compute validation loss and accuracy
        #val_loss, val_acc = evaluate(loader_va)
        print(
            "Epoch: {}, Loss: {:.3f}".format(
                epoch, loss
            )
        )

"""32 graphs predictions at a time:

No of entries in combined predictions = ceil(no. of graphs / batch size)*epoch size

I need the final ceil(no. of graphs / batch size) indices from the combined_predictions list to get the final training output:
"""

len(combined_predictions)

combined_predictions[0]

"""# Saving the model:"""

model.save('/content/drive/MyDrive/SKKU_JSNS^2/GNNs/model2', save_format="tf")

model.save_weights('/content/drive/MyDrive/SKKU_JSNS^2/GNNs/model2_weights')

"""# Loading the model:"""

model.load_weights('/content/drive/MyDrive/SKKU_JSNS^2/GNNs/model2_weights/model2_weights')

#model.load('/content/drive/MyDrive/SKKU_JSNS^2/GNNs/model2')

"""# Making predictions:"""

max_no_of_graphs_test

"""No of entries in combined predictions = ceil(no. of graphs / batch size)*epoch size"""

data_test = MyTestDataset(math.floor(max_no_of_graphs_test/32) * 32)

"""Taking only the 19296 graphs, for neatness:"""

data_test

loader_test = DisjointLoader(data_test, batch_size=32, epochs=1)

"""Predictions are made by training the model on the test graphs, and then reload the original model saved, so as to forget the weights trained using the test data:"""

combined_predictions = []
loss_combined = []
epoch_count = 0
for batch in loader_test:
  loss, prediction = train_step(*batch)
  combined_predictions.append(prediction)
  loss_combined.append(loss)
  if (len(combined_predictions)% math.floor(max_no_of_graphs_test/32)) == 0:
    epoch_count = epoch_count + 1
    #print(epoch_count)
    print(sum(loss_combined)/len(loss_combined))
    model.load_weights('/content/drive/MyDrive/SKKU_JSNS^2/GNNs/model2_weights/model2_weights') #reload original model
    #if not ((epoch_count == 9) or (epoch_count == 10)):
    #  combined_predictions = []
  #predictions = model(batch, training=False)

mae = float(np.array(sum(loss_combined)/len(loss_combined)))

len(combined_predictions)

"""Calculating number of graphs predicted on:"""

n_graphs = math.floor(max_no_of_graphs_test/32) * 32

n_graphs

final_predictions = np.zeros(n_graphs)

for i in range(len(combined_predictions)): 
  a = np.array(combined_predictions[i]).reshape(32) 
  for j in range(32):
    final_predictions[(32*i) + j] = a[j]

final_predictions

"""# Getting truth values from the shuffled graphs:"""

DF_graphs_test_y = pd.DataFrame(np.zeros(n_graphs))

for i in range(len(DF_graphs_test_y)):
  DF_graphs_test_y[0][i] = data_test[i].y[0]

"""# Correlation plot:"""

fig = plt.figure(figsize=(10, 10))
D_pred = pd.DataFrame(final_predictions)
plt.hexbin(DF_graphs_test_y[0], D_pred[0], bins = 301, mincnt = 0.1)
cbar = plt.colorbar()

cbar.ax.tick_params(labelsize=25)
cbar.set_label('# of events',  fontsize = 20)
params = {'mathtext.default': 'regular' }          
plt.rcParams.update(params)
#plt.plot(range(60), range(60), color = 'red')
plt.xticks(fontsize=20)
plt.yticks(fontsize=20)
plt.xlabel('$E_{MC} $(MeV)', fontsize = 20)
plt.ylabel('$E_{pred}$ (MeV)', fontsize = 20)
plt.title(label = 'GNN architecture \n Optimization technique: Manual\n MAE = ' + str(round(mae,4)) + '\n \n $E_{pred}$ vs $E_{MC} $' , fontsize = 10)
#plt.savefig("/content/drive/MyDrive/SKKU_JSNS^2/Plots/GNNs/correlation.jpeg")

"""# Loading mono-energetic data:

Reminder: 32 is the batch size
"""

#Loading mono-energetic data in the form of graphs
n_graphs1 = math.floor(len(D_mono_input1)/32) * 32
data_test1 = MyMonoEnergeticDataset1(n_graphs1)
n_graphs5 = math.floor(len(D_mono_input5)/32) * 32
data_test5 = MyMonoEnergeticDataset5(n_graphs5)
n_graphs8 = math.floor(len(D_mono_input8)/32) * 32
data_test8 = MyMonoEnergeticDataset8(n_graphs8)
n_graphs10 = math.floor(len(D_mono_input10)/32) * 32
data_test10 = MyMonoEnergeticDataset10(n_graphs10)
n_graphs20 = math.floor(len(D_mono_input20)/32) * 32
data_test20 = MyMonoEnergeticDataset20(n_graphs20)
n_graphs30 = math.floor(len(D_mono_input30)/32) * 32
data_test30 = MyMonoEnergeticDataset30(n_graphs30)
n_graphs40 = math.floor(len(D_mono_input40)/32) * 32
data_test40 = MyMonoEnergeticDataset40(n_graphs40)

#loading mono-energetic test data to the DisjointLoader
loader_test1 = DisjointLoader(data_test1, batch_size=32, epochs=1) 
loader_test5 = DisjointLoader(data_test5, batch_size=32, epochs=1) 
loader_test8 = DisjointLoader(data_test8, batch_size=32, epochs=1) 
loader_test10 = DisjointLoader(data_test10, batch_size=32, epochs=1) 
loader_test20 = DisjointLoader(data_test20, batch_size=32, epochs=1) 
loader_test30 = DisjointLoader(data_test30, batch_size=32, epochs=1) 
loader_test40 = DisjointLoader(data_test40, batch_size=32, epochs=1) 

#empty arrays to store the final mono-energetic predictions
final_predictions1 = np.zeros(n_graphs1)
final_predictions5 = np.zeros(n_graphs5)
final_predictions8 = np.zeros(n_graphs8)
final_predictions10 = np.zeros(n_graphs10)
final_predictions20 = np.zeros(n_graphs20)
final_predictions30 = np.zeros(n_graphs30)
final_predictions40 = np.zeros(n_graphs40)

"""Making Predictions on the Mono-energetic data graphs:

1 MeV:
"""

#Lines with hashtags need change of variables:

model.load_weights('/content/drive/MyDrive/SKKU_JSNS^2/GNNs/model2_weights/model2_weights')
combined_predictions1 = [] ##
loss_combined1 = [] #
epoch_count = 0
for batch in loader_test1: #
  loss, prediction = train_step(*batch) 
  combined_predictions1.append(prediction) #
  loss_combined1.append(loss) #
  if (len(combined_predictions1)% math.floor(len(D_mono_input1)/32)) == 0: #
    epoch_count = epoch_count + 1
    #print(epoch_count)
    #print(sum(loss_combined)/len(loss_combined))
    model.load_weights('/content/drive/MyDrive/SKKU_JSNS^2/GNNs/model2_weights/model2_weights')

for i in range(len(combined_predictions1)):  #
  a = np.array(combined_predictions1[i]).reshape(32) #
  for j in range(32):
    final_predictions1[(32*i) + j] = a[j] #

D_pred1 = pd.DataFrame(final_predictions1) #

DF_graphs_test_y1 = pd.DataFrame(np.zeros(n_graphs1)) #

for i in range(len(DF_graphs_test_y1)): #
  DF_graphs_test_y1[0][i] = data_test1[i].y[0] #

"""5 MeV:"""

#Lines with hashtags need change of variables:

model.load_weights('/content/drive/MyDrive/SKKU_JSNS^2/GNNs/model2_weights/model2_weights')
combined_predictions5 = [] ##
loss_combined5 = [] #
epoch_count = 0
for batch in loader_test5: #
  loss, prediction = train_step(*batch) 
  combined_predictions5.append(prediction) #
  loss_combined5.append(loss) #
  if (len(combined_predictions5)% math.floor(len(D_mono_input5)/32)) == 0: #
    epoch_count = epoch_count + 1
    #print(epoch_count)
    #print(sum(loss_combined)/len(loss_combined))
    model.load_weights('/content/drive/MyDrive/SKKU_JSNS^2/GNNs/model2_weights/model2_weights')

for i in range(len(combined_predictions5)):  #
  a = np.array(combined_predictions5[i]).reshape(32) #
  for j in range(32):
    final_predictions5[(32*i) + j] = a[j] #

D_pred5 = pd.DataFrame(final_predictions5) #

DF_graphs_test_y5 = pd.DataFrame(np.zeros(n_graphs5)) #

for i in range(len(DF_graphs_test_y5)): #
  DF_graphs_test_y5[0][i] = data_test5[i].y[0] #

"""8 MeV:"""

#Lines with hashtags need change of variables:

model.load_weights('/content/drive/MyDrive/SKKU_JSNS^2/GNNs/model2_weights/model2_weights')
combined_predictions8 = [] ##
loss_combined8 = [] #
epoch_count = 0
for batch in loader_test8: #
  loss, prediction = train_step(*batch) 
  combined_predictions8.append(prediction) #
  loss_combined8.append(loss) #
  if (len(combined_predictions8)% math.floor(len(D_mono_input8)/32)) == 0: #
    epoch_count = epoch_count + 1
    #print(epoch_count)
    #print(sum(loss_combined)/len(loss_combined))
    model.load_weights('/content/drive/MyDrive/SKKU_JSNS^2/GNNs/model2_weights/model2_weights')

for i in range(len(combined_predictions8)):  #
  a = np.array(combined_predictions8[i]).reshape(32) #
  for j in range(32):
    final_predictions8[(32*i) + j] = a[j] #

D_pred8 = pd.DataFrame(final_predictions8) #

DF_graphs_test_y8 = pd.DataFrame(np.zeros(n_graphs8)) #

for i in range(len(DF_graphs_test_y8)): #
  DF_graphs_test_y8[0][i] = data_test8[i].y[0] #

"""10 MeV:"""

#Lines with hashtags need change of variables:

model.load_weights('/content/drive/MyDrive/SKKU_JSNS^2/GNNs/model2_weights/model2_weights')
combined_predictions10 = [] ##
loss_combined10 = [] #
epoch_count = 0
for batch in loader_test10: #
  loss, prediction = train_step(*batch) 
  combined_predictions10.append(prediction) #
  loss_combined10.append(loss) #
  if (len(combined_predictions10)% math.floor(len(D_mono_input10)/32)) == 0: #
    epoch_count = epoch_count + 1
    #print(epoch_count)
    #print(sum(loss_combined)/len(loss_combined))
    model.load_weights('/content/drive/MyDrive/SKKU_JSNS^2/GNNs/model2_weights/model2_weights')

for i in range(len(combined_predictions10)):  #
  a = np.array(combined_predictions10[i]).reshape(32) #
  for j in range(32):
    final_predictions10[(32*i) + j] = a[j] #

D_pred10 = pd.DataFrame(final_predictions10) #

DF_graphs_test_y10 = pd.DataFrame(np.zeros(n_graphs10)) #

for i in range(len(DF_graphs_test_y10)): #
  DF_graphs_test_y10[0][i] = data_test10[i].y[0] #

"""20 MeV:"""

#Lines with hashtags need change of variables:

model.load_weights('/content/drive/MyDrive/SKKU_JSNS^2/GNNs/model2_weights/model2_weights')
combined_predictions20 = [] ##
loss_combined20 = [] #
epoch_count = 0
for batch in loader_test20: #
  loss, prediction = train_step(*batch) 
  combined_predictions20.append(prediction) #
  loss_combined20.append(loss) #
  if (len(combined_predictions20)% math.floor(len(D_mono_input20)/32)) == 0: #
    epoch_count = epoch_count + 1
    #print(epoch_count)
    #print(sum(loss_combined)/len(loss_combined))
    model.load_weights('/content/drive/MyDrive/SKKU_JSNS^2/GNNs/model2_weights/model2_weights')

for i in range(len(combined_predictions20)):  #
  a = np.array(combined_predictions20[i]).reshape(32) #
  for j in range(32):
    final_predictions20[(32*i) + j] = a[j] #

D_pred20 = pd.DataFrame(final_predictions20) #

DF_graphs_test_y20 = pd.DataFrame(np.zeros(n_graphs20)) #

for i in range(len(DF_graphs_test_y20)): #
  DF_graphs_test_y20[0][i] = data_test20[i].y[0] #

"""30 MeV:"""

#Lines with hashtags need change of variables:

model.load_weights('/content/drive/MyDrive/SKKU_JSNS^2/GNNs/model2_weights/model2_weights')
combined_predictions30 = [] ##
loss_combined30 = [] #
epoch_count = 0
for batch in loader_test30: #
  loss, prediction = train_step(*batch) 
  combined_predictions30.append(prediction) #
  loss_combined30.append(loss) #
  if (len(combined_predictions30)% math.floor(len(D_mono_input30)/32)) == 0: #
    epoch_count = epoch_count + 1
    #print(epoch_count)
    #print(sum(loss_combined)/len(loss_combined))
    model.load_weights('/content/drive/MyDrive/SKKU_JSNS^2/GNNs/model2_weights/model2_weights')

for i in range(len(combined_predictions30)):  #
  a = np.array(combined_predictions30[i]).reshape(32) #
  for j in range(32):
    final_predictions30[(32*i) + j] = a[j] #

D_pred30 = pd.DataFrame(final_predictions30) #

DF_graphs_test_y30 = pd.DataFrame(np.zeros(n_graphs30)) #

for i in range(len(DF_graphs_test_y30)): #
  DF_graphs_test_y30[0][i] = data_test30[i].y[0] #

"""40 MeV:"""

#Lines with hashtags need change of variables:

model.load_weights('/content/drive/MyDrive/SKKU_JSNS^2/GNNs/model2_weights/model2_weights')
combined_predictions40 = [] ##
loss_combined40 = [] #
epoch_count = 0
for batch in loader_test40: #
  loss, prediction = train_step(*batch) 
  combined_predictions40.append(prediction) #
  loss_combined40.append(loss) #
  if (len(combined_predictions40)% math.floor(len(D_mono_input40)/32)) == 0: #
    epoch_count = epoch_count + 1
    #print(epoch_count)
    #print(sum(loss_combined)/len(loss_combined))
    model.load_weights('/content/drive/MyDrive/SKKU_JSNS^2/GNNs/model2_weights/model2_weights')

for i in range(len(combined_predictions40)):  #
  a = np.array(combined_predictions40[i]).reshape(32) #
  for j in range(32):
    final_predictions40[(32*i) + j] = a[j] #

D_pred40 = pd.DataFrame(final_predictions40) #

DF_graphs_test_y40 = pd.DataFrame(np.zeros(n_graphs40)) #

for i in range(len(DF_graphs_test_y40)): #
  DF_graphs_test_y40[0][i] = data_test40[i].y[0] #

"""# Saving predictions:"""

np.save('/content/drive/MyDrive/SKKU_JSNS^2/Mono_energetic_predictions/GNNs/1MeV', final_predictions1)
np.save('/content/drive/MyDrive/SKKU_JSNS^2/Mono_energetic_predictions/GNNs/5MeV', final_predictions5)
np.save('/content/drive/MyDrive/SKKU_JSNS^2/Mono_energetic_predictions/GNNs/8MeV', final_predictions8)
np.save('/content/drive/MyDrive/SKKU_JSNS^2/Mono_energetic_predictions/GNNs/10MeV', final_predictions10)
np.save('/content/drive/MyDrive/SKKU_JSNS^2/Mono_energetic_predictions/GNNs/20MeV', final_predictions20)
np.save('/content/drive/MyDrive/SKKU_JSNS^2/Mono_energetic_predictions/GNNs/30MeV', final_predictions30)
np.save('/content/drive/MyDrive/SKKU_JSNS^2/Mono_energetic_predictions/GNNs/40MeV', final_predictions40)