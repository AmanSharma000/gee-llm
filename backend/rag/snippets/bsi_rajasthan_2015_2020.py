import ee


# Load custom India boundaries (village-level granularity)
india_boundaries = ee.FeatureCollection("projects/ee-myresearch/assets/India_sorted")

# Filter for Rajasthan state
rajasthan = india_boundaries.filter(ee.Filter.eq('STATE', 'RAJASTHAN')).first()
geometry = rajasthan.geometry()

# BSI formula for Sentinel-2:
# BSI = ((RED + SWIR) - (NIR + BLUE)) / ((RED + SWIR) + (NIR + BLUE))
def compute_bsi(image):
    red = image.select("B4")
    swir = image.select("B11")
    nir = image.select("B8")
    blue = image.select("B2")
    num = red.add(swir).subtract(nir.add(blue))
    den = red.add(swir).add(nir).add(blue)
    return num.divide(den).rename("BSI")


start_year = 2015
end_year = 2020
years = list(range(start_year, end_year + 1))


def yearly_bsi(year):
    """Compute mean BSI for a single year over Rajasthan state."""
    year = ee.Number(year)  # Ensure year is an EE number
    start = ee.Date.fromYMD(year, 1, 1)
    end = ee.Date.fromYMD(year, 12, 31)

    collection = (
        ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")
        .filterDate(start, end)
        .filterBounds(geometry)
        .filter(ee.Filter.lt("CLOUDY_PIXEL_PERCENTAGE", 20))
    )

    # Handle empty collection case
    median = ee.Algorithms.If(
        collection.size().gt(0),
        collection.median(),
        ee.Image.constant(0).rename("BSI") # Fallback
    )
    median = ee.Image(median) # Cast back to Image

    bsi = compute_bsi(median)

    stats = bsi.reduceRegion(
        reducer=ee.Reducer.fixedHistogram(-1.5, 1.5, 30),
        geometry=geometry,
        scale=10,
        bestEffort=True,
        maxPixels=1e13
    )
    
    # Return a Feature, not a dictionary, for server-side mapping
    return ee.Feature(None, {
        "year": year,
        "BSI": stats.get("BSI")
    })


# Use server-side mapping for performance
years_list = ee.List(years)
result_fc = ee.FeatureCollection(years_list.map(yearly_bsi))

# Fetch all results in ONE network request
result = result_fc.getInfo()["features"]
# Clean up the result structure
result = [{"year": f["properties"]["year"], "BSI": f["properties"]["BSI"]} for f in result]


