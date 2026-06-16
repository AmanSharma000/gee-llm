import ee
from datetime import datetime


# Load custom India boundaries (village-level granularity)
# Filter for Bangalore district
bangalore = india_boundaries.filter(ee.Filter.eq('DISTRICT', 'BANGALORE')).first()
geometry = bangalore.geometry()

# Calculate for multiple years (2018 to 2023)
years = list(range(2018, 2024))  # 2018, 2019, 2020, 2021, 2022, 2023

def compute_yearly_ui(year):
    """Compute mean UI for a single year"""
    year = ee.Number(year)
    start = ee.Date.fromYMD(year, 1, 1)
    end = ee.Date.fromYMD(year, 12, 31)
    
    collection = (
        ee.ImageCollection("LANDSAT/LC08/C02/T1_L2")
        .filterDate(start, end)
        .filterBounds(geometry)
        .filter(ee.Filter.lt("CLOUD_COVER", 20))
    )
    
    def calculate_ui(image):
        """Calculate UI (Urban Index)"""
        optical_bands = image.select('SR_B.').multiply(0.0000275).add(-0.2)
        nir = optical_bands.select('SR_B5')
        swir2 = optical_bands.select('SR_B7')
        
        # UI formula: (SWIR2 - NIR) / (SWIR2 + NIR)
        ui = swir2.subtract(nir).divide(swir2.add(nir)).rename('UI')
        
        return image.addBands(ui)
    
    ui_collection = collection.map(calculate_ui)
    
    median = ee.Algorithms.If(
        ui_collection.size().gt(0),
        ui_collection.median(),
        ee.Image.constant(0).rename('UI')
    )
    median = ee.Image(median)
    
    stats = median.select('UI').reduceRegion(
        reducer=ee.Reducer.fixedHistogram(-1.5, 1.5, 30),
        geometry=geometry,
        scale=30,
        bestEffort=True,
        maxPixels=1e13
    )
    
    return ee.Feature(None, {
        'year': year,
        'UI': stats.get('UI')
    })

# Server-side mapping
years_list = ee.List(years)
result_fc = ee.FeatureCollection(years_list.map(compute_yearly_ui))

# Get results
result = result_fc.getInfo()["features"]
result = [{"year": f["properties"]["year"], "ui": round(f["properties"]["UI"], 4)} for f in result]
