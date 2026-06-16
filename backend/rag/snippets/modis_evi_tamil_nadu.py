import ee
from datetime import datetime


# Load custom India boundaries (village-level granularity)
# Filter for Tamil Nadu state
tamil_nadu = india_boundaries.filter(ee.Filter.eq('STATE', 'TAMIL NADU')).first()
geometry = tamil_nadu.geometry()

# Calculate for multiple years (2020 to 2023)
years = list(range(2020, 2024))  # 2020, 2021, 2022, 2023

def compute_yearly_evi_modis(year):
    """Compute mean EVI for a single year using MODIS"""
    year = ee.Number(year)
    start = ee.Date.fromYMD(year, 1, 1)
    end = ee.Date.fromYMD(year, 12, 31)
    
    # MODIS MOD13A1 has pre-calculated EVI
    collection = (
        ee.ImageCollection("MODIS/061/MOD13A1")
        .filterDate(start, end)
        .filterBounds(geometry)
    )
    
    # Get mean EVI (scale factor 0.0001)
    mean_evi_raw = collection.select('EVI').mean().reduceRegion(
        reducer=ee.Reducer.fixedHistogram(-1.0, 1.0, 20),
        geometry=geometry,
        scale=500,  # 500m resolution
        bestEffort=True,
        maxPixels=1e13
    ).get('EVI')
    
    # Apply scale factor
    evi_value = ee.Number(mean_evi_raw).multiply(0.0001)
    
    return ee.Feature(None, {
        'year': year,
        'EVI': evi_value
    })

# Server-side mapping
years_list = ee.List(years)
result_fc = ee.FeatureCollection(years_list.map(compute_yearly_evi_modis))

# Get results
result = result_fc.getInfo()["features"]
result = [{"year": f["properties"]["year"], "evi": round(f["properties"]["EVI"], 4)} for f in result]
