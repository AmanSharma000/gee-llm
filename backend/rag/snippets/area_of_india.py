import ee

# Load custom India boundaries (village-level granularity)
india_boundaries = ee.FeatureCollection("projects/ee-myresearch/assets/India_sorted")

# Filter for Village level features to avoid double counting
# The dataset appears to contain hierarchical levels (Country, State, District, Tehsil, Village)
# Summing all features leads to ~5x overestimation (16M vs 3.28M sq km)
# We filter for features where 'VILLAGE' is defined to get the granular sum
india_villages = india_boundaries.filter(ee.Filter.neq('VILLAGE', ''))

# Calculate total area by summing the 'AREA_Ha' field
total_area_ha = india_villages.aggregate_sum('AREA_Ha')

# Convert Hectares to Square Kilometers (1 Ha = 0.01 Sq Km)
total_area_sqkm = ee.Number(total_area_ha).divide(100)


# Store result in Feature for consistency and potential future batching
result_feature = ee.Feature(None, {
    'area_sqkm': total_area_sqkm,
    'region': 'India (Village Sum)',
    'note': 'Calculated by summing village-level areas to avoid administrative overlap'
})

result_data = result_feature.getInfo()['properties']

# Get the result
result = {
    'area_sqkm': round(result_data['area_sqkm'], 2) if result_data['area_sqkm'] else 0,
    'region': result_data['region'],
    'note': result_data['note']
}
