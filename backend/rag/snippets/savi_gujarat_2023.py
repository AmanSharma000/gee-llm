import ee
import geemap

def run_query():
    ee.Initialize()
    geometry = ee.FeatureCollection("FAO/GAUL/2015/level1").filter(ee.Filter.eq('ADM1_NAME', 'Gujarat'))
    collection = ee.ImageCollection("LANDSAT/LC08/C02/T1_L2")        .filterBounds(geometry)        .filterDate('2023-01-01', '2023-12-31')        .filter(ee.Filter.lt('CLOUD_COVER', 10))
    
    def calculate_index(image):
        savi = image.expression('((NIR - RED) / (NIR + RED + 0.5)) * (1.5)', {
            'NIR': image.select('SR_B5'),
            'RED': image.select('SR_B4')
        }).rename('SAVI')
        return image.addBands(savi)
    
    with_index = collection.map(calculate_index)
    median_image = with_index.select('SAVI').median()
    stats = median_image.reduceRegion(reducer=ee.Reducer.fixedHistogram(-1.0, 1.0, 20), geometry=geometry, scale=30, maxPixels=1e9)
    return stats.getInfo()
