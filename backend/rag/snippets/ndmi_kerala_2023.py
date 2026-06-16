import ee
from datetime import datetime


# Load custom India boundaries (village-level granularity)
india_boundaries = ee.FeatureCollection("projects/ee-myresearch/assets/India_sorted")

# Filter for Kerala state
kerala = india_boundaries.filter(ee.Filter.eq('STATE', 'KERALA')).first()
geometry = kerala.geometry()

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

def calculate_ndmi(image):
    """Calculate NDMI (Normalized Difference Moisture Index)"""
    optical_bands = image.select('SR_B.').multiply(0.0000275).add(-0.2)
    nir = optical_bands.select('SR_B5')
    swir1 = optical_bands.select('SR_B6')
    
    # NDMI formula: (NIR - SWIR1) / (NIR + SWIR1)
    ndmi = nir.subtract(swir1).divide(nir.add(swir1)).rename('NDMI')
    
    return image.addBands(ndmi)

# Calculate NDMI
ndmi_collection = collection.map(calculate_ndmi)


# Store result in Feature for consistency
result_feature = ee.Feature(None, {
    'year': year,
    'NDMI': ndmi_collection.select('NDMI').mean().reduceRegion(
        reducer=ee.Reducer.fixedHistogram(-1.0, 1.0, 20),
        geometry=geometry,
        scale=30,
        bestEffort=True,
        maxPixels=1e13
    ).get('NDMI')
})

result_data = result_feature.getInfo()['properties']

result = {
    'year': result_data['year'],
    'ndmi_histogram': result_data['NDMI'] if result_data.get('NDMI') is not None else [],
}
