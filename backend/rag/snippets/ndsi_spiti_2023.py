import ee
import geemap

def run_query():
    ee.Initialize()
    geometry = ee.FeatureCollection("FAO/GAUL/2015/level2").filter(ee.Filter.eq('ADM2_NAME', 'Lahaul and Spiti'))
    collection = ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")        .filterBounds(geometry)        .filterDate('2023-01-01', '2023-12-31')        .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 20))
    
    def calculate_index(image):
        ndsi = image.normalizedDifference(['B3', 'B11']).rename('NDSI')
        return image.addBands(ndsi)
    
    with_index = collection.map(calculate_index)
    median_image = with_index.select('NDSI').median()
    stats = median_image.reduceRegion(reducer=ee.Reducer.fixedHistogram(-1.0, 1.0, 20), geometry=geometry, scale=20, maxPixels=1e9)
    return stats.getInfo()
