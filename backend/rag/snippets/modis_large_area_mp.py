import ee
from datetime import datetime


# Load custom India boundaries (village-level granularity)
india_boundaries = ee.FeatureCollection("projects/ee-myresearch/assets/India_sorted")

# Filter for Madhya Pradesh state
mp = india_boundaries.filter(ee.Filter.eq('STATE', 'MADHYA PRADESH')).first()
geometry = mp.geometry()

# Calculate for multiple years using MODIS
current_year = datetime.now().year
years = list(range(2019, current_year))

def compute_yearly_ndvi_modis(year):
    """Compute mean NDVI for a single year using MODIS"""
    year = ee.Number(year)
    start = ee.Date.fromYMD(year, 1, 1)
    end = ee.Date.fromYMD(year, 12, 31)
    
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
        'year': year,
        'NDVI': ndvi_value
    })

# Server-side mapping
years_list = ee.List(years)
result_fc = ee.FeatureCollection(years_list.map(compute_yearly_ndvi_modis))

# Get results
result = result_fc.getInfo()["features"]
result = [{"year": f["properties"]["year"], "ndvi": round(f["properties"]["NDVI"], 4)} for f in result]
