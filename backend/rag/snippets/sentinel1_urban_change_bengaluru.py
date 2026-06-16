import ee
from datetime import datetime

india_boundaries = ee.FeatureCollection("projects/ee-myresearch/assets/India_sorted")
bangalore = india_boundaries.filter(ee.Filter.eq('DISTRICT', 'BENGALURU URBAN')).first()
geometry = bangalore.geometry()
year = 2023

# Sentinel-1 for urban structures (Double bounce causes very high VV and VH)
collection = (
    ee.ImageCollection("COPERNICUS/S1_GRD")
    .filterBounds(geometry)
    .filterDate(ee.Date.fromYMD(year, 1, 1), ee.Date.fromYMD(year, 12, 31))
    .filter(ee.Filter.eq('instrumentMode', 'IW'))
    .filter(ee.Filter.listContains('transmitterReceiverPolarisation', 'VV'))
    .filter(ee.Filter.listContains('transmitterReceiverPolarisation', 'VH'))
)

mean_sar = collection.mean()
# Add VV and VH to amplify double-bounce urban signature
urban_index = mean_sar.select('VV').add(mean_sar.select('VH')).rename('Urban_Backscatter')

result_feature = ee.Feature(None, {
    'year': year,
    'satellite': 'Sentinel-1 SAR',
    'region': 'Bengaluru Urban',
    'Urban_histogram': urban_index.reduceRegion(
        reducer=ee.Reducer.fixedHistogram(-30.0, 10.0, 40),
        geometry=geometry,
        scale=10,
        bestEffort=True,
        maxPixels=1e13
    ).get('Urban_Backscatter')
})

result_data = result_feature.getInfo()['properties']
result = {
    'year': result_data['year'],
    'urban_histogram': result_data['Urban_histogram'] if result_data.get('Urban_histogram') is not None else [],
    'region': result_data['region'],
    'satellite': result_data['satellite']
}
