from pathlib import Path

import matplotlib

matplotlib.rcParams['text.usetex'] = True
matplotlib.rcParams['font.family'] = 'serif'
import matplotlib.pyplot as plt
import math
import pandas as pd
import numpy as np

# Path to local data
local_data_folder = Path('../data/')
# Choose which dataset to work with
dataset = 'full'
dataset_folder = local_data_folder / dataset

# Read the results
trips_csv = dataset_folder / 'sample_relocated_trips_with_bus.csv'
trips_df = pd.read_csv(trips_csv)
# Find the percentage of the distance that was walked or by bus
trips_df['bus_ride_distance_perc'] = trips_df['bus_ride_distance'] / (
        trips_df['bus_ride_distance'] + trips_df['walking_distance'])
trips_df['walking_distance_perc'] = trips_df['walking_distance'] / (
        trips_df['bus_ride_distance'] + trips_df['walking_distance'])

# File to save the plot of taxi/buses-distance/time
taxi_vs_bus_plot_file = dataset_folder / 'taxi_vs_bus.eps'
# File to save stats for bins
results_file = dataset_folder / 'final_results.csv'

# Create the bins df for our results
# The upper bound is the upper thousand
upper_bound = int(
    math.ceil(trips_df['manhattan_distance'].max() / 1000.0)) * 1000
bins = np.linspace(0, upper_bound, 6).astype(int)
trips_bins = pd.cut(trips_df['manhattan_distance'], bins=bins)
trips_grouped_temp = trips_df.groupby(trips_bins)
trips_grouped = trips_grouped_temp.mean()
trips_grouped['count'] = trips_grouped_temp.size()
# Get the percentage performance of the bus
# We don't do that before because we get inf error
trips_grouped['taxi_to_bus_duration'] = trips_grouped['taxi_duration'] / trips_grouped[
    'bus_duration']
trips_grouped.to_csv(results_file, index_label='manhattan_distance_bins',
                     columns=['manhattan_distance', 'taxi_duration',
                              'bus_duration', 'taxi_to_bus_duration', 'buses',
                              'unique_buses',
                              'bus_ride_distance', 'walking_distance',
                              'bus_ride_distance_perc',
                              'walking_distance_perc',
                              'count'],
                     float_format='%.2f')
# Get row with means without bins
totals_s = trips_df.mean().rename('total')
totals_s['count'] = trips_df.shape[0]
totals_df = pd.DataFrame(totals_s).transpose()
totals_df['count'] = totals_df['count'].astype(int)
# Get the percentage performance of the bus
# We don't do that before because we get inf error
totals_df['taxi_to_bus_duration'] = totals_df['taxi_duration'] / totals_df[
    'bus_duration']
totals_df.to_csv(results_file, header=None, mode='a',
                 columns=['manhattan_distance', 'taxi_duration',
                          'bus_duration', 'taxi_to_bus_duration', 'buses',
                          'unique_buses',
                          'bus_ride_distance', 'walking_distance',
                          'bus_ride_distance_perc',
                          'walking_distance_perc',
                          'count'],
                 float_format='%.2f')
print('test')

# Create scatter plot of distance-time
fig, ax = plt.subplots()
bus_scatter = ax.scatter(x=trips_df['manhattan_distance'],
                         y=trips_df['bus_duration'], label='bus',
                         s=5, alpha=0.3)
taxi_scatter = ax.scatter(x=trips_df['manhattan_distance'],
                          y=trips_df['taxi_duration'], label='taxi',
                          s=5, alpha=0.3)
ax.legend()
ax.xaxis.set_label_text('trip Manhattan distance (m)')
ax.yaxis.set_label_text('trip duration (s)')
fig.show()
fig.savefig(taxi_vs_bus_plot_file, bbox_inches='tight')
