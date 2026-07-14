import ee
ee.Initialize()

def deforest():
    geom = ee.FeatureCollection('projects/ee-myresearch/assets/India_sorted') \
        .filter(ee.Filter.eq('STATE', 'ARUNACHAL PRADESH'))
    collection = ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED') \
        .filterDate('2023-01-01', '2023-12-31') \
        .select(['B8', 'B4', 'B2'])
    img = collection.median().clip(geom)
    evi = img.expression(
        '2.5 * ((N - R) / (N + 6 * R - 7.5 * B + 1))',
        {
            'N': img.select('B8'),
            'R': img.select('B4'),
            'B': img.select('B2')
        }
    )
    forest = evi.gt(0.4)
    area = forest.multiply(ee.Image.pixelArea()).reduceRegion(
        reducer=ee.Reducer.sum(),
        geometry=geom,
        scale=1000,
        maxPixels=1e10
    ).get('constant').getInfo()
    return area

result = deforest()