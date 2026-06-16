import ee
from datetime import datetime

india_boundaries = ee.FeatureCollection("projects/ee-myresearch/assets/India_sorted")
kerala = india_boundaries.filter(ee.Filter.eq('STATE', 'KERALA')).first()
geometry = kerala.geometry()
year = 2023

# Sentinel-1 for forest monitoring (VH is sensitive to volume scattering from trees)
collection = (
    ee.ImageCollection("COPERNICUS/S1_GRD")
    .filterBounds(geometry)
    .filterDate(ee.Date.fromYMD(year, 1, 1), ee.Date.fromYMD(year, 12, 31))
    .filter(ee.Filter.eq('instrumentMode', 'IW'))
    .filter(ee.Filter.listContains('transmitterReceiverPolarisation', 'VH'))
)

mean_sar = collection.select('VH').mean()

result_feature = ee.Feature(None, {
    'year': year,
    'satellite': 'Sentinel-1 SAR',
    'region': 'Kerala',
    'VH_histogram': mean_sar.reduceRegion(
        reducer=ee.Reducer.fixedHistogram(-25.0, -5.0, 40),
        geometry=geometry,
        scale=10,
        bestEffort=True,
        maxPixels=1e13
    ).get('VH')
})

result_data = result_feature.getInfo()['properties']
result = {
    'year': result_data['year'],
    'vh_histogram': result_data['VH_histogram'] if result_data.get('VH_histogram') is not None else [],
    'region': result_data['region'],
    'satellite': result_data['satellite']
}
