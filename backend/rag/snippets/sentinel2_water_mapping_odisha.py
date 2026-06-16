import ee
from datetime import datetime


# Load custom India boundaries (village-level granularity)
india_boundaries = ee.FeatureCollection("projects/ee-myresearch/assets/India_sorted")

# Filter for Odisha state
odisha = india_boundaries.filter(ee.Filter.eq('STATE', 'ODISHA')).first()
geometry = odisha.geometry()

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

def calculate_mndwi_s2(image):
    """Calculate MNDWI using Sentinel-2"""
    green = image.select('B3').multiply(0.0001)
    swir1 = image.select('B11').multiply(0.0001)
    
    # MNDWI formula: (GREEN - SWIR1) / (GREEN + SWIR1)
    mndwi = green.subtract(swir1).divide(green.add(swir1)).rename('MNDWI')
    
    return image.addBands(mndwi)

# Calculate MNDWI
mndwi_collection = collection.map(calculate_mndwi_s2)

# Get median MNDWI
median_mndwi = mndwi_collection.select('MNDWI').median()

# Threshold for water detection (MNDWI > 0.3)
water_mask = median_mndwi.gt(0.3)


# Batch both water area and mean MNDWI into single .getInfo() call
stats_dict = ee.Dictionary({
    'water_area_m2': water_mask.multiply(ee.Image.pixelArea()).reduceRegion(
        reducer=ee.Reducer.sum(),
        geometry=geometry,
        scale=10,
        bestEffort=True,
        maxPixels=1e13
    ).get('MNDWI'),
    'mean_mndwi': median_mndwi.reduceRegion(
        reducer=ee.Reducer.fixedHistogram(-1.0, 1.0, 20),
        geometry=geometry,
        scale=10,
        bestEffort=True,
        maxPixels=1e13
    ).get('MNDWI')
})

# Single network request!
result_data = stats_dict.getInfo()

# Convert to square kilometers
water_area_km2 = result_data['water_area_m2'] / 1_000_000 if result_data['water_area_m2'] else 0

result = {
    'year': year,
    'mndwi': round(result_data['mean_mndwi'], 4) if result_data['mean_mndwi'] else None,
    'water_area_km2': round(water_area_km2, 2),
    'satellite': 'Sentinel-2'
}
