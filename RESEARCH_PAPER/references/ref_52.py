import ee
ee.Initialize()
def get_nightlights():
    collection = ee.ImageCollection('NOAA/VIIRS/DNB/MONTHLY_V1/VCMSLCFG').filterDate('2023-01-01', '2023-12-31')
    geometry = ee.FeatureCollection('FAO/GAUL/2015/level1').filter(ee.Filter.eq('ADM1_NAME', 'Delhi'))
    image = collection.median().clip(geometry)
    return image.select('avg_rad').reduceRegion(reducer=ee.Reducer.mean(), geometry=geometry.geometry(), scale=500, maxPixels=1e9).get('avg_rad').getInfo()
result = get_nightlights()