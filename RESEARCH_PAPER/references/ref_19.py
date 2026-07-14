import ee
ee.Initialize()

def trend_ndvi(start, end):
    geom = ee.FeatureCollection('projects/ee-myresearch/assets/India_sorted') \
        .filter(ee.Filter.eq('STATE', 'MAHARASHTRA'))
    res = []
    for y in range(start, end+1):
        c = ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED') \
            .filterDate(f'{y}-01-01', f'{y}-12-31') \
            .select(['B8', 'B4'])
        img = c.median().clip(geom)
        nd = img.normalizedDifference(['B8', 'B4']).reduceRegion(ee.Reducer.mean(), geom, 1000, maxPixels=1e9).get('nd').getInfo()
        res.append(nd)
    return res

result = trend_ndvi(2018, 2023)