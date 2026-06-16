import ee
import geemap

def run_query():
    ee.Initialize()
    geometry = ee.FeatureCollection("FAO/GAUL/2015/level1").filter(ee.Filter.eq('ADM1_NAME', 'Punjab'))
    collection = ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")        .filterBounds(geometry)        .filterDate('2023-01-01', '2023-12-31')        .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 10))
    
    def calculate_index(image):
        gci = image.expression('(NIR / GREEN) - 1', {
            'NIR': image.select('B9'),
            'GREEN': image.select('B3')
        }).rename('GCI')
        return image.addBands(gci)
    
    with_index = collection.map(calculate_index)
    median_image = with_index.select('GCI').median()
    stats = median_image.reduceRegion(reducer=ee.Reducer.fixedHistogram(-1.0, 5.0, 60), geometry=geometry, scale=20, maxPixels=1e9)
    return stats.getInfo()
