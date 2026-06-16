import ee
from datetime import datetime

india_boundaries = ee.FeatureCollection("projects/ee-myresearch/assets/India_sorted")
punjab = india_boundaries.filter(ee.Filter.eq('STATE', 'PUNJAB')).first()
geometry = punjab.geometry()
year = 2023

# Sentinel-1 for crop monitoring
collection = (
    ee.ImageCollection("COPERNICUS/S1_GRD")
    .filterBounds(geometry)
    .filterDate(ee.Date.fromYMD(year, 1, 1), ee.Date.fromYMD(year, 12, 31))
    .filter(ee.Filter.eq('instrumentMode', 'IW'))
    .filter(ee.Filter.listContains('transmitterReceiverPolarisation', 'VV'))
    .filter(ee.Filter.listContains('transmitterReceiverPolarisation', 'VH'))
)

mean_sar = collection.mean()
# Cross-polarization ratio (VH - VV in dB) correlates with crop canopy volume
cross_pol_ratio = mean_sar.select('VH').subtract(mean_sar.select('VV')).rename('VH_VV_Ratio')

result_feature = ee.Feature(None, {
    'year': year,
    'satellite': 'Sentinel-1 SAR',
    'region': 'Punjab',
    'CrossPol_histogram': cross_pol_ratio.reduceRegion(
        reducer=ee.Reducer.fixedHistogram(-15.0, 5.0, 40),
        geometry=geometry,
        scale=10,
        bestEffort=True,
        maxPixels=1e13
    ).get('VH_VV_Ratio')
})

result_data = result_feature.getInfo()['properties']
result = {
    'year': result_data['year'],
    'cross_pol_histogram': result_data['CrossPol_histogram'] if result_data.get('CrossPol_histogram') is not None else [],
    'region': result_data['region'],
    'satellite': result_data['satellite']
}
