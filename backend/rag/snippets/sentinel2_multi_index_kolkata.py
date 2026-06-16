import ee
from datetime import datetime


# Load custom India boundaries (village-level granularity)
india_boundaries = ee.FeatureCollection("projects/ee-myresearch/assets/India_sorted")

# Filter for Kolkata district
kolkata = india_boundaries.filter(ee.Filter.eq('DISTRICT', 'KOLKATA')).first()
geometry = kolkata.geometry()

# Target year
year = 2023

start = ee.Date.fromYMD(year, 1, 1)
end = ee.Date.fromYMD(year, 12, 31)

# Load Sentinel-2
collection = (
    ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")
    .filterDate(start, end)
    .filterBounds(geometry)
    .filter(ee.Filter.lt("CLOUDY_PIXEL_PERCENTAGE", 20))
)

def calculate_multi_indices_s2(image):
    """Calculate multiple indices using Sentinel-2"""
    # Scale bands
    nir = image.select('B8').multiply(0.0001)
    red = image.select('B4').multiply(0.0001)
    green = image.select('B3').multiply(0.0001)
    swir1 = image.select('B11').multiply(0.0001)
    swir2 = image.select('B12').multiply(0.0001)
    
    # NDVI: (NIR - RED) / (NIR + RED)
    ndvi = nir.subtract(red).divide(nir.add(red)).rename('NDVI')
    
    # NDWI: (GREEN - NIR) / (GREEN + NIR)
    ndwi = green.subtract(nir).divide(green.add(nir)).rename('NDWI')
    
    # MNDWI: (GREEN - SWIR1) / (GREEN + SWIR1)
    mndwi = green.subtract(swir1).divide(green.add(swir1)).rename('MNDWI')
    
    # UI: (SWIR2 - NIR) / (SWIR2 + NIR)
    ui = swir2.subtract(nir).divide(swir2.add(nir)).rename('UI')
    
    return image.addBands([ndvi, ndwi, mndwi, ui])

# Calculate all indices
multi_index_collection = collection.map(calculate_multi_indices_s2)

# Get mean values for all indices
mean_image = multi_index_collection.select(['NDVI', 'NDWI', 'MNDWI', 'UI']).mean()

# Batch all stats into single .getInfo() call using ee.Dictionary
stats_dict = ee.Dictionary({
    'NDVI': mean_image.select('NDVI').reduceRegion(
        reducer=ee.Reducer.fixedHistogram(-1.0, 1.0, 20),
        geometry=geometry,
        scale=10,
        bestEffort=True,
        maxPixels=1e13
    ).get('NDVI'),
    'NDWI': mean_image.select('NDWI').reduceRegion(
        reducer=ee.Reducer.fixedHistogram(-1.0, 1.0, 20),
        geometry=geometry,
        scale=10,
        bestEffort=True,
        maxPixels=1e13
    ).get('NDWI'),
    'MNDWI': mean_image.select('MNDWI').reduceRegion(
        reducer=ee.Reducer.fixedHistogram(-1.0, 1.0, 20),
        geometry=geometry,
        scale=10,
        bestEffort=True,
        maxPixels=1e13
    ).get('MNDWI'),
    'UI': mean_image.select('UI').reduceRegion(
        reducer=ee.Reducer.fixedHistogram(-1.0, 1.0, 20),
        geometry=geometry,
        scale=10,
        bestEffort=True,
        maxPixels=1e13
    ).get('UI')
})

stats = stats_dict.getInfo()  # Single network request!

result = {
    'year': year,
    'ndvi': round(stats['NDVI'], 4) if stats['NDVI'] is not None else None,
    'ndwi': round(stats['NDWI'], 4) if stats['NDWI'] is not None else None,
    'mndwi': round(stats['MNDWI'], 4) if stats['MNDWI'] is not None else None,
    'ui': round(stats['UI'], 4) if stats['UI'] is not None else None,
    'satellite': 'Sentinel-2'
}
