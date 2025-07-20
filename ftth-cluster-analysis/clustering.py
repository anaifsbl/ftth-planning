import geopandas as gpd
import numpy as np
from k_means_constrained import KMeansConstrained

# loading shapefile of house centroid points
house_loc = "D:/01. ANA/04. TB/02. Task 02/01. Data/point_rumah_kota_serang_sampling.shp"
house = gpd.read_file(house_loc)

# getting coordinates from house point layer
coords = np.array([[point.x, point.y] for point in house.geometry])

# constrained k-means clustering
n_clusters = 75
min_member = 200
max_member = 1000
constrained_kmeans = KMeansConstrained(
    n_clusters = n_clusters,
    size_min = min_member,
    size_max = max_member,
    random_state = 42,
    n_init = 3,
    max_iter = 75,
    verbose = True
)
house['cluster_label'] = constrained_kmeans.fit_predict(coords)
print(house['cluster_label'].value_counts())
output_path = "D:/01. ANA/04. TB/02. Task 02/area-criteria/result/clustered_house.shp"
house.to_file(output_path)