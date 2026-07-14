import ee
ee.Initialize()

def get_ndvi():
    collection = ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED') \
        .filterDate('2023-01-01', '2023-12-31') \
        .select(['B8', 'B4'])
    geometry = ee.FeatureCollection('projects/ee-myresearch/assets/India_sorted') \
        .filter(ee.Filter.eq('STATE', 'RAJASTHAN'))
    image = collection.median().clip(geometry)
    ndvi = image.normalizedDifference(['B8', 'B4'])
    return ndvi.reduceRegion(
        reducer=ee.Reducer.mean(),
        geometry=geometry,
        scale=1000,
        maxPixels=1e9
    ).get('nd').getInfo()

result = get_ndvi()