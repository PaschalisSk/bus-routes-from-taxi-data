from pathlib import Path
import matplotlib
matplotlib.rcParams['text.usetex'] = True
matplotlib.rcParams['font.family'] = 'serif'
import matplotlib.pyplot as plt
import matplotlib.colors
import numpy as np
import networkx as nx
import pandas as pd
from sklearn import cluster
from scipy.spatial import distance
from itertools import combinations
import xml.etree.ElementTree as ET
import OSMParser

# Path to local data
local_data_folder = Path('../data/')
# Choose which dataset to work with
dataset = 'full'
dataset_folder = local_data_folder / dataset
routes_graph_output = dataset_folder / 'bus_routes.eps'

osm_file = local_data_folder / 'map.osm'

# Parse the XML tree
tree = ET.parse(osm_file)
root = tree.getroot()
bounds = root.find('bounds').attrib

# Convert each coordinate str value in bounds to float
for k, v in bounds.items():
    bounds[k] = float(v)
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
bus_stops_df = pd.read_csv(bus_stops_csv)
# Read the bus routes
bus_routes_csv = dataset_folder / 'bus_routes.csv'
bus_routes_df = pd.read_csv(bus_routes_csv)

# Create a dictionary(pos) which has the node id as keys and
# values equal to (lon, lat) of the node, will be used for plotting
lons = nx.get_node_attributes(G, 'lon')
lats = nx.get_node_attributes(G, 'lat')
ds = [lons, lats]
pos = {}
for k, v in lons.items():
    pos[k] = tuple(pos[k] for pos in ds)

fig, ax = plt.subplots()
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

# Group routes by bus_id and plot each one
grouped_routes = bus_routes_df.groupby('bus_id')

#https://stackoverflow.com/questions/8389636/creating-over-20-unique-legend-colors-using-matplotlib
n_routes = len(grouped_routes)
cm = plt.get_cmap('gnuplot')
# Create the color list for each route
colors_list = [cm(1.*i/n_routes) for i in range(n_routes)]
for bus_id, group in grouped_routes:
    color = matplotlib.colors.rgb2hex(colors_list[bus_id][:3])
    # Create the subgraph for the route
    route_G = G.subgraph(map(str, group['route_nodes'].values))
    nx.draw_networkx_edges(route_G, pos, ax=ax, edge_color=color, width=1.2)
    # Get the bus plots and plot them as circles
    stops_nodes = bus_stops_df.loc[bus_stops_df['bus_id'] == bus_id, 'node_id']
    stops_pos = [pos[str(node)] for node in stops_nodes]
    stops_lons = [stop_pos[0] for stop_pos in stops_pos]
    stops_lats = [stop_pos[1] for stop_pos in stops_pos]
    # We want only one label in the legend so check if this is the first time
    label = None
    if bus_id == 0:
        label = 'Bus stops'
    stops_scatter = ax.scatter(stops_lons, stops_lats, color=color, s=10,
                               label=label)

# Add legend to top left
leg = ax.legend(loc=2, handletextpad=0.1)
# Change the color to something neutrial
leg.legendHandles[0].set_color('#000000')
fig.savefig(routes_graph_output, bbox_inches='tight')
fig.show()
