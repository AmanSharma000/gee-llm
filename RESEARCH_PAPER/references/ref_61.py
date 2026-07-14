import ee
ee.Initialize()

def trend_ndvi_punjab():
    geom = ee.FeatureCollection('projects/ee-myresearch/assets/India_sorted') \
        .filter(ee.Filter.eq('STATE', 'PUNJAB'))
    years = ee.List.sequence(2015, 2023)
    
    def get_year_ndvi(y):
        y = ee.Number(y)
        c = ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED') \
            .filterDate(ee.Date.fromYMD(y, 1, 1), ee.Date.fromYMD(y, 12, 31)) \
            .select(['B8', 'B4'])
            
        def compute_ndvi():
            img = c.median().clip(geom)
            nd = img.normalizedDifference(['B8', 'B4'])
            mean = nd.reduceRegion(
                reducer=ee.Reducer.mean(),
                geometry=geom,
                scale=1000,
                maxPixels=1e9
            ).get('nd')
            return ee.Feature(None, {'year': y, 'ndvi': mean})
            
        def return_empty():
            return ee.Feature(None, {'year': y, 'ndvi': None})
            
        return ee.Feature(ee.Algorithms.If(c.size().gt(0), compute_ndvi(), return_empty()))
        
    features = ee.FeatureCollection(years.map(get_year_ndvi))
    features_info = features.getInfo()
    return [f['properties']['ndvi'] for f in features_info['features']]

result = trend_ndvi_punjab()