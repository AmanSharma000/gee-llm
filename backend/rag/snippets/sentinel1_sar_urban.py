import ee
from datetime import datetime

# Load custom India boundaries (village-level granularity)
india_boundaries = ee.FeatureCollection("projects/ee-myresearch/assets/India_sorted")

# Filter for Mumbai district
mumbai = india_boundaries.filter(ee.Filter.eq('DISTRICT', 'MUMBAI')).first()
geometry = mumbai.geometry()

# Target year
year = 2023

start = ee.Date.fromYMD(year, 1, 1)
end = ee.Date.fromYMD(year, 12, 31)

# Load Sentinel-1 SAR GRD
collection = (
    ee.ImageCollection("COPERNICUS/S1_GRD")
    .filterBounds(geometry)
    .filterDate(start, end)
    .filter(ee.Filter.eq('instrumentMode', 'IW'))
    .filter(ee.Filter.listContains('transmitterReceiverPolarisation', 'VV'))
    .filter(ee.Filter.listContains('transmitterReceiverPolarisation', 'VH'))
    .filter(ee.Filter.eq('orbitProperties_pass', 'DESCENDING'))
)

# Calculate mean backscatter (already in decibels)
mean_sar = collection.mean()

# Store result in Feature for consistency
result_feature = ee.Feature(None, {
    'year': year,
    'satellite': 'Sentinel-1 SAR',
    'region': 'Mumbai',
    'VV_histogram': mean_sar.select('VV').reduceRegion(
        reducer=ee.Reducer.fixedHistogram(-30.0, 0.0, 30),
        geometry=geometry,
        scale=10,  # 10m resolution for Sentinel-1
        bestEffort=True,
        maxPixels=1e13
    ).get('VV'),
    'VH_histogram': mean_sar.select('VH').reduceRegion(
        reducer=ee.Reducer.fixedHistogram(-40.0, 5.0, 45),
        geometry=geometry,
        scale=10,
        bestEffort=True,
        maxPixels=1e13
    ).get('VH')
})

result_data = result_feature.getInfo()['properties']

result = {
    'year': result_data['year'],
    'vv_histogram': result_data['VV_histogram'] if result_data.get('VV_histogram') is not None else [],
    'vh_histogram': result_data['VH_histogram'] if result_data.get('VH_histogram') is not None else [],
    'region': result_data['region'],
    'satellite': result_data['satellite']
}
