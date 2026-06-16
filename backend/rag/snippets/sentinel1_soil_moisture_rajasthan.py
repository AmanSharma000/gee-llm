import ee
from datetime import datetime

india_boundaries = ee.FeatureCollection("projects/ee-myresearch/assets/India_sorted")
rajasthan = india_boundaries.filter(ee.Filter.eq('STATE', 'RAJASTHAN')).first()
geometry = rajasthan.geometry()
year = 2023

# Sentinel-1 for bare soil moisture (VV backscatter increases with dielectric constant/moisture)
collection = (
    ee.ImageCollection("COPERNICUS/S1_GRD")
    .filterBounds(geometry)
    .filterDate(ee.Date.fromYMD(year, 6, 1), ee.Date.fromYMD(year, 8, 31)) # Monsoon onset
    .filter(ee.Filter.eq('instrumentMode', 'IW'))
    .filter(ee.Filter.listContains('transmitterReceiverPolarisation', 'VV'))
)

mean_sar = collection.select('VV').mean()

result_feature = ee.Feature(None, {
    'year': year,
    'satellite': 'Sentinel-1 SAR',
    'region': 'Rajasthan',
    'SoilMoisture_VV_histogram': mean_sar.reduceRegion(
        reducer=ee.Reducer.fixedHistogram(-25.0, 5.0, 30),
        geometry=geometry,
        scale=10,
        bestEffort=True,
        maxPixels=1e13
    ).get('VV')
})

result_data = result_feature.getInfo()['properties']
result = {
    'year': result_data['year'],
    'vv_histogram': result_data['SoilMoisture_VV_histogram'] if result_data.get('SoilMoisture_VV_histogram') is not None else [],
    'region': result_data['region'],
    'satellite': result_data['satellite']
}
