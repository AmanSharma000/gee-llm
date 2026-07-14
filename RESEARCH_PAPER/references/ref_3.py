import ee
ee.Initialize()

def f():
    geom = ee.FeatureCollection('projects/ee-myresearch/assets/India_sorted') \
        .filter(ee.Filter.eq('DISTRICT', 'BENGALURU URBAN'))
    collection = ee.ImageCollection('LANDSAT/LC08/C02/T1_L2') \
        .filterDate('2023-01-01', '2023-12-31') \
        .select(['SR_B3', 'SR_B6'])
    image = collection.median().clip(geom)
    nd = image.normalizedDifference(['SR_B3', 'SR_B6'])
    return nd.reduceRegion(
        reducer=ee.Reducer.mean(),
        geometry=geom,
        scale=100,
        maxPixels=1e9
    ).getInfo()

result = f()