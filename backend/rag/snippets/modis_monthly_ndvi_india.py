import ee
from datetime import datetime


# Load custom India boundaries (village-level granularity)
india_boundaries = ee.FeatureCollection("projects/ee-myresearch/assets/India_sorted")

# Filter for India
india = india_boundaries.filter(ee.Filter.eq('COUNTRY', 'INDIA')).first()
geometry = india.geometry()

# Target year
year = 2023

# Get monthly NDVI for current year using MODIS
months = list(range(1, 13))

def compute_monthly_ndvi_modis(month):
    """Compute mean NDVI for a single month using MODIS"""
    month = ee.Number(month)
    start = ee.Date.fromYMD(year, month, 1)
    end = start.advance(1, 'month')
    
    collection = (
        ee.ImageCollection("MODIS/061/MOD13A1")
        .filterDate(start, end)
        .filterBounds(geometry)
    )
    
    # Get mean NDVI
    mean_ndvi_raw = collection.select('NDVI').mean().reduceRegion(
        reducer=ee.Reducer.fixedHistogram(-1.0, 1.0, 20),
        geometry=geometry,
        scale=500,
        bestEffort=True,
        maxPixels=1e13
    ).get('NDVI')
    
    # Apply scale factor
    ndvi_value = ee.Number(mean_ndvi_raw).multiply(0.0001)
    
    return ee.Feature(None, {
        'month': month,
        'NDVI': ndvi_value
    })

# Server-side mapping
months_list = ee.List(months)
result_fc = ee.FeatureCollection(months_list.map(compute_monthly_ndvi_modis))

# Get results
result = result_fc.getInfo()["features"]
result = [{"month": f["properties"]["month"], "ndvi": round(f["properties"]["NDVI"], 4)} for f in result]
