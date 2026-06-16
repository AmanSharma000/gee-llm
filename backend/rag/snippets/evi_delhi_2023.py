import ee
from datetime import datetime


# Load custom India boundaries (village-level granularity)
india_boundaries = ee.FeatureCollection("projects/ee-myresearch/assets/India_sorted")

# Filter for Delhi State
delhi = india_boundaries.filter(ee.Filter.eq('STATE', 'DELHI')).first()
geometry = delhi.geometry()

# Target year
year = 2023

start = ee.Date.fromYMD(year, 1, 1)
end = ee.Date.fromYMD(year, 12, 31)

# Load Landsat 8 Collection 2 Tier 1 Level 2
collection = (
    ee.ImageCollection("LANDSAT/LC08/C02/T1_L2")
    .filterDate(start, end)
    .filterBounds(geometry)
    .filter(ee.Filter.lt("CLOUD_COVER", 20))
)

def calculate_evi(image):
    """Calculate EVI (Enhanced Vegetation Index)"""
    # Apply scale factors
    optical_bands = image.select('SR_B.').multiply(0.0000275).add(-0.2)
    
    # Get bands
    nir = optical_bands.select('SR_B5')
    red = optical_bands.select('SR_B4')
    blue = optical_bands.select('SR_B2')
    
    # EVI formula: 2.5 * ((NIR - RED) / (NIR + 6*RED - 7.5*BLUE + 1))
    evi = nir.subtract(red).divide(
        nir.add(red.multiply(6)).subtract(blue.multiply(7.5)).add(1)
    ).multiply(2.5).rename('EVI')
    
    return image.addBands(evi)

# Calculate EVI for all images
evi_collection = collection.map(calculate_evi)


# Store result in Feature for consistency
result_feature = ee.Feature(None, {
    'year': year,
    'EVI': evi_collection.select('EVI').mean().reduceRegion(
        reducer=ee.Reducer.fixedHistogram(-1.0, 1.0, 20),
        geometry=geometry,
        scale=30,
        bestEffort=True,
        maxPixels=1e13
    ).get('EVI')
})

result_data = result_feature.getInfo()['properties']

result = {
    'year': result_data['year'],
    'evi_histogram': result_data['EVI'] if result_data.get('EVI') is not None else [],
}
