import ee
from datetime import datetime


# Load custom India boundaries (village-level granularity)
# Filter for Ahmedabad district
ahmedabad = india_boundaries.filter(ee.Filter.eq('DISTRICT', 'AHMEDABAD')).first()
geometry = ahmedabad.geometry()

# Define two time periods for urban change detection
year1 = 2018
year2 = 2023

def calculate_ui_landsat(image):
    """Calculate UI (Urban Index) using Landsat 8"""
    optical_bands = image.select('SR_B.').multiply(0.0000275).add(-0.2)
    nir = optical_bands.select('SR_B5')
    swir2 = optical_bands.select('SR_B7')
    
    # UI formula: (SWIR2 - NIR) / (SWIR2 + NIR)
    ui = swir2.subtract(nir).divide(swir2.add(nir)).rename('UI')
    
    return image.addBands(ui)

# Period 1
collection1 = (
    ee.ImageCollection("LANDSAT/LC08/C02/T1_L2")
    .filterDate(f'{year1}-01-01', f'{year1}-12-31')
    .filterBounds(geometry)
    .filter(ee.Filter.lt("CLOUD_COVER", 20))
    .map(calculate_ui_landsat)
)

ui1 = collection1.select('UI').median()

# Period 2
collection2 = (
    ee.ImageCollection("LANDSAT/LC08/C02/T1_L2")
    .filterDate(f'{year2}-01-01', f'{year2}-12-31')
    .filterBounds(geometry)
    .filter(ee.Filter.lt("CLOUD_COVER", 20))
    .map(calculate_ui_landsat)
)

ui2 = collection2.select('UI').median()

# Calculate change
ui_change = ui2.subtract(ui1).rename('UI_Change')


# Batch all statistics into single .getInfo() call using FeatureCollection
stats_features = ee.FeatureCollection([
    ee.Feature(None, {'period': 'ui1', 'UI': ui1.reduceRegion(
        reducer=ee.Reducer.fixedHistogram(-1.0, 1.0, 20),
        geometry=geometry,
        scale=30,
        bestEffort=True,
        maxPixels=1e13
    ).get('UI')}),
    ee.Feature(None, {'period': 'ui2', 'UI': ui2.reduceRegion(
        reducer=ee.Reducer.fixedHistogram(-1.0, 1.0, 20),
        geometry=geometry,
        scale=30,
        bestEffort=True,
        maxPixels=1e13
    ).get('UI')}),
    ee.Feature(None, {'period': 'change', 'UI_Change': ui_change.reduceRegion(
        reducer=ee.Reducer.fixedHistogram(-1.0, 1.0, 20),
        geometry=geometry,
        scale=30,
        bestEffort=True,
        maxPixels=1e13
    ).get('UI_Change')})
])

# Single network request!
stats_results = stats_features.getInfo()['features']

result = {
    'year1': year1,
    'year2': year2,
    'ui_2018': round(stats_results[0]['properties']['UI'], 4),
    'ui_2023': round(stats_results[1]['properties']['UI'], 4),
    'ui_change': round(stats_results[2]['properties']['UI_Change'], 4),
    'urbanization_trend': 'Increasing' if stats_results[2]['properties']['UI_Change'] > 0 else 'Decreasing'
}
