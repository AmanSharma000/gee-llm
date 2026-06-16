import ee
from datetime import datetime


# Load custom India boundaries (village-level granularity)
india_boundaries = ee.FeatureCollection("projects/ee-myresearch/assets/India_sorted")

# Filter for Uttarakhand state
uttarakhand = india_boundaries.filter(ee.Filter.eq('STATE', 'UTTARAKHAND')).first()
geometry = uttarakhand.geometry()

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

def calculate_nbr(image):
    """Calculate NBR (Normalized Burn Ratio)"""
    optical_bands = image.select('SR_B.').multiply(0.0000275).add(-0.2)
    nir = optical_bands.select('SR_B5')
    swir2 = optical_bands.select('SR_B7')
    
    # NBR formula: (NIR - SWIR2) / (NIR + SWIR2)
    nbr = nir.subtract(swir2).divide(nir.add(swir2)).rename('NBR')
    
    return image.addBands(nbr)

# Calculate NBR
nbr_collection = collection.map(calculate_nbr)


# Store result in Feature for consistency
result_feature = ee.Feature(None, {
    'year': year,
    'NBR': nbr_collection.select('NBR').mean().reduceRegion(
        reducer=ee.Reducer.fixedHistogram(-1.0, 1.0, 20),
        geometry=geometry,
        scale=30,
        bestEffort=True,
        maxPixels=1e13
    ).get('NBR')
})

result_data = result_feature.getInfo()['properties']

result = {
    'year': result_data['year'],
    'nbr_histogram': result_data['NBR'] if result_data.get('NBR') is not None else [],
}
