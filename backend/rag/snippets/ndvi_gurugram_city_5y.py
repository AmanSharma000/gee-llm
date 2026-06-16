import ee
from datetime import datetime

# Load custom India boundaries (village-level granularity)
india_boundaries = ee.FeatureCollection("projects/ee-myresearch/assets/India_sorted")

# Filter for Gurugram city (User specified City -> Filter by VILLAGE)
gurgaon = india_boundaries.filter(ee.Filter.eq('VILLAGE', 'GURUGRAM')).first()
geometry = gurgaon.geometry()

# Calculate years for the last 5 years
current_year = datetime.now().year
years = list(range(current_year - 5, current_year))


def compute_yearly_ndvi(year):
    """Compute mean NDVI for a single year."""
    year = ee.Number(year)
    start = ee.Date.fromYMD(year, 1, 1)
    end = ee.Date.fromYMD(year, 12, 31)
    
    collection = (
        ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")
        .filterDate(start, end)
        .filterBounds(geometry)
        .filter(ee.Filter.lt("CLOUDY_PIXEL_PERCENTAGE", 20))
    )
    
    median = ee.Algorithms.If(
        collection.size().gt(0),
        collection.median(),
        ee.Image.constant(0).addBands(ee.Image.constant(0)).rename(["B8", "B4"])
    )
    median = ee.Image(median)

    ndvi = median.normalizedDifference(["B8", "B4"]).rename("NDVI").clamp(-1.0, 1.0)
    
    stats = ndvi.reduceRegion(
        reducer=ee.Reducer.fixedHistogram(-1.0, 1.0, 20),
        geometry=geometry,
        scale=10,
        bestEffort=True,
        maxPixels=1e13
    )
    
    return ee.Feature(None, {
        'year': year,
        'NDVI': stats.get("NDVI")
    })

# Server-side mapping
years_list = ee.List(years)
result_fc = ee.FeatureCollection(years_list.map(compute_yearly_ndvi))

# Fetch results
result = result_fc.getInfo()["features"]
result = [{
    "year": f["properties"]["year"], 
    "ndvi": round(f["properties"]["NDVI"], 4) if f["properties"]["NDVI"] is not None else None
} for f in result]

