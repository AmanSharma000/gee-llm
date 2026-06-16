import ee
from datetime import datetime

# Load custom India boundaries
india_boundaries = ee.FeatureCollection("projects/ee-myresearch/assets/India_sorted")
assam = india_boundaries.filter(ee.Filter.eq('STATE', 'ASSAM')).first()
geometry = assam.geometry()
year = 2023

# Sentinel-1 for water mapping (VV is best for water)
collection = (
    ee.ImageCollection("COPERNICUS/S1_GRD")
    .filterBounds(geometry)
    .filterDate(ee.Date.fromYMD(year, 6, 1), ee.Date.fromYMD(year, 9, 30)) # Monsoon season
    .filter(ee.Filter.eq('instrumentMode', 'IW'))
    .filter(ee.Filter.listContains('transmitterReceiverPolarisation', 'VV'))
    .filter(ee.Filter.eq('orbitProperties_pass', 'DESCENDING'))
)

mean_sar = collection.select('VV').mean()

# Store result using fixedHistogram (-30 to 0 dB is typical for water and land)
result_feature = ee.Feature(None, {
    'year': year,
    'satellite': 'Sentinel-1 SAR',
    'region': 'Assam',
    'VV_histogram': mean_sar.reduceRegion(
        reducer=ee.Reducer.fixedHistogram(-30.0, 0.0, 30),
        geometry=geometry,
        scale=10,
        bestEffort=True,
        maxPixels=1e13
    ).get('VV')
})

result_data = result_feature.getInfo()['properties']
result = {
    'year': result_data['year'],
    'vv_histogram': result_data['VV_histogram'] if result_data.get('VV_histogram') is not None else [],
    'region': result_data['region'],
    'satellite': result_data['satellite']
}
