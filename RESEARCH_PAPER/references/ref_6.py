import ee
ee.Initialize()

def f():
    geom = ee.FeatureCollection('projects/ee-myresearch/assets/India_sorted') \
        .filter(ee.Filter.eq('STATE', 'UTTARAKHAND'))
    collection = ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED') \
        .filterDate('2023-01-01', '2023-12-31') \
        .select(['B8', 'B12'])
    image = collection.median().clip(geom)
    nd = image.normalizedDifference(['B8', 'B12'])
    return nd.reduceRegion(
        reducer=ee.Reducer.mean(),
        geometry=geom,
        scale=1000,
        maxPixels=1e9
    ).getInfo()

result = f()