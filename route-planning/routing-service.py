import openrouteservice
from openrouteservice import optimization
from qgis.core import QgsApplication, QgsVectorLayer
from shapely.geometry import LineString
import geopandas as gpd
import os

# Set up QGIS environment
QgsApplication.setPrefixPath("C:/Program Files/QGIS 3.28.3", True)
qgs = QgsApplication([], False)
qgs.initQgis()

# API Key ORS
ors_api_key = "eyJvcmciOiI1YjNjZTM1OTc4NTExMTAwMDFjZjYyNDgiLCJpZCI6ImVkOWY3Y2Q2ZjVlNTRmODM5ODgwZjZkYmRlZmUyOGYxIiwiaCI6Im11cm11cjY0In0="
ors = openrouteservice.Client(key=ors_api_key)

# Load point layer
point = "D:/01. ANA/04. TB/01. Task 01/01. Data/point_input_ors.shp"
point_layer = QgsVectorLayer(point, "point_layer", "ogr")
if not point_layer.isValid():
    raise Exception("Failed to load point layer")

# Extract coordinates from point layer
point_coordinate = []
for feat in point_layer.getFeatures():
    geom = feat.geometry().asPoint()
    point_coordinate.append([geom.x(), geom.y()])

# Define jobs and vehicles for TSP
jobs = [optimization.Job(id=i + 1, location=coord) for i, coord in enumerate(point_coordinate)]
vehicles = [optimization.Vehicle(
    id=1,
    profile='driving-car',
    start=point_coordinate[0],
    end=point_coordinate[0]
)]

# Run TSP optimization
result = ors.optimization(jobs=jobs, vehicles=vehicles)
route_result = result['routes'][0]['steps']

# Get ordered coordinates from TSP result
ordered_coords = []
for step in route_result:
    if 'location' in step:
        ordered_coords.append(step['location'])

# Create LineStrings between ordered points
lines = []
for i in range(len(ordered_coords) - 1):
    start = ordered_coords[i]
    end = ordered_coords[i + 1]

    response = ors.directions(
        coordinates=[start, end],
        profile='driving-car',
        format='geojson',
        validate=False,
        instructions=True
    )

    if 'features' in response and response['features']:
        coords = response['features'][0]['geometry']['coordinates']
        segments = response['features'][0]['properties']['segments']
        total_distance = sum(seg['distance'] for seg in segments)
        #total_duration = sum(seg['duration'] for seg in segments)

        line = LineString(coords)
        lines.append({
            'geometry': line,
            'from_id': i,
            'to_id': i + 1,
            'distance_m': total_distance,
            #'duration_s': total_duration
        })
    else:
        print(f"Warning: No features returned for segment {i} -> {i+1}")

# Save to shapefile
output_path = "D:/01. ANA/04. TB/01. Task 01/routing-service/result/optimized_route.shp"
gdf = gpd.GeoDataFrame(lines, crs='EPSG:4326')
gdf.to_file(output_path)

print("Done")
qgs.exitQgis()
