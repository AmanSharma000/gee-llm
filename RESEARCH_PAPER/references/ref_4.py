import ee
ee.Initialize()

def f():
    geom = ee.FeatureCollection('projects/ee-myresearch/assets/India_sorted') \
        .filter(ee.Filter.eq('DISTRICT', 'CHENNAI'))
    collection = ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED') \
        .filterDate('2023-01-01', '2023-12-31') \
        .select(['B3', 'B8'])
    image = collection.median().clip(geom)
    nd = image.normalizedDifference(['B3', 'B8'])
    return nd.reduceRegion(
        reducer=ee.Reducer.mean(),
        geometry=geom,
        scale=100,
        maxPixels=1e9
    ).getInfo()

result = f()