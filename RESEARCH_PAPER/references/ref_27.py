import ee
ee.Initialize()

def water_body():
    geom = ee.FeatureCollection('projects/ee-myresearch/assets/India_sorted') \
        .filter(ee.Filter.eq('DISTRICT', 'VARANASI'))
    col = ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED') \
        .filterDate('2023-01-01', '2023-12-31') \
        .select(['B3', 'B8'])
    img = col.median().clip(geom)
    ndwi = img.normalizedDifference(['B3', 'B8'])
    water = ndwi.gt(0.1)
    area = water.multiply(ee.Image.pixelArea()).reduceRegion(ee.Reducer.sum(), geom, 100, maxPixels=1e10).get('nd').getInfo()
    return area

result = water_body()