import ee
import geemap

def run_query():
    ee.Initialize()
    geometry = ee.FeatureCollection("FAO/GAUL/2015/level1").filter(ee.Filter.eq('ADM1_NAME', 'Delhi'))
    collection = ee.ImageCollection("MODIS/061/MCD19A2_GRANULES")        .filterBounds(geometry)        .filterDate('2023-01-01', '2023-12-31')
    
    median_image = collection.select('Optical_Depth_047').median()
    stats = median_image.reduceRegion(reducer=ee.Reducer.fixedHistogram(0.0, 5.0, 50), geometry=geometry, scale=1000, maxPixels=1e9)
    return stats.getInfo()
