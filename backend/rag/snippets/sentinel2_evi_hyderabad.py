import ee
from datetime import datetime


# Load custom India boundaries (village-level granularity)
# Filter for Hyderabad district
hyderabad = india_boundaries.filter(ee.Filter.eq('DISTRICT', 'HYDERABAD')).first()
geometry = hyderabad.geometry()

# Calculate for multiple years (2020 to 2023)
years = list(range(2020, 2024))  # 2020, 2021, 2022, 2023

def compute_yearly_evi_s2(year):
    """Compute mean EVI for a single year using Sentinel-2"""
    year = ee.Number(year)
    start = ee.Date.fromYMD(year, 1, 1)
    end = ee.Date.fromYMD(year, 12, 31)
    
    collection = (
        ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")
        .filterDate(start, end)
        .filterBounds(geometry)
        .filter(ee.Filter.lt("CLOUDY_PIXEL_PERCENTAGE", 20))
    )
    
    def calculate_evi(image):
        """Calculate EVI using Sentinel-2 bands"""
        # Sentinel-2: B8=NIR, B4=RED, B2=BLUE
        nir = image.select('B8').multiply(0.0001)
        red = image.select('B4').multiply(0.0001)
        blue = image.select('B2').multiply(0.0001)
        
        # EVI formula: 2.5 * ((NIR - RED) / (NIR + 6*RED - 7.5*BLUE + 1))
        evi = nir.subtract(red).divide(
            nir.add(red.multiply(6)).subtract(blue.multiply(7.5)).add(1)
        ).multiply(2.5).rename('EVI')
        
        return image.addBands(evi)
    
    evi_collection = collection.map(calculate_evi)
    
    median = ee.Algorithms.If(
        evi_collection.size().gt(0),
        evi_collection.median(),
        ee.Image.constant(0).rename('EVI')
    )
    median = ee.Image(median)
    
    stats = median.select('EVI').reduceRegion(
        reducer=ee.Reducer.fixedHistogram(-1.0, 1.0, 20),
        geometry=geometry,
        scale=10,  # 10m resolution
        bestEffort=True,
        maxPixels=1e13
    )
    
    return ee.Feature(None, {
        'year': year,
        'EVI': stats.get('EVI')
    })

# Server-side mapping
years_list = ee.List(years)
result_fc = ee.FeatureCollection(years_list.map(compute_yearly_evi_s2))

# Get results
result = result_fc.getInfo()["features"]
result = [{"year": f["properties"]["year"], "evi": round(f["properties"]["EVI"], 4)} for f in result]
