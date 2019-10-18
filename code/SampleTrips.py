from pathlib import Path

import numpy as np
import pandas as pd

# Path to local data folder
local_data_folder = Path('../data/')
input_file = local_data_folder / 'trips.01-11-2013.07-11-2013.full.csv'
output_file = local_data_folder / 'trips.01-11-2013.07-11-2013.sample.csv'

full_df = pd.read_csv(input_file,
                      parse_dates=['pickup_datetime', 'dropoff_datetime'],
                      dtype={'pickup_longitude': np.float32,
                             'pickup_latitude': np.float32,
                             'dropoff_longitude': np.float32,
                             'dropoff_latitude': np.float32})

# Initialise our random state
r_state = np.random.RandomState(1234)
full_df.sample(n=1000, random_state=r_state).to_csv(output_file, index=False)
