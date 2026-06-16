import ee
from datetime import datetime


# Load custom India boundaries (village-level granularity)
india_boundaries = ee.FeatureCollection("projects/ee-myresearch/assets/India_sorted")

# Filter for Himachal Pradesh state
himachal = india_boundaries.filter(ee.Filter.eq('STATE', 'HIMACHAL PRADESH')).first()
geometry = himachal.geometry()

# Define pre-fire and post-fire periods
# Example: Fire in May 2023
pre_fire_start = ee.Date('2023-04-01')
pre_fire_end = ee.Date('2023-04-30')
post_fire_start = ee.Date('2023-06-01')
post_fire_end = ee.Date('2023-06-30')

def calculate_nbr_landsat(image):
    """Calculate NBR using Landsat 8"""
    optical_bands = image.select('SR_B.').multiply(0.0000275).add(-0.2)
    nir = optical_bands.select('SR_B5')
    swir2 = optical_bands.select('SR_B7')
    
    # NBR formula: (NIR - SWIR2) / (NIR + SWIR2)
    nbr = nir.subtract(swir2).divide(nir.add(swir2)).rename('NBR')
    
    return image.addBands(nbr)

# Pre-fire NBR
pre_fire_collection = (
    ee.ImageCollection("LANDSAT/LC08/C02/T1_L2")
    .filterDate(pre_fire_start, pre_fire_end)
    .filterBounds(geometry)
    .filter(ee.Filter.lt("CLOUD_COVER", 20))
    .map(calculate_nbr_landsat)
)

pre_fire_nbr = pre_fire_collection.select('NBR').median()

# Post-fire NBR
post_fire_collection = (
    ee.ImageCollection("LANDSAT/LC08/C02/T1_L2")
    .filterDate(post_fire_start, post_fire_end)
    .filterBounds(geometry)
    .filter(ee.Filter.lt("CLOUD_COVER", 20))
    .map(calculate_nbr_landsat)
)

post_fire_nbr = post_fire_collection.select('NBR').median()

# Calculate dNBR (difference NBR) - fire severity
dnbr = pre_fire_nbr.subtract(post_fire_nbr).rename('dNBR')


# Store stats in Feature for consistency
result_feature = ee.Feature(None, {
    'pre_fire_period': '2023-04',
    'post_fire_period': '2023-06',
    'dNBR': dnbr.reduceRegion(
        reducer=ee.Reducer.fixedHistogram(-1.0, 1.0, 20),
        geometry=geometry,
        scale=30,
        bestEffort=True,
        maxPixels=1e13
    ).get('dNBR')
})

result_data = result_feature.getInfo()['properties']

result = {
    'pre_fire_period': result_data['pre_fire_period'],
    'post_fire_period': result_data['post_fire_period'],
    'dnbr': round(result_data['dNBR'], 4) if result_data['dNBR'] else None,
    'severity': 'High' if result_data.get('dNBR', 0) > 0.66 else 'Moderate' if result_data.get('dNBR', 0) > 0.27 else 'Low'
}
