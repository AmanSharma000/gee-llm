import ee


s2 = ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")
# Load custom India boundaries (village-level granularity)
india_boundaries = ee.FeatureCollection("projects/ee-myresearch/assets/India_sorted")

# Filter for Karnal district (Example for field/region analysis)
karnal = india_boundaries.filter(ee.Filter.eq('DISTRICT', 'KARNAL')).first()
geometry = karnal.geometry()

filtered = (
    s2.filter(ee.Filter.date("2017-01-01", "2018-01-01"))
    .filterBounds(geometry)
)

cs_plus = ee.ImageCollection("GOOGLE/CLOUD_SCORE_PLUS/V1/S2_HARMONIZED")
cs_plus_bands = cs_plus.first().bandNames()

filtered_with_cs = filtered.linkCollection(cs_plus, cs_plus_bands)


def mask_low_qa(image):
    qa_band = "cs"
    clear_threshold = 0.5
    mask = image.select(qa_band).gte(clear_threshold)
    return image.updateMask(mask)


filtered_masked = filtered_with_cs.map(mask_low_qa).select("B.*")


def scale_values(image):
    scaled = image.multiply(0.0001)
    return scaled.copyProperties(image, ["system:time_start"])


def add_ndvi(image):
    ndvi = image.normalizedDifference(["B8", "B4"]).rename("ndvi")
    return image.addBands(ndvi)


with_ndvi = filtered_masked.map(scale_values).map(add_ndvi)


def image_to_feature(image):
    mean_dict = image.select("ndvi").reduceRegion(
        reducer=ee.Reducer.fixedHistogram(-1.0, 1.0, 20),
        geometry=geometry,
        scale=10,
        maxPixels=1e10,
    )
    ndvi_value = mean_dict.get("ndvi")
    date_str = ee.Date(image.get("system:time_start")).format("YYYY-MM-dd")
    return ee.Feature(None, {"date": date_str, "ndvi": ndvi_value})


fc = with_ndvi.map(image_to_feature)

# Fetch results and format properly
result = fc.getInfo()['features']
result = [{
    'date': f['properties']['date'], 
    'ndvi': round(f['properties']['ndvi'], 4) if f['properties']['ndvi'] is not None else None
} for f in result]
