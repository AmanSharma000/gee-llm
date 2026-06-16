import ee
from datetime import datetime


# Load custom India boundaries (village-level granularity)
india_boundaries = ee.FeatureCollection("projects/ee-myresearch/assets/India_sorted")

# Filter for West Bengal state
west_bengal = india_boundaries.filter(ee.Filter.eq('STATE', 'WEST BENGAL')).first()
geometry = west_bengal.geometry()

# Target year
year = 2023

start = ee.Date.fromYMD(year, 1, 1)
end = ee.Date.fromYMD(year, 12, 31)

# Load Landsat 8
collection = (
    ee.ImageCollection("LANDSAT/LC08/C02/T1_L2")
    .filterDate(start, end)
    .filterBounds(geometry)
    .filter(ee.Filter.lt("CLOUD_COVER", 20))
)

def calculate_mndwi(image):
    """Calculate MNDWI (Modified NDWI)"""
    optical_bands = image.select('SR_B.').multiply(0.0000275).add(-0.2)
    green = optical_bands.select('SR_B3')
    swir1 = optical_bands.select('SR_B6')
    
    # MNDWI formula: (GREEN - SWIR1) / (GREEN + SWIR1)
    mndwi = green.subtract(swir1).divide(green.add(swir1)).rename('MNDWI')
    
    return image.addBands(mndwi)

# Calculate MNDWI
mndwi_collection = collection.map(calculate_mndwi)


# Store result in Feature for consistency
result_feature = ee.Feature(None, {
    'year': year,
    'MNDWI': mndwi_collection.select('MNDWI').mean().reduceRegion(
        reducer=ee.Reducer.fixedHistogram(-1.0, 1.0, 20),
        geometry=geometry,
        scale=30,
        bestEffort=True,
        maxPixels=1e13
    ).get('MNDWI')
})

result_data = result_feature.getInfo()['properties']

result = {
    'year': result_data['year'],
    'mndwi_histogram': result_data['MNDWI'] if result_data.get('MNDWI') is not None else [],
}
