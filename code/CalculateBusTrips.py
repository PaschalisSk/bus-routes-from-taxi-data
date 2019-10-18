from itertools import islice
from pathlib import Path
import matplotlib.pyplot as plt
import matplotlib.colors
import OSMParser
import networkx as nx
import pandas as pd

# Path to local data
local_data_folder = Path('../data/')
# Choose which dataset to work with
dataset = 'sample'
dataset_folder = local_data_folder / dataset

osm_file = local_data_folder / 'map.osm'
# Read the OSM as a directed graph
G = OSMParser.read_osm(str(osm_file))
# We convert to undirected graph because a bus stop may have been placed in
# a dead end.
G = G.to_undirected()
# We get the giant component because our graph has many components
# so we may not be able to get from some point A to point B
G = max(nx.connected_component_subgraphs(G), key=len)

# Average walking speed 1.2m/s
# https://journals.sagepub.com/doi/pdf/10.1177/0361198106198200104
# Add the duration to travel each edge
for u, v, d in G.edges(data=True):
    d['duration'] = d['length'] / 1.2

# Read the bus routes
bus_routes_csv = dataset_folder / 'bus_routes.csv'
bus_routes_df = pd.read_csv(bus_routes_csv)
# Read the bus stops
bus_stops_csv = dataset_folder / 'bus_stops_relocated_with_buses.csv'
bus_stops_df = pd.read_csv(bus_stops_csv)
# Read the trips, relocating them all would take much time so we test with
# the sample trips
trips_csv = local_data_folder / 'sample_relocated_trips.csv'
trips_df = pd.read_csv(trips_csv)

# File to save the output
trips_w_bus = dataset_folder / 'sample_relocated_trips_with_bus.csv'

# The following loop adds edges between bus stops with the appropriate weights
grouped_routes = bus_routes_df.groupby('bus_id')
for bus_id, group in grouped_routes:
    # The current_bus_stops are the stops of the bus_id but unordered
    current_bus_stops = bus_stops_df.loc[bus_stops_df['bus_id'] == bus_id]
    current_bus_stops_nodes = list(map(str, current_bus_stops['node_id']))
    # Save the starting stop
    initial_bus_stop_node = str(group.iloc[0]['route_nodes'])

    # Create a list of all the unvisited stops so far
    unvisited_bus_stops = current_bus_stops_nodes
    unvisited_bus_stops.remove(initial_bus_stop_node)

    # Calculate the length and duration between 2 bus stops
    # and add an edge between those 2 nodes in our graph G
    length_btw_stops = 0
    previous_bus_stop = initial_bus_stop_node
    previous_node = initial_bus_stop_node
    # Iterate over all the nodes in the route but not the first
    for idx, row in islice(group.iterrows(), 1, None):
        current_node = str(row['route_nodes'])
        length_btw_stops += G.edge[previous_node][current_node]['length']
        if current_node in unvisited_bus_stops:
            # Average Manhattan bus speed 2.5m/s
            duration = length_btw_stops / 2.5
            G.add_edge(previous_bus_stop, current_node,
                       {'length': length_btw_stops, 'duration': duration,
                        'bus_id': bus_id})
            length_btw_stops = 0
            unvisited_bus_stops.remove(current_node)
            if len(unvisited_bus_stops) == 0:
                unvisited_bus_stops.append(initial_bus_stop_node)
            previous_bus_stop = current_node
        previous_node = current_node
# Now our graph G has edges from one bus stop to the other with the
# related length and duration as attributes

# Calculate trip distances
for idx, row in trips_df.iterrows():
    pickup_node = str(row['pickup_node'])
    dropoff_node = str(row['dropoff_node'])
    path = nx.dijkstra_path(G, source=pickup_node,
                                 target=dropoff_node,
                                 weight='duration')
    total_duration = 0
    walking_distance = 0
    bus_ride_distance = 0
    buses_used = 0
    unique_buses = []
    # Save previous method of transportation
    walking_flag = True
    for u, v in zip(path, path[1:]):
        edge_data = G.get_edge_data(u, v)
        total_duration += edge_data['duration']
        if 'bus_id' in edge_data:
            bus_ride_distance += edge_data['length']
        else:
            walking_distance += edge_data['length']
        if 'bus_id' in edge_data and walking_flag:
            buses_used += 1
            walking_flag = False
            bus_id = edge_data['bus_id']
            if not(bus_id in unique_buses):
                unique_buses.append(bus_id)
        if not('bus_id' in edge_data) and not(walking_flag):
            walking_flag = True
    trips_df.at[idx, 'bus_duration'] = total_duration
    trips_df.at[idx, 'buses'] = buses_used
    trips_df.at[idx, 'unique_buses'] = len(unique_buses)
    trips_df.at[idx, 'bus_ride_distance'] = bus_ride_distance
    trips_df.at[idx, 'walking_distance'] = walking_distance

trips_df['bus_duration'] = trips_df['bus_duration'].astype(int)
trips_df['buses'] = trips_df['buses'].astype(int)
trips_df['unique_buses'] = trips_df['unique_buses'].astype(int)
trips_df['bus_ride_distance'] = trips_df['bus_ride_distance'].astype(int)
trips_df['walking_distance'] = trips_df['walking_distance'].astype(int)
trips_df.to_csv(trips_w_bus, index=False)
