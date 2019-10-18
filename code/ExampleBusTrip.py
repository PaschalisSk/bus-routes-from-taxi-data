from itertools import islice
from pathlib import Path
import matplotlib
matplotlib.rcParams['text.usetex'] = True
matplotlib.rcParams['font.family'] = 'serif'
import matplotlib.pyplot as plt
import matplotlib.colors
import OSMParser
import numpy as np
import networkx as nx
import xml.etree.ElementTree as ET
import pandas as pd

# Path to local data
local_data_folder = Path('../data/')
# Choose which dataset to work with
dataset = 'full'
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
# Read the trips
trips_csv = local_data_folder / 'sample_relocated_trips.csv'
trips_df = pd.read_csv(trips_csv)

# File to save the csv output
example_trip_output_file = dataset_folder / 'example_trip.csv'
# File to save the plot
example_trip_graph_output_file = dataset_folder / 'example_trip.eps'

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

# Initialise our random state
r_state = np.random.RandomState(12345)
# Get random row, set as weights the manhattan_distance in order to get a
# larger trip
row = trips_df.sample(n=1, random_state=r_state, weights='manhattan_distance')
row = row.reset_index(drop=True).iloc[0]

# Calculate trip distance
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
row['bus_duration'] = total_duration
row['buses'] = buses_used
row['unique_buses'] = len(unique_buses)
row['bus_ride_distance'] = bus_ride_distance
row['walking_distance'] = walking_distance

row_df = pd.DataFrame(row).transpose()
row_df = row_df.astype(np.int64)
row_df.to_csv(example_trip_output_file, index=False)


# Create a dictionary(pos) which has the node id as keys and
# values equal to (lon, lat) of the node, will be used for plotting
lons = nx.get_node_attributes(G, 'lon')
lats = nx.get_node_attributes(G, 'lat')
ds = [lons, lats]
pos = {}
for k, v in lons.items():
    pos[k] = tuple(pos[k] for pos in ds)

fig, ax = plt.subplots()
# Get map bounds to bound plot
# Parse the XML tree
tree = ET.parse(osm_file)
root = tree.getroot()
bounds = root.find('bounds').attrib

# Convert each coordinate str value in bounds to float
for k, v in bounds.items():
    bounds[k] = float(v)
# Set the bound of our graph and an equal ratio
ax.set_xlim([bounds['minlon'], bounds['maxlon']])
ax.set_ylim([bounds['minlat'], bounds['maxlat']])
ax.set_aspect('equal')
# Set the labels
ax.xaxis.set_label_text('longitude')
ax.yaxis.set_label_text('latitude')

# Draw the underlying map
map_lc = nx.draw_networkx_edges(G, pos, ax=ax,
                                edge_color='#d4d2d1', width=1.2)

# Group routes by bus_id
grouped_routes = bus_routes_df.groupby('bus_id')
#https://stackoverflow.com/questions/8389636/creating-over-20-unique-legend-colors-using-matplotlib
# Add one because we want different color for walking
n_routes = len(grouped_routes) + 1
cm = plt.get_cmap('gist_rainbow')
# Create the color list for each route
colors_list = [cm(1.*i/n_routes) for i in range(n_routes)]
# flags for the labels in order to show only 2
bus_label_flag = True
walking_label_flag = True
for u, v in zip(path, path[1:]):
    edge_data = G.get_edge_data(u, v)
    edge_subgraph = G.subgraph([u, v])
    style = 'solid'
    label = None
    if not('bus_id' in edge_data):
        # 0 to n_routes-2 are the indices for the color for bus routes
        # we use n_routes as the color for walking
        color = matplotlib.colors.rgb2hex(colors_list[n_routes-1][:3])
        style = 'dotted'
        if walking_label_flag:
            label = 'Walk'
            walking_label_flag = False
        edge_lc = nx.draw_networkx_edges(edge_subgraph, pos,
                                         ax=ax, edge_color=color, width=1.2,
                                         style=style, label=label)
    else:
        bus_id = edge_data['bus_id']
        color = matplotlib.colors.rgb2hex(colors_list[bus_id][:3])
        stop_label = None
        if bus_label_flag:
            label = 'Bus'
            stop_label = 'Bus stop'
            bus_label_flag = False
        # Also draw the bus stops
        stop_lons = [G.node[u]['lon'], G.node[v]['lon']]
        stop_lats = [G.node[u]['lat'], G.node[v]['lat']]
        # Draw the edge, plot here so that it appears before the stops
        # in legend
        edge_lc = nx.draw_networkx_edges(edge_subgraph, pos,
                                         ax=ax, edge_color=color, width=1.2,
                                         style=style, label=label, zorder=10)
        stops_scatter = ax.scatter(stop_lons, stop_lats, color=color, s=10,
                                   label=stop_label)

leg = ax.legend(loc=2)
# Change the color to something neutral
idx = 0
for leg_text in leg.get_texts():
    if leg_text._text == 'Bus' or leg_text._text == 'Bus stop':
        leg.legendHandles[idx].set_color('#000000')
    idx += 1

fig.savefig(example_trip_graph_output_file, bbox_inches='tight')
fig.show()
