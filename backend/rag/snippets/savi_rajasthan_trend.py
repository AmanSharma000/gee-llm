import ee
from datetime import datetime


# Load custom India boundaries (village-level granularity)
india_boundaries = ee.FeatureCollection("projects/ee-myresearch/assets/India_sorted")

# Filter for Rajasthan state
rajasthan = india_boundaries.filter(ee.Filter.eq('STATE', 'RAJASTHAN')).first()
geometry = rajasthan.geometry()

# Calculate for multiple years (2019 to 2023)
# Calculate years for the last 5 years (2019-2023)
# Calculate years for the last 5 years (2019-2023)
years = list(range(2019, 2024))  # Keep specific range for SAVI trend analysis

def compute_yearly_savi(year):
    """Compute mean SAVI for a single year"""
    year = ee.Number(year)
    start = ee.Date.fromYMD(year, 1, 1)
    end = ee.Date.fromYMD(year, 12, 31)
    
    collection = (
        ee.ImageCollection("LANDSAT/LC08/C02/T1_L2")
        .filterDate(start, end)
        .filterBounds(geometry)
        .filter(ee.Filter.lt("CLOUD_COVER", 20))
    )
    
    def calculate_savi(image):
        """Calculate SAVI (Soil Adjusted Vegetation Index)"""
        optical_bands = image.select('SR_B.').multiply(0.0000275).add(-0.2)
        nir = optical_bands.select('SR_B5')
        red = optical_bands.select('SR_B4')
        
        # SAVI formula: ((NIR - RED) / (NIR + RED + L)) * (1 + L)
        # L = 0.5 for moderate vegetation
        L = 0.5
        savi = nir.subtract(red).divide(
            nir.add(red).add(L)
        ).multiply(1 + L).rename('SAVI')
        
        return image.addBands(savi)
    
    savi_collection = collection.map(calculate_savi)
    
    median = ee.Algorithms.If(
        savi_collection.size().gt(0),
        savi_collection.median(),
        ee.Image.constant(0).rename('SAVI')
    )
    median = ee.Image(median)
    
    stats = median.select('SAVI').reduceRegion(
        reducer=ee.Reducer.fixedHistogram(-1.0, 1.0, 20),
        geometry=geometry,
        scale=30,
        bestEffort=True,
        maxPixels=1e13
    )
    
    return ee.Feature(None, {
        'year': year,
        'SAVI': stats.get('SAVI')
    })

# Server-side mapping
years_list = ee.List(years)
result_fc = ee.FeatureCollection(years_list.map(compute_yearly_savi))

# Get results
result = result_fc.getInfo()["features"]
result = [{"year": f["properties"]["year"], "savi": round(f["properties"]["SAVI"], 4)} for f in result]
