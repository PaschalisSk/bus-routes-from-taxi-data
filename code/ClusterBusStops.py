from pathlib import Path
import matplotlib
import matplotlib.pyplot as plt
import numpy as np
import networkx as nx
import pandas as pd
from sklearn import cluster
from scipy.spatial import distance
import OSMParser

# Path to local data
local_data_folder = Path('../data/')
# Choose which dataset to work with
dataset = 'sample'
dataset_folder = local_data_folder / dataset
bus_stops = dataset_folder / 'bus_stops_relocated.csv'
# File to save bus stop locations
bus_stops_with_buses_output = dataset_folder / 'bus_stops_relocated_with_buses.csv'

bus_stops_df = pd.read_csv(bus_stops,
                           dtype={'stop_label': int})

# Initialise our random state
r_seed = 1234
r_state = np.random.RandomState(r_seed)

# Define half of the number of buses. Since the buses will go in two directions
# if we have 5 clusters(i.e. this case) we need 10 buses.
n_clusters = 5
# Cluster
K_means = cluster.KMeans(n_clusters=n_clusters, init='k-means++', n_init=10,
                         random_state=r_state, n_jobs=-1)
centroids = K_means.fit(bus_stops_df[['longitude', 'latitude']])

# Add the labels to the dataframe
bus_stops_df['bus_id'] = centroids.labels_

# Save the bus stops
bus_stops_df.to_csv(bus_stops_with_buses_output,
                    columns=['stop_label', 'node_id', 'bus_id'], index=False)
