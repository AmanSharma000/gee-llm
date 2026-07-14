import ee
ee.Initialize()

def snow_himalayas():
    geom = ee.FeatureCollection('projects/ee-myresearch/assets/India_sorted') \
        .filter(ee.Filter.inList('STATE', ['JAMMU & KASHMIR', 'HIMACHAL PRADESH', 'UTTARAKHAND', 'SIKKIM', 'ARUNACHAL PRADESH']))
    
    collection = ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED') \
        .filterDate('2023-01-01', '2023-12-31') \
        .select(['B3', 'B11'])
        
    img = collection.median().clip(geom)
    ndsi = img.normalizedDifference(['B3', 'B11'])
    snow = ndsi.gt(0.4)
    area = snow.multiply(ee.Image.pixelArea()).reduceRegion(
        reducer=ee.Reducer.sum(),
        geometry=geom,
        scale=5000,
        maxPixels=1e10
    ).get('nd').getInfo()
    return area

result = snow_himalayas()