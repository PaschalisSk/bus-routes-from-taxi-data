from pathlib import Path

import matplotlib
import pandas as pd

matplotlib.rcParams['text.usetex'] = True
matplotlib.rcParams['font.family'] = 'serif'
import matplotlib.pyplot as plt
import numpy as np
from sklearn import cluster
import OSMParser

# Path to local data folder
local_data_folder = Path('../data/')
# Choose which dataset to work with
dataset = 'sample'
# The trips file which we will process
trips_file = local_data_folder / (
            'trips.01-11-2013.07-11-2013.' + dataset + '.csv')
dataset_folder = local_data_folder / dataset
# File to save bus stop locations
bus_stops_output_file = dataset_folder / 'bus_stops.csv'
# File to save map plot
map_plot_output_file = dataset_folder / 'trips_and_stops_map.eps'
# File to the 90th percentile distance for n number of buses
n_stops_p_output_file = dataset_folder / 'n_stops_90th_perc.csv'

# Read the trips
csv_data = pd.read_csv(trips_file,
                       usecols=['pickup_datetime', 'dropoff_datetime',
                                'pickup_longitude', 'pickup_latitude',
                                'dropoff_longitude', 'dropoff_latitude'],
                       parse_dates=['pickup_datetime', 'dropoff_datetime'],
                       dtype={'pickup_longitude': np.float32,
                              'pickup_latitude': np.float32,
                              'dropoff_longitude': np.float32,
                              'dropoff_latitude': np.float32})

# Create new dataframe with the pickup locations
pickup = csv_data[['pickup_longitude', 'pickup_latitude']]
pickup.columns = ['longitude', 'latitude']

# Create dataframe with dropoff locations
dropoff = csv_data[['dropoff_longitude', 'dropoff_latitude']]
dropoff.columns = ['longitude', 'latitude']

# Combine the two dataframes(pickup and dropoff) to get a dataframe of all
# the endpoints
endpoints = pickup.append(dropoff).reset_index(drop=True)

map_fig, map_ax = plt.subplots()

# List of the bins for our hexbin
bins = [1, 3, 8, 21, 55, 144, 233, 377, 610, 984]

hb = map_ax.hexbin(endpoints['longitude'].values, endpoints['latitude'].values,
                   gridsize=600, cmap='jet', mincnt=1, bins=bins)

# Set the aspect of the axes to be equal so that we have no distortion
# and the output resembles manhattan
map_ax.set_aspect('equal')
# Set the labels
map_ax.xaxis.set_label_text('longitude')
map_ax.yaxis.set_label_text('latitude')

# Create the colorbar
N = len(bins)
cbar = map_fig.colorbar(hb, ax=map_ax, ticks=range(N))
cbar.ax.set_yticklabels(bins)
cbar.ax.set_ylabel('Counts', rotation=270, labelpad=10)

# Initialise our random state
r_state = np.random.RandomState(1234)

# Start with 40 clusters and increase by 5 until the 90th percentile
# Manhattan distance to walk is less than 400m
n_clusters = 40
# Dataframe to hold the average walking distance for each n_clusters
clusters_dist = pd.DataFrame(columns=['n_clusters', '90perc_mnh_dist'])
clusters_df_idx = 0
# Initialise variable to hold the output of KMeans
centroids = None
# Initialise variable to hold Manhattan distances from stops to endpoints
manh_dist = np.empty(len(endpoints))

while True:
    # Fit KMeans
    K_means = cluster.KMeans(n_clusters=n_clusters, init='k-means++', n_init=4,
                             random_state=r_state, n_jobs=-1)
    centroids = K_means.fit(endpoints.values)

    # Store the Manhattan distance from the endpoints
    # to the bus stops
    for idx, row in endpoints.iterrows():
        label = centroids.labels_[idx]
        centroid = centroids.cluster_centers_[label]
        c_lon = centroid[0]
        c_lat = centroid[1]
        r_lon = row['longitude']
        r_lat = row['latitude']
        # Calculate the distance in metres using the haversine formula
        # https://en.wikipedia.org/wiki/Haversine_formula
        d_lon = OSMParser.haversine(c_lon, c_lat, r_lon, c_lat)
        d_lat = OSMParser.haversine(c_lon, c_lat, c_lon, r_lat)
        manh_dist[idx] = d_lon + d_lat

    nnth_percentile = np.percentile(manh_dist, 90)
    clusters_dist.loc[clusters_df_idx] = [n_clusters, nnth_percentile]
    # If the 90th percentile Manhattan distance is less than 400m stop,
    # otherwise increase our clusters by 5
    if np.percentile(nnth_percentile, 90) < 400:
        break
    else:
        n_clusters += 5
        clusters_df_idx += 1

# Create labels for our clusters(bus stops) and save their locations
cluster_labels = np.arange(n_clusters)[:, np.newaxis]
np.savetxt(bus_stops_output_file,
           np.column_stack((cluster_labels, centroids.cluster_centers_)),
           comments='', header='stop_label,longitude,latitude', fmt='%i,%f,%f')

# Draw the bus stops in the map
sp = map_ax.scatter(centroids.cluster_centers_[:, 0],
                    centroids.cluster_centers_[:, 1],
                    color='#ff4747', s=10, label='Bus stops')
# Add legend to top left
map_ax.legend(loc=2, handletextpad=0.1)

map_fig.savefig(map_plot_output_file, bbox_inches='tight')
map_fig.tight_layout()
map_fig.show()

# Convert the number of clusters column to integer and print them
clusters_dist['n_clusters'] = pd.to_numeric(clusters_dist['n_clusters'],
                                            downcast='integer')
clusters_dist.to_csv(n_stops_p_output_file,
                     index=False, float_format='%.2f')
