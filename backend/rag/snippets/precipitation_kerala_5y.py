"""
Annual precipitation totals for Kerala from 2020 to 2024 using CHIRPS.
"""
import ee

# Load custom India boundaries (village-level granularity)
india_boundaries = ee.FeatureCollection("projects/ee-myresearch/assets/India_sorted")

# Filter for Kerala state
kerala = india_boundaries.filter(ee.Filter.eq('STATE', 'KERALA')).first()
geometry = kerala.geometry()

# Function to compute yearly precipitation
def compute_yearly_precip(year):
    year = ee.Number(year)
    start = ee.Date.fromYMD(year, 1, 1)
    end = ee.Date.fromYMD(year, 12, 31)
    
    chirps = ee.ImageCollection('UCSB-CHG/CHIRPS/DAILY') \
        .filterDate(start, end) \
        .filterBounds(geometry)
    
    # Handle empty collection
    total_precip = ee.Algorithms.If(
        chirps.size().gt(0),
        chirps.select('precipitation').sum(),
        ee.Image.constant(0).rename('precipitation')
    )
    total_precip = ee.Image(total_precip)
    
    # Get mean precipitation over region
    stats = total_precip.reduceRegion(
        reducer=ee.Reducer.fixedHistogram(0.0, 3000.0, 30),
        geometry=geometry,
        scale=5000,
        bestEffort=True,
        maxPixels=1e13
    )
    
    return ee.Feature(None, {
        'year': year,
        'precipitation_mm': stats.get('precipitation')
    })

# Compute for 2020-2024 using server-side mapping
years = ee.List.sequence(2020, 2024)
yearly_precip = years.map(compute_yearly_precip)

# Get result in one go
result = ee.FeatureCollection(yearly_precip).getInfo()['features']
result = [{'year': f['properties']['year'], 'precipitation': f['properties']['precipitation_mm']} for f in result]
