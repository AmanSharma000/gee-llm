import ee
ee.Initialize()

def f():
    geom = ee.FeatureCollection('projects/ee-myresearch/assets/India_sorted') \
        .filter(ee.Filter.eq('DISTRICT', 'HYDERABAD'))
    collection = ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED') \
        .filterDate('2022-01-01', '2022-12-31') \
        .select(['B8', 'B4'])
    image = collection.median().clip(geom)
    savi = image.expression(
        '((B8 - B4) / (B8 + B4 + 0.5)) * 1.5',
        {
            'B8': image.select('B8'),
            'B4': image.select('B4')
        }
    )
    return savi.reduceRegion(
        reducer=ee.Reducer.mean(),
        geometry=geom,
        scale=100,
        maxPixels=1e9
    ).getInfo()

result = f()