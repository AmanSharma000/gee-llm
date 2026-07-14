import ee
ee.Initialize()

def compare_ndvi(year):
    collection = ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED') \
        .filterDate(f'{year}-01-01', f'{year}-12-31') \
        .select(['B8', 'B4'])
    g1 = ee.FeatureCollection('projects/ee-myresearch/assets/India_sorted') \
        .filter(ee.Filter.eq('STATE', 'DELHI'))
    g2 = ee.FeatureCollection('projects/ee-myresearch/assets/India_sorted') \
        .filter(ee.Filter.eq('STATE', 'MAHARASHTRA'))
    img1 = collection.median().clip(g1)
    img2 = collection.median().clip(g2)
    n1 = img1.normalizedDifference(['B8', 'B4']).reduceRegion(ee.Reducer.mean(), g1, 1000, maxPixels=1e9).get('nd').getInfo()
    n2 = img2.normalizedDifference(['B8', 'B4']).reduceRegion(ee.Reducer.mean(), g2, 1000, maxPixels=1e9).get('nd').getInfo()
    return n1, n2

result = compare_ndvi(2023)