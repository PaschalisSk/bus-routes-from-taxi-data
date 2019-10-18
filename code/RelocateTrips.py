import csv
from pathlib import Path

import OSMParser
import networkx as nx
import pandas as pd
import numpy as np
from scipy.spatial import distance

# Path to local data folder
local_data_folder = Path('../data/')

osm_file = local_data_folder / 'map.osm'
# We only relocate the sample, it would take a lot of time to relocate the
# full dataset. The relocated trips are only used to calculate bus trip
# duration in CalculateBusTrips.py
input_file = local_data_folder / 'trips.01-11-2013.07-11-2013.sample.csv'
output_file = local_data_folder / 'sample_relocated_trips.csv'

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

trips_df = pd.read_csv(input_file,
                       parse_dates=['pickup_datetime', 'dropoff_datetime'],
                       usecols=['pickup_datetime', 'dropoff_datetime',
                                'pickup_longitude', 'pickup_latitude',
                                'dropoff_longitude', 'dropoff_latitude'],
                       dtype={'pickup_longitude': np.float32,
                              'pickup_latitude': np.float32,
                              'dropoff_longitude': np.float32,
                              'dropoff_latitude': np.float32})

relocated_trips_df = pd.DataFrame(columns=['pickup_node', 'dropoff_node',
                                           'manhattan_distance',
                                           'taxi_duration'])

for idx, row in trips_df.iterrows():
    # We are talking only about Manhattan, taking the euclidean with the
    # coordinates doesn't affect the result
    pickup_node = min(pos.items(),
                      key=lambda node: distance.euclidean(
                          (node[1][0], node[1][1]),
                          (row['pickup_longitude'],
                           row['pickup_latitude'])
                      ))[0]
    dropoff_node = min(pos.items(),
                       key=lambda node: distance.euclidean(
                           (node[1][0], node[1][1]),
                           (row['dropoff_longitude'],
                            row['dropoff_latitude'])
                       ))[0]

    d_lon = OSMParser.haversine(row['pickup_longitude'],
                                row['pickup_latitude'],
                                row['dropoff_longitude'],
                                row['pickup_latitude'])
    d_lat = OSMParser.haversine(row['pickup_longitude'],
                                row['pickup_latitude'],
                                row['pickup_longitude'],
                                row['dropoff_latitude'])
    manhattan_distance = d_lon + d_lat

    trip_duration = row['dropoff_datetime'] - row['pickup_datetime']
    trip_duration = trip_duration.total_seconds()
    relocated_trips_df = relocated_trips_df.append({
                                'pickup_node': int(pickup_node),
                                'dropoff_node': int(dropoff_node),
                                'manhattan_distance': int(manhattan_distance),
                                'taxi_duration': int(trip_duration)
                            }, ignore_index=True)

relocated_trips_df.to_csv(output_file, index=False)
