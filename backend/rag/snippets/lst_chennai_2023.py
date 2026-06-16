import ee
import geemap

def run_query():
    ee.Initialize()
    geometry = ee.FeatureCollection("FAO/GAUL/2015/level2").filter(ee.Filter.eq('ADM2_NAME', 'Chennai'))
    collection = ee.ImageCollection("MODIS/061/MOD11A1")        .filterBounds(geometry)        .filterDate('2023-01-01', '2023-12-31')
    
    def convert_lst(image):
        lst = image.select('LST_Day_1km').multiply(0.02).subtract(273.15).rename('LST')
        return image.addBands(lst)
    
    with_index = collection.map(convert_lst)
    median_image = with_index.select('LST').median()
    stats = median_image.reduceRegion(reducer=ee.Reducer.fixedHistogram(0.0, 60.0, 60), geometry=geometry, scale=1000, maxPixels=1e9)
    return stats.getInfo()
