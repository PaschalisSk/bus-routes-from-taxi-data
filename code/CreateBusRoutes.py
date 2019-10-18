from pathlib import Path
import matplotlib
import matplotlib.pyplot as plt
import numpy as np
import networkx as nx
import pandas as pd
from sklearn import cluster
from scipy.spatial import distance
from itertools import combinations
import OSMParser

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

# Read the bus stops
bus_stops_csv = dataset_folder / 'bus_stops_relocated_with_buses.csv'
all_stops_df = pd.read_csv(bus_stops_csv)
# File to save the routes
bus_routes_output_file = dataset_folder / 'bus_routes.csv'

# Get the number of buses
n_buses = len(all_stops_df.groupby(by='bus_id'))

# The final dataframe for our routes
routes_df = pd.DataFrame(columns=['bus_id', 'route_nodes'])

for bus in range(n_buses):
    stops_df = all_stops_df[all_stops_df['bus_id'] == bus].reset_index()
    # For all stops create 2d dataframe with shortest path lengths
    lengths_df = pd.DataFrame(columns=stops_df['node_id'],
                              index=stops_df['node_id'])
    # Create the lengths dataframe
    for start_node, end_node in combinations(stops_df['node_id'].values, 2):
        path_length = nx.dijkstra_path_length(G, source=str(start_node),
                                              target=str(end_node),
                                              weight='length')
        lengths_df.at[start_node, end_node] = path_length
        lengths_df.at[end_node, start_node] = path_length

    # Run the repetitive Nearest neighbour to solve the TSP
    min_route = None
    min_cost = 0
    # For every bus stop run the NN
    for initial_bus_stop in stops_df['node_id'].values:
        # Add all the bus stops to a list
        bus_stops = stops_df['node_id'].values.tolist()
        n_bus_stops = len(bus_stops)
        # Initialise our route
        route = [initial_bus_stop]
        current_bus_stop = initial_bus_stop
        # Save the unvisited stops in a list
        unvisited_bus_stops = bus_stops
        unvisited_bus_stops.remove(initial_bus_stop)

        total_cost = 0
        # For each stop go to the nearest neighbour
        for i in range(n_bus_stops - 1):
            next_bus_stop = unvisited_bus_stops[0]
            min_distance = lengths_df.at[current_bus_stop, next_bus_stop]
            for bus_stop in unvisited_bus_stops:
                if lengths_df.at[current_bus_stop, bus_stop] < min_distance:
                    next_bus_stop = bus_stop
                    min_distance = lengths_df.at[current_bus_stop, bus_stop]
            route.append(next_bus_stop)
            unvisited_bus_stops.remove(next_bus_stop)
            current_bus_stop = next_bus_stop
            total_cost += min_distance

        # Add our initial stop to close the circuit
        route.append(initial_bus_stop)
        total_cost += lengths_df.at[current_bus_stop, initial_bus_stop]
        # Save the route if it is the best found so far
        if min_route is None or total_cost < min_cost:
            min_route = route
            min_cost = total_cost

    # Determine the shortest paths for each bus_stop in our min_route
    # We previously just saved the cost.
    for start_node, end_node in zip(min_route, min_route[1:]):
        shortest_path = nx.dijkstra_path(G, source=str(start_node),
                                         target=str(end_node),
                                         weight='length')

        shortest_path_array = np.array(shortest_path)
        bus_id_array = np.full(len(shortest_path), bus)
        route_part_df = pd.DataFrame({'bus_id': bus_id_array,
                                      'route_nodes': shortest_path_array})
        # If this is not the first intermediate route between stops
        # don't save the starting point because it's the ending point
        # of the previous route and we end up with duplicates
        if len(routes_df[routes_df['bus_id']==bus]) != 0:
            route_part_df = route_part_df.iloc[1:]
        routes_df = routes_df.append(route_part_df).reset_index(drop=True)

# Save the buses' routes to file
routes_df.to_csv(bus_routes_output_file, index=False)
