"""
Monthly temperature trend for Rajasthan in 2024 using MODIS Land Surface Temperature.
"""
import ee

# Load custom India boundaries (village-level granularity)
india_boundaries = ee.FeatureCollection("projects/ee-myresearch/assets/India_sorted")

# Filter for Rajasthan state
rajasthan = india_boundaries.filter(ee.Filter.eq('STATE', 'RAJASTHAN')).first()
geometry = rajasthan.geometry()

# Function to compute monthly temperature
def compute_monthly_temp(month):
    month = ee.Number(month)
    start = ee.Date.fromYMD(2024, month, 1)
    end = start.advance(1, 'month')
    
    modis_lst = ee.ImageCollection('MODIS/061/MOD11A1') \
        .select('LST_Day_1km')
    
    monthly_col = modis_lst.filterDate(start, end) \
        .filterBounds(geometry)
    
    mean_img = ee.Algorithms.If(
        monthly_col.size().gt(0),
        monthly_col.mean(),
        ee.Image.constant(0).rename('LST_Day_1km')
    )
    mean_img = ee.Image(mean_img)
    
    # Convert from Kelvin * 0.02 to Celsius
    temp_celsius = mean_img.multiply(0.02).subtract(273.15)
    
    # Get mean temperature over region
    stats = temp_celsius.reduceRegion(
        reducer=ee.Reducer.fixedHistogram(0.0, 60.0, 60),
        geometry=geometry,
        scale=1000,
        bestEffort=True,
        maxPixels=1e13
    )
    
    return ee.Feature(None, {
        'month': month,
        'temperature_celsius': stats.get('LST_Day_1km')
    })

# Compute for all 12 months using server-side mapping
months = ee.List.sequence(1, 12)
monthly_temps = months.map(compute_monthly_temp)

# Get result in one go
result = ee.FeatureCollection(monthly_temps).getInfo()['features']
result = [{'month': f['properties']['month'], 'temperature': f['properties']['temperature_celsius']} for f in result]
