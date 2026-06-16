"""
Compare NDVI between two years for a specific region (Delhi).
Returns side-by-side comparison data.
"""
import ee

# Load custom India boundaries (village-level granularity)
india_boundaries = ee.FeatureCollection("projects/ee-myresearch/assets/India_sorted")

# Filter for Delhi State
delhi = india_boundaries.filter(ee.Filter.eq('STATE', 'DELHI')).first()
geometry = delhi.geometry()

# Function to compute yearly NDVI
def compute_yearly_ndvi(year):
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
    
    s2_ndvi = s2.map(add_ndvi)
    median = s2_ndvi.median()
    
    # Get mean NDVI over region
    stats = median.select('NDVI').reduceRegion(
        reducer=ee.Reducer.fixedHistogram(-1.0, 1.0, 20),
        geometry=geometry,
        scale=30,
        maxPixels=1e9
    )
    
    return ee.Feature(None, {
        'year': year,
        'NDVI': stats.get('NDVI')
    })

# Compute for 2023 and 2024
ndvi_2023 = compute_yearly_ndvi(2023)
ndvi_2024 = compute_yearly_ndvi(2024)

# Create comparison result
result = ee.FeatureCollection([ndvi_2023, ndvi_2024]).getInfo()['features']
result = [{'year': f['properties']['year'], 'NDVI': f['properties']['NDVI']} for f in result]
