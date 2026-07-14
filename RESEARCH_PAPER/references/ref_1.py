import ee
ee.Initialize()

def get_ndvi(year):
    collection = ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED') \
        .filterDate(f'{year}-01-01', f'{year}-12-31') \
        .select(['B8', 'B4'])
    geometry = ee.FeatureCollection('projects/ee-myresearch/assets/India_sorted') \
        .filter(ee.Filter.eq('STATE', 'DELHI'))
    image = collection.median().clip(geometry)
    ndvi = image.normalizedDifference(['B8', 'B4']).rename('NDVI')
    return ndvi.reduceRegion(
        reducer=ee.Reducer.mean(),
        geometry=geometry,
        scale=100,
        maxPixels=1e9
    ).get('NDVI').getInfo()

result = get_ndvi(2023)