import ee
from datetime import datetime


# Load custom India boundaries (village-level granularity)
india_boundaries = ee.FeatureCollection("projects/ee-myresearch/assets/India_sorted")

# Filter for Maharashtra state
maharashtra = india_boundaries.filter(ee.Filter.eq('STATE', 'MAHARASHTRA')).first()
geometry = maharashtra.geometry()

# Target year
year = 2023

start = ee.Date.fromYMD(year, 1, 1)
end = ee.Date.fromYMD(year, 12, 31)

# Load MODIS NDVI product (16-day composite)
# MODIS already has pre-calculated NDVI
collection = (
    ee.ImageCollection("MODIS/061/MOD13A1")
    .filterDate(start, end)
    .filterBounds(geometry)
)

# MODIS NDVI band already exists, just need to get mean
# Scale factor is 0.0001
mean_ndvi_raw = collection.select('NDVI').mean().reduceRegion(
    reducer=ee.Reducer.fixedHistogram(-1.0, 1.0, 20),
    geometry=geometry,
    scale=500,  # 500m resolution for MODIS
    bestEffort=True,
    maxPixels=1e13
).get('NDVI').getInfo()

# Apply scale factor
ndvi_value = mean_ndvi_raw * 0.0001

result = {'year': year, 'ndvi': round(ndvi_value, 4), 'satellite': 'MODIS', 'resolution': '500m'}
