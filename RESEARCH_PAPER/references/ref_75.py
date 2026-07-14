import ee
ee.Initialize()

def compare_ghats():
    india = ee.FeatureCollection('projects/ee-myresearch/assets/India_sorted')
    g1 = india.filter(ee.Filter.inList('STATE', ['TAMIL NADU', 'ANDHRA PRADESH', 'ODISHA', 'WEST BENGAL']))
    g2 = india.filter(ee.Filter.inList('STATE', ['KERALA', 'KARNATAKA', 'GOA', 'MAHARASHTRA']))
    
    collection = ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED') \
        .filterDate('2023-01-01', '2023-12-31') \
        .select(['B8', 'B4'])
        
    img1 = collection.median().clip(g1)
    img2 = collection.median().clip(g2)
    
    n1 = img1.normalizedDifference(['B8', 'B4']).reduceRegion(
        reducer=ee.Reducer.mean(),
        geometry=g1,
        scale=10000,
        maxPixels=1e9
    ).get('nd').getInfo()
    
    n2 = img2.normalizedDifference(['B8', 'B4']).reduceRegion(
        reducer=ee.Reducer.mean(),
        geometry=g2,
        scale=10000,
        maxPixels=1e9
    ).get('nd').getInfo()
    
    return n1, n2

result = compare_ghats()