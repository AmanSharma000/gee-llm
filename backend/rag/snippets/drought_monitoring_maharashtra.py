"""
Monitor drought conditions in Maharashtra using VCI (Vegetation Condition Index).
"""
import ee
from datetime import datetime

# Load custom India boundaries (village-level granularity)
india_boundaries = ee.FeatureCollection("projects/ee-myresearch/assets/India_sorted")

# Filter for Maharashtra state
maharashtra = india_boundaries.filter(ee.Filter.eq('STATE', 'MAHARASHTRA')).first()
geometry = maharashtra.geometry()

# Function to compute VCI for a year
def compute_vci(year):
    year = ee.Number(year)
    start = ee.Date.fromYMD(year, 1, 1)
    end = ee.Date.fromYMD(year, 12, 31)
    
    s2 = ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED') \
        .filterDate(start, end) \
        .filterBounds(geometry) \
        .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 20))
    
    # Add NDVI band
    def add_ndvi(img):
        ndvi = img.normalizedDifference(['B8', 'B4']).rename('NDVI')
        return img.addBands(ndvi)
    
    s2_ndvi = s2.map(add_ndvi).select('NDVI')
    
    # Get min, max, and mean NDVI
    ndvi_min = s2_ndvi.min()
    ndvi_max = s2_ndvi.max()
    ndvi_mean = s2_ndvi.mean()
    
    # Calculate VCI
    vci = ndvi_mean.subtract(ndvi_min).divide(
        ndvi_max.subtract(ndvi_min)
    ).multiply(100).rename('VCI')
    
    # Get mean VCI over region
    stats = vci.reduceRegion(
        reducer=ee.Reducer.fixedHistogram(-1.0, 1.0, 20),
        geometry=geometry,
        scale=1000,
        bestEffort=True,
        maxPixels=1e13
    )
    
    return ee.Feature(None, {
        'year': year,
        'VCI': stats.get('VCI')
    })

# Compute for last 2 years (dynamic)
current_year = datetime.now().year
year1 = current_year - 2
year2 = current_year - 1

vci_year1 = compute_vci(year1)
vci_year2 = compute_vci(year2)

# Create comparison result
result = ee.FeatureCollection([vci_year1, vci_year2]).getInfo()['features']
result = [{
    'year': f['properties']['year'], 
    'vci': round(f['properties']['VCI'], 2) if f['properties']['VCI'] is not None else None
} for f in result]
