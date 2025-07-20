import sys
import os
from qgis.core import (
    QgsApplication,
    QgsVectorLayer,
    QgsRasterLayer,
    QgsProject
)

# initialize qgis library
QgsApplication.setPrefixPath("C:/Program Files/QGIS 3.28.3/bin/python-qgis.bat", True)
qgs = QgsApplication([], False)
qgs.initQgis()

# Manual load processing module
sys.path.append('C:/Program Files/QGIS 3.28.3/apps/qgis/python/plugins')
import processing
from processing.core.Processing import Processing
Processing.initialize()

print ("qgis library initiated")

# load clustered points
base_path = "D:/01. ANA/04. TB/02. Task 02/area-criteria/result/clustered_house.shp"
save_base = "D:/01. ANA/04. TB/02. Task 02/area-criteria/result-script/"

clustered_house_lyr = QgsVectorLayer(base_path, "clustered_house", "ogr")
if not clustered_house_lyr.isValid():
    raise Exception("failed to load clustered house points")

# reproject into utm 48s
cluster_house_utm_path = f"{save_base}clustered_house_utm.shp"
clustered_house_utm_layer = processing.run("native:reprojectlayer", {
    'INPUT' : clustered_house_lyr,
    'TARGET_CRS' : 'EPSG:32748',
    'OUTPUT' : cluster_house_utm_path
})
clustered_house_layer = QgsVectorLayer(cluster_house_utm_path, "clustered_house_utm_layer", "ogr")

# generating grid using minimum bounding geometry
grid_path = f"{save_base}01_grid_cluster.shp"
grid = processing.run("qgis:minimumboundinggeometry", {
    'INPUT' : clustered_house_layer,
    'FIELD' : 'cluster_la',
    'TYPE' : 3, # convex hull
    'OUTPUT' : grid_path
})
print("grid is generated!")
grid_layer = QgsVectorLayer(grid_path, "grid_layer", "ogr")

# def intersect and dissolve
def intersect_dissolve_repro(input_layer_path, intersect_layer, output_path):
    input_layer = QgsVectorLayer(input_layer_path, "input_intersect", "ogr")
    intersect_layer  = grid_layer
    if not input_layer.isValid() or not intersect_layer.isValid():
        raise Exception("input layer or intersect layer failed to load")
    
    # intersect
    intersect_result = processing.run("native:intersection", {
        'INPUT' : input_layer,
        'OVERLAY' : intersect_layer,
        'INPUT_FIELDS' : ['OBJECTID'],
        'OVERLAY_FIELDS' : ['cluster_la'],
        'OUTPUT' :'TEMPORARY_OUTPUT'
    }) ['OUTPUT']

    # dissolve based on cluster_la
    dissolve_result = processing.run("native:dissolve", {
        'INPUT' : intersect_result,
        'FIELD' : ['cluster_la'],
        'OUTPUT' : 'TEMPORARY_OUTPUT'
    }) ['OUTPUT']
    print(f"intersect and dissolve is done and generated at: {output_path}")

    # reproject layer to utm
    utm_result = processing.run("native:reprojectlayer", {
        'INPUT' : dissolve_result,
        'TARGET_CRS': 'EPSG:32748',
        'OUTPUT' : output_path
    }) ['OUTPUT']
    print(f"intersect_dissolve_repro function for {input_layer_path} is done")


# PARAMETER 1 : ROAD
# calculating road length per grid
print("processing road as parameter")
road_grid_path = f"{save_base}02_int_dis_road_per_grid.shp"
intersect_dissolve_repro(
    input_layer_path = "D:/01. ANA/04. TB/02. Task 02/01. Data/line_jalan_kota_serang.shp",
    intersect_layer = grid_layer,
    output_path = road_grid_path,
)
road_grid_layer = QgsVectorLayer(road_grid_path, "int_dis_road_per_grid", "ogr")
if not road_grid_layer.isValid():
    raise Exception("Failed to load road_grid_layer")
road_length_path = f"{save_base}03_road_length.shp"
road_length = processing.run("qgis:fieldcalculator", {
    'INPUT' : road_grid_layer,
    'FIELD_NAME' : 'length_road',
    'FIELD_TYPE' : 2, # decimal number
    'FIELD_LENGTH' : 20,
    'FIELD_PRECISION': 3,
    'FORMULA' : 'length($geometry)',
    'OUTPUT' : road_length_path
})
print(f"road length calculated and saved")

# joining road length into grid
grid_params_road_path = f"{save_base}04_grid_params_road.shp"
grid_params_road = processing.run("native:joinattributestable", {
    'INPUT' : grid_layer,
    'FIELD' : 'cluster_la',
    'INPUT_2' : road_length['OUTPUT'],
    'FIELD_2' : 'cluster_la',
    'OUTPUT' : grid_params_road_path
})

# def intersect, dissolve, repro, and calculating density percentage of area in grid
def percentage(input_layer_path, intersect_layer, output_path):
    input_layer = QgsVectorLayer(input_layer_path, "input_intersect", "ogr")
    intersect_layer  = grid_layer
    if not input_layer.isValid() or not intersect_layer.isValid():
        raise Exception("input layer or intersect layer failed to load")
    
    input_name = os.path.splitext(os.path.basename(input_layer_path))[0]
    area_field_name = f"area_{input_name}"
    norm_field_name = f"norm_{input_name}"
    percent_field_name = f"percent_{input_name}"

    # reproject input layer to utm
    utm_result = processing.run("native:reprojectlayer", {
        'INPUT' : input_layer,
        'TARGET_CRS': 'EPSG:32748',
        'OUTPUT' : 'TEMPORARY_OUTPUT'
    }) ['OUTPUT']

    # intersect
    intersect_path = f"{save_base}intersect_{input_name}.shp"
    intersect_result = processing.run("native:intersection", {
        'INPUT' : utm_result,
        'OVERLAY' : intersect_layer,
        'INPUT_FIELDS' : ['OBJECTID'],
        'OVERLAY_FIELDS' : ['cluster_la'],
        'OUTPUT' : intersect_path
    }) ['OUTPUT']

    # dissolve based on cluster_la
    dissolve_path = f"{save_base}dissolve_{input_name}.shp"
    dissolve_result = processing.run("native:dissolve", {
        'INPUT' : intersect_result,
        'FIELD' : ['cluster_la'],
        'OUTPUT' : dissolve_path
    })['OUTPUT']

    # calculating area for feature in each grid
    area_path = f"{save_base}area_{input_name}.shp"
    area = processing.run("qgis:fieldcalculator", {
        'INPUT' : dissolve_result,
        'FIELD_NAME' : area_field_name,
        'FIELD_TYPE' : 0, #decimal number
        'FIELD_LENGTH' : 10,
        'FIELD_PRECISION' : 3,
        'FORMULA' : 'area($geometry)',
        'OUTPUT' : area_path
    })['OUTPUT']

    # joining area of feature to grid layer
    grid_params_area_path = f"{save_base}joined_grid_params_{input_name}.shp"
    grid_params_area = processing.run("native:joinattributestable", {
        'INPUT' : grid_layer,
        'FIELD' : 'cluster_la',
        'INPUT_2' : area,
        'FIELD_2' :'cluster_la',
        'OUTPUT' : grid_params_area_path
    })['OUTPUT']

    # calculating area percentage
    percentage_path = f"{save_base}percentage_{input_name}.shp"
    percentage = processing.run("qgis:fieldcalculator", {
        'INPUT': grid_params_area,
        'FIELD_NAME': percent_field_name,
        'FIELD_TYPE': 0,
        'FIELD_LENGTH': 10,
        'FIELD_PRECISION': 3,
        'FORMULA': f'coalesce("{area_field_name}", 0) / area($geometry) * 100',
        'OUTPUT': percentage_path
    })
    percentage_layer = QgsVectorLayer(percentage_path, f"percentage_{input_name}", "ogr")

    # normalisasi
    laundered_percent_field = next(
        (field.name() for field in percentage_layer.fields() if field.name().startswith("percent_")),
        None
    )
    if laundered_percent_field is None:
        raise Exception("Percentage field from percentage function not found after calculation")
    
    values = [f[laundered_percent_field] for f in percentage_layer.getFeatures() if f[laundered_percent_field] is not None]
    min_val = min(values)
    max_val = max(values)
    norm_formula = f'1 - ((\"{laundered_percent_field}\" - {min_val}) / ({max_val} - {min_val}))'

    normalize = processing.run("qgis:fieldcalculator", {
        'INPUT' : percentage_layer,
        'FIELD_NAME' : norm_field_name,
        'FIELD_TYPE' : 0,
        'FIELD_LENGTH' : 10,
        'FIELD_PRECISION' : 3,
        'FORMULA' : norm_formula,
        'OUTPUT' : output_path
    })
    print(f"percentage function process for {input_layer_path} is done")

# PARAMETER 2 : WATER
print("processing water as parameter")
water_grid_path = f"{save_base}05_water_per_grid.shp"
percentage(
    input_layer_path = "D:/01. ANA/04. TB/02. Task 02/01. Data/water.shp",
    intersect_layer = grid_layer,
    output_path = water_grid_path
)
water_grid_layer = QgsVectorLayer(water_grid_path, "water_grid_path", "ogr")
if not water_grid_layer.isValid():
    raise Exception ("Failed to load water_grid_layer")

# PARAMETER 3 : TREE
print("processing tree as parameter")
tree_grid_path = f"{save_base}06_tree_per_grid.shp"
percentage(
    input_layer_path = "D:/01. ANA/04. TB/02. Task 02/01. Data/tree.shp",
    intersect_layer = grid_layer,
    output_path = tree_grid_path
)
tree_grid_layer = QgsVectorLayer(tree_grid_path, "tree_grid_path", "ogr")
if not tree_grid_layer.isValid():
    raise Exception ("Failed to load tree_grid_layer")

# PARAMETER 4 : SLOPE
print("processing slope as parameter")
slope_grid_path = f"{save_base}slope_grid.shp"
slope_grid = processing.run("native:zonalstatisticsfb", {
    'INPUT' : grid_layer,
    'INPUT_RASTER' : "D:/01. ANA/04. TB/02. Task 02/01. Data/slope_serang.tif",
    'RASTER_BAND' : 1,
    'STATISTICS' : [2],
    'OUTPUT' : slope_grid_path
}) ['OUTPUT']
slope_grid_layer = QgsVectorLayer(slope_grid_path, "slope_grid_path", "ogr")

# normalizing mean slope
slope_field = '_mean'
values = [f[slope_field] for f in slope_grid_layer.getFeatures() if f[slope_field] is not None]
min_slope = min(values)
max_slope = max(values)

norm_slope_grid_path = f"{save_base}07_slope_per_grid.shp"
normalize_slope = processing.run("qgis:fieldcalculator", {
    'INPUT' : slope_grid_layer,
    'FIELD_NAME' : 'norm_slope',
    'FIELD_TYPE' : 0,
    'FIELD_LENGTH' : 10,
    'FIELD_PRECISION' : 3,
    'FORMULA' : f'1 - ((\"{slope_field}\" - {min_slope}) / ({max_slope} - {min_slope}))',
    'OUTPUT' : norm_slope_grid_path
})
norm_slope_grid_layer = QgsVectorLayer(norm_slope_grid_path, "norm_slope_grid_path", "ogr")

# PARAMETER 5 : HOUSE PER KM
print("processing houser per km as parameter")
# calculating how many house in each grid
norm_house_road_path = f"{save_base}08_house_road_per_grid.shp"
house_grid = processing.run("native:countpointsinpolygon", {
    'POLYGONS' : grid_layer,
    'POINTS' : clustered_house_layer,
    'OUTPUT' : 'TEMPORARY_OUTPUT'
})
house_grid_lyr = house_grid['OUTPUT']

joined_house_grid = processing.run("native:joinattributestable", {
    'INPUT' : house_grid_lyr,
    'FIELD' : 'cluster_la',
    'INPUT_2' : grid_params_road['OUTPUT'],
    'FIELD_2' : 'cluster_la',
    'OUTPUT' : 'TEMPORARY_OUTPUT'
})
joined_house_grid_lyr = joined_house_grid['OUTPUT']

house_road_grid = processing.run("qgis:fieldcalculator", {
    'INPUT' : joined_house_grid_lyr,
    'FIELD_NAME' : 'house_road_km',
    'FIELD_TYPE' : 0,
    'FIELD_LENGTH' : 10,
    'FIELD_PRECISION' : 3,
    'FORMULA' : ' "NUMPOINTS" / ("length_roa" /1000)',
    'OUTPUT' : 'TEMPORARY_OUTPUT'
})
house_road_grid_lyr = house_road_grid['OUTPUT']

norm_house_road = processing.run("qgis:fieldcalculator", {
    'INPUT' : house_road_grid_lyr,
    'FIELD_NAME' : 'norm_house_road',
    'FIELD_TYPE' : 0,
    'FIELD_LENGTH' : 10,
    'FIELD_PRECISION' : 3,
    'FORMULA' : '("house_road_km" - minimum("house_road_km")) / (maximum("house_road_km") - minimum("house_road_km"))',
    'OUTPUT' : norm_house_road_path
})
house_road_grid_layer = QgsVectorLayer(norm_house_road_path, "norm_house_road_path", "ogr")

# JOINING PARAMETER INTO ONE FILE
print("joining all parameter in one file")
joined_calc_grid_path = f"{save_base}010_final_calc_grid.shp"
grid = grid_layer
join_water = processing.run("native:joinattributestable", {
    'INPUT' : grid,
    'FIELD' : 'cluster_la',
    'INPUT_2' : water_grid_layer,
    'FIELD_2' : 'cluster_la',
    'OUTPUT' : 'TEMPORARY_OUTPUT'
})
print("water joined!")
join_water_lyr = join_water['OUTPUT']
join_tree = processing.run("native:joinattributestable", {
    'INPUT' : join_water_lyr,
    'FIELD' : 'cluster_la',
    'INPUT_2' : tree_grid_layer,
    'FIELD_2' : 'cluster_la',
    'OUTPUT' : 'TEMPORARY_OUTPUT'
})
print("tree joined!")
join_tree_lyr = join_tree['OUTPUT']
join_slope = processing.run("native:joinattributestable", {
    'INPUT' : join_tree_lyr,
    'FIELD' : 'cluster_la',
    'INPUT_2' : norm_slope_grid_layer,
    'FIELD_2' : 'cluster_la',
    'OUTPUT' : 'TEMPORARY_OUTPUT'
})
join_slope_lyr = join_slope['OUTPUT']
print("slope joined!")
join_house = processing.run("native:joinattributestable", {
    'INPUT' : join_slope_lyr,
    'FIELD' : 'cluster_la',
    'INPUT_2' : house_road_grid_layer,
    'FIELD_2' : 'cluster_la',
    'OUTPUT' : joined_calc_grid_path
})
all_params_layer = QgsVectorLayer(joined_calc_grid_path, "joined_all_params_layer", "ogr")
print("all params joined!")

# CALCULATING MCDA
print("calculating mcda using all params")
final_calc_grid_path = f"{save_base}011_final_calc_grid.shp"
mcda = processing.run("qgis:fieldcalculator", {
    'INPUT' : all_params_layer,
    'FIELD_NAME' : 'mdca_score',
    'FIELD_TYPE' : 0,
    'FIELD_LENGTH' : 10,
    'FIELD_PRECISION' : 3,
    'FORMULA' : '(0.4 * "norm_house") + (0.2 * "norm_slope") + (0.2 * "norm_tree") + (0.2 * "norm_water")',
    'OUTPUT' : final_calc_grid_path
})

