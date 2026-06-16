import ee
import geemap

def run_query():
    ee.Initialize()
    geometry = ee.FeatureCollection("FAO/GAUL/2015/level1").filter(ee.Filter.eq('ADM1_NAME', 'Rajasthan'))
    collection = ee.ImageCollection("LANDSAT/LC08/C02/T1_L2")        .filterBounds(geometry)        .filterDate('2023-01-01', '2023-12-31')        .filter(ee.Filter.lt('CLOUD_COVER', 10))
    
    def calculate_index(image):
        msavi = image.expression('(2 * NIR + 1 - sqrt((2 * NIR + 1)**2 - 8 * (NIR - RED))) / 2', {
            'NIR': image.select('SR_B5'),
            'RED': image.select('SR_B4')
        }).rename('MSAVI')
        return image.addBands(msavi)
    
    with_index = collection.map(calculate_index)
    median_image = with_index.select('MSAVI').median()
    stats = median_image.reduceRegion(reducer=ee.Reducer.fixedHistogram(-1.0, 1.0, 20), geometry=geometry, scale=30, maxPixels=1e9)
    return stats.getInfo()
