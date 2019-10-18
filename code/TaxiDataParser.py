import csv
import os
import glob
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path

# Boolean to define if we want to parse a maximum number of trips
MAX_TRIPS_FILTER = False
MAX_TRIPS = 10
# Boolean to define if we want to parse trips for specific dates
DATE_FILTER = True
MIN_DATE = datetime.strptime('01-11-2013', '%d-%m-%Y')
MAX_DATE = datetime.strptime('07-11-2013', '%d-%m-%Y')

# Path to the folder which contains the FOIL trips .csv
trips_data_folder = Path('D:/FOIL2013')
# Use the line below if we want to parse all the trips
#trips_pathname = str(trips_data_folder / '*.csv')
# Since there is 1 csv file for each month and we want to process the
# first week of November, we can look only at trip_data_11.csv in order
# to avoid reading files 1-10. I didn't put the rest in DICE
# so they have to be downloaded from here
# https://databank.illinois.edu/datasets/IDB-9610843#
trips_pathname = str(trips_data_folder / 'trip_data_11.csv')

# Path to local data folder
local_data_folder = Path('../data/')
# Path to map file from which we read the borders
# The borders are the lon and lat min/max in which we are working
OSM_file = local_data_folder / 'map.osm'

# Parse the XML tree
tree = ET.parse(OSM_file)
root = tree.getroot()
bounds = root.find('bounds').attrib

# Convert each coordinate str value in bounds to float
for k, v in bounds.items():
    bounds[k] = float(v)

# Create an appropriate filename for output
output_filename = 'trips.'
if DATE_FILTER:
    output_filename += MIN_DATE.strftime('%d-%m-%Y') + '.'
    output_filename += MAX_DATE.strftime('%d-%m-%Y') + '.'
if MAX_TRIPS_FILTER:
    output_filename += str(MAX_TRIPS) + '.'
output_filename += 'csv'
output_file = local_data_folder / output_filename

with open(output_file, 'w', newline='') as outputCSV:
    # Set the headers for our output
    fieldnames = ['pickup_datetime', 'dropoff_datetime',
                  'pickup_longitude', 'pickup_latitude',
                  'dropoff_longitude', 'dropoff_latitude']
    writer = csv.DictWriter(outputCSV, fieldnames=fieldnames)
    writer.writeheader()
    # Counter in case we have MAX_TRIPS_FILTER to True
    trips_counter = 0

    # For each file in our path
    for inputFile in glob.glob(trips_pathname):
        # Exit if we have read the MAX_TRIPS
        if MAX_TRIPS_FILTER and trips_counter == MAX_TRIPS:
            break
        print('Reading file ' + inputFile)
        with open(inputFile, newline='') as inputCSV:
            reader = csv.DictReader(inputCSV, skipinitialspace=True)
            for row in reader:
                # Stop reading if we have read the MAX_TRIPS
                if MAX_TRIPS_FILTER and trips_counter == MAX_TRIPS:
                    break
                try:
                    pick_lon = float(row['pickup_longitude'])
                    pick_lat = float(row['pickup_latitude'])
                    drop_lon = float(row['dropoff_longitude'])
                    drop_lat = float(row['dropoff_latitude'])
                    # Check the dates if we have enabled the filter
                    if DATE_FILTER:
                        # Get the pickup and dropoff dates
                        pick_date_str = row['pickup_datetime'].split(' ')[0]
                        pick_date = datetime.strptime(pick_date_str,
                                                      '%Y-%m-%d')
                        drop_date_str = row['dropoff_datetime'].split(' ')[0]
                        drop_date = datetime.strptime(drop_date_str,
                                                      '%Y-%m-%d')
                        # The trips are ordered by pick_date so if we have
                        # surpassed the max then stop
                        if pick_date > MAX_DATE:
                            break
                        # If we are outside our window then continue
                        if pick_date < MIN_DATE or pick_date > MAX_DATE \
                                or drop_date < MIN_DATE or drop_date > MAX_DATE:
                            continue
                    # Check if we are inside the boundaries of our map but
                    # also check if the pick location is different than the
                    # drop location since some of the input is wrong(same loc)
                    if bounds['minlon'] <= pick_lon <= bounds['maxlon'] and \
                        bounds['minlat'] <= pick_lat <= bounds['maxlat'] and \
                        bounds['minlon'] <= drop_lon <= bounds['maxlon'] and \
                        bounds['minlat'] <= drop_lat <= bounds['maxlat'] and \
                            (pick_lon != drop_lon or pick_lat != drop_lat):

                        # If all of the above are true then print the trip
                        writer.writerow({
                            'pickup_datetime': row['pickup_datetime'],
                            'dropoff_datetime': row['dropoff_datetime'],
                            'pickup_longitude': row['pickup_longitude'],
                            'pickup_latitude': row['pickup_latitude'],
                            'dropoff_longitude': row['dropoff_longitude'],
                            'dropoff_latitude': row['dropoff_latitude']
                        })
                        trips_counter += 1
                except ValueError as e:
                    print('Line with invalid location or time detected.')
                    print(e)
