import OSMParser
import networkx as nx
import matplotlib.pyplot as plt


G = OSMParser.read_osm(OSMParser.download_osm(-74.0203, 40.6958, -73.9226, 40.8392))
lats = nx.get_node_attributes(G, 'lat')
lons = nx.get_node_attributes(G, 'lon')
ds = [lats, lons]
pos = {}
for k, v in lons.items():
    pos[k] = tuple(pos[k] for pos in ds)

plt.gca().invert_yaxis()
plt.gca().invert_xaxis()
edges = nx.draw_networkx_edges(G, pos)
plt.show()
print('deb')
