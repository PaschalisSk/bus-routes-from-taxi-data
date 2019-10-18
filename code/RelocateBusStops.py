from pathlib import Path
import matplotlib
import matplotlib.pyplot as plt
import numpy as np
import networkx as nx
import pandas as pd
from scipy.spatial import distance
import OSMParser

matplotlib.rcParams['text.usetex'] = True
matplotlib.rcParams['font.family'] = 'serif'

# Path to local data
local_data_folder = Path('../data/')
osm_file = local_data_folder / 'map.osm'

# Choose which dataset to work with
dataset = 'sample'
dataset_folder = local_data_folder / dataset
# File which contains the bus stops found in ClusterEndpoints.py
bus_stops_file = dataset_folder / 'bus_stops.csv'
# Relocated bus stops file
bus_stops_relocated_output = dataset_folder / 'bus_stops_relocated.csv'

# Read the OSM as a directed graph
G = OSMParser.read_osm(str(osm_file))
# We convert to undirected graph because a bus stop may have been placed in
# a dead end.
G = G.to_undirected()
# We get the giant component because our graph has many components
# so we may not be able to get from some point A to point B
G = max(nx.connected_component_subgraphs(G), key=len)

# Create a dictionary(pos) which has the node id as keys and
# values equal to (lon, lat) of the node
lons = nx.get_node_attributes(G, 'lon')
lats = nx.get_node_attributes(G, 'lat')
ds = [lons, lats]
pos = {}
for k, v in lons.items():
    pos[k] = tuple(pos[k] for pos in ds)

# Read the bus stops
bus_stops_df = pd.read_csv(bus_stops_file,
                           dtype={'stop_label': int,
                                  'longitude': np.float64,
                                  'latitude': np.float64})

# Add empty column to save the node id
bus_stops_df['node_id'] = np.nan

for idx, row in bus_stops_df.iterrows():
    # Get the lon, lat of each row and find the closest graph node
    stop_lon = row['longitude']
    stop_lat = row['latitude']
    # We are talking only about Manhattan, taking the euclidean with the
    # coordinates doesn't affect the result
    closest_node = min(pos.items(),
                  key=lambda node: distance.euclidean((node[1][0], node[1][1]),
                                                      (stop_lon, stop_lat)))
    # Reposition the bus stop and add the node id
    bus_stops_df.loc[idx, 'longitude'] = closest_node[1][0]
    bus_stops_df.loc[idx, 'latitude'] = closest_node[1][1]
    bus_stops_df.loc[idx, 'node_id'] = closest_node[0]

# Save the repositioned bus stops to file
bus_stops_df.to_csv(bus_stops_relocated_output, index=False)
