import ee
from datetime import datetime

# Load custom India boundaries (village-level granularity)
india_boundaries = ee.FeatureCollection("projects/ee-myresearch/assets/India_sorted")

# Filter for Gurugram city (User specified City -> Filter by VILLAGE)
gurugram = india_boundaries.filter(ee.Filter.eq('VILLAGE', 'GURUGRAM')).first()
geometry = gurugram.geometry()

# Calculate for 5 years
current_year = datetime.now().year
years = list(range(current_year - 5, current_year))


def compute_yearly_ndvi(year):
    """Compute mean NDVI for a single year using MODIS."""
    year = ee.Number(year)
    start = ee.Date.fromYMD(year, 1, 1)
    end = ee.Date.fromYMD(year, 12, 31)
    
    # MODIS NDVI product (16-day composite)
    collection = (
        ee.ImageCollection("MODIS/061/MOD13A1")
        .filterDate(start, end)
        .filterBounds(geometry)
    )
    
    # Compute mean NDVI - store RAW value (will be scaled in result processing)
    ndvi_mean = collection.select('NDVI').mean()
    
    stats = ndvi_mean.reduceRegion(
        reducer=ee.Reducer.fixedHistogram(-1.0, 1.0, 20),
        geometry=geometry,
        scale=500,  # 500m resolution for MODIS
        bestEffort=True,
        maxPixels=1e13
    )
    
    # Store RAW MODIS value (scaled 10000) - will scale in Python after .getInfo()
    return ee.Feature(None, {
        'year': year,
        'NDVI': stats.get('NDVI')
    })

# Server-side mapping
years_list = ee.List(years)
result_fc = ee.FeatureCollection(years_list.map(compute_yearly_ndvi))

# Fetch results and apply MODIS scaling in Python  
result = result_fc.getInfo()["features"]
result = [
    {
        "year": f["properties"]["year"], 
        "ndvi": round(f["properties"]["NDVI"] * 0.0001, 4) if f["properties"]["NDVI"] is not None else None
    } 
    for f in result
]
