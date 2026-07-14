import ee
ee.Initialize()

def f():
    geom = ee.FeatureCollection('projects/ee-myresearch/assets/India_sorted') \
        .filter(ee.Filter.eq('DISTRICT', 'JAIPUR'))
    collection = ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED') \
        .filterDate('2022-01-01', '2022-12-31') \
        .select(['B8', 'B4', 'B2'])
    image = collection.median().clip(geom)
    evi = image.expression(
        '2.5 * ((B8 - B4) / (B8 + 6 * B4 - 7.5 * B2 + 1))',
        {
            'B8': image.select('B8'),
            'B4': image.select('B4'),
            'B2': image.select('B2')
        }
    )
    return evi.reduceRegion(
        reducer=ee.Reducer.mean(),
        geometry=geom,
        scale=100,
        maxPixels=1e9
    ).getInfo()

result = f()