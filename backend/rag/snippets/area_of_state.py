import ee

# Load custom India boundaries (village-level granularity)
india_boundaries = ee.FeatureCollection("projects/ee-myresearch/assets/India_sorted")

# Filter for Rajasthan state
# CRITICAL: We must also filter for 'VILLAGE' != '' to avoid double counting
# The dataset contains overlapping features for State, District, Tehsil, and Village
rajasthan_villages = india_boundaries \
    .filter(ee.Filter.eq('STATE', 'RAJASTHAN')) \
    .filter(ee.Filter.neq('VILLAGE', ''))

# Calculate total area by summing the 'AREA_Ha' field
total_area_ha = rajasthan_villages.aggregate_sum('AREA_Ha')

# Convert Hectares to Square Kilometers (1 Ha = 0.01 Sq Km)
total_area_sqkm = ee.Number(total_area_ha).divide(100)


# Store result in Feature for consistency and potential future batching
result_feature = ee.Feature(None, {
    'area_sqkm': total_area_sqkm,
    'region': 'Rajasthan (Village Sum)',
    'note': 'Calculated by summing village-level areas to avoid administrative overlap'
})

result_data = result_feature.getInfo()['properties']

# Get the result
result = {
    'area_sqkm': round(result_data['area_sqkm'], 2) if result_data['area_sqkm'] else 0,
    'region': result_data['region'],
    'note': result_data['note']
}
