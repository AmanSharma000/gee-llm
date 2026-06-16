"""
Crop health monitoring for Punjab using EVI (Enhanced Vegetation Index).
Tracks agricultural health during growing season.
"""
import ee
from datetime import datetime

# Load custom India boundaries (village-level granularity)
india_boundaries = ee.FeatureCollection("projects/ee-myresearch/assets/India_sorted")

# Filter for Punjab state
punjab = india_boundaries.filter(ee.Filter.eq('STATE', 'PUNJAB')).first()
geometry = punjab.geometry()

# Get current year for growing season monitoring
current_year = datetime.now().year

# Load Sentinel-2 for growing season (April to October)
s2 = ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED') \
    .filterDate(f'{current_year}-04-01', f'{current_year}-10-31') \
    .filterBounds(geometry) \
    .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 20))

# Add EVI band (Enhanced Vegetation Index)
def add_evi(img):
    # EVI = 2.5 * ((NIR - Red) / (NIR + 6*Red - 7.5*Blue + 1))
    nir = img.select('B8')
    red = img.select('B4')
    blue = img.select('B2')
    
    evi = nir.subtract(red).divide(
        nir.add(red.multiply(6)).subtract(blue.multiply(7.5)).add(1)
    ).multiply(2.5).rename('EVI')
    
    return img.addBands(evi)

s2_evi = s2.map(add_evi)

# Get monthly EVI values
def compute_monthly_evi(month):
    month = ee.Number(month)
    start = ee.Date.fromYMD(current_year, month, 1)
    end = start.advance(1, 'month')
    
    monthly_col = s2_evi.filterDate(start, end)
    
    mean_evi = ee.Algorithms.If(
        monthly_col.size().gt(0),
        monthly_col.select('EVI').mean(),
        ee.Image.constant(0).rename('EVI')
    )
    mean_evi = ee.Image(mean_evi)
    
    stats = mean_evi.reduceRegion(
        reducer=ee.Reducer.fixedHistogram(-1.0, 1.0, 20),
        geometry=geometry,
        scale=10,
        bestEffort=True,
        maxPixels=1e13
    )
    
    return ee.Feature(None, {
        'month': month,
        'EVI': stats.get('EVI')
    })

# Compute for April to October (months 4-10) using server-side mapping
months = ee.List.sequence(4, 10)
monthly_evi = months.map(compute_monthly_evi)

# Get result in one go
result = ee.FeatureCollection(monthly_evi).getInfo()['features']
result = [{
    'month': f['properties']['month'], 
    'evi': round(f['properties']['EVI'], 4) if f['properties']['EVI'] is not None else None
} for f in result]
