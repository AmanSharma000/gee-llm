"""
Satellite Selector for GeoAI
Auto-selects best satellite based on query requirements
"""

from typing import Dict, Any, Optional


# Satellite configurations
SATELLITE_CONFIGS = {
    'LANDSAT8': {
        'collection': 'LANDSAT/LC08/C02/T1_L2',
        'name': 'Landsat 8',
        'resolution': 30,
        'revisit_days': 16,
        'bands': {
            'BLUE': 'SR_B2',
            'GREEN': 'SR_B3',
            'RED': 'SR_B4',
            'NIR': 'SR_B5',
            'SWIR1': 'SR_B6',
            'SWIR2': 'SR_B7'
        },
        'scale_factor': 0.0000275,
        'offset': -0.2,
        'cloud_filter': 'CLOUD_COVER'
    },
    'SENTINEL2': {
        'collection': 'COPERNICUS/S2_SR_HARMONIZED',
        'name': 'Sentinel-2',
        'resolution': 10,
        'revisit_days': 5,
        'bands': {
            'BLUE': 'B2',
            'GREEN': 'B3',
            'RED': 'B4',
            'NIR': 'B8',
            'SWIR1': 'B11',
            'SWIR2': 'B12'
        },
        'scale_factor': 0.0001,
        'offset': 0,
        'cloud_filter': 'CLOUDY_PIXEL_PERCENTAGE'
    },
    'MODIS': {
        'collection': 'MODIS/061/MOD13A1',
        'name': 'MODIS',
        'resolution': 500,
        'revisit_days': 1,
        'bands': {
            'NDVI': 'NDVI',
            'EVI': 'EVI'
        },
        'scale_factor': 0.0001,
        'offset': 0,
        'cloud_filter': None  # MODIS products are already cloud-masked
    },
    'SENTINEL1': {
        'collection': 'COPERNICUS/S1_GRD',
        'name': 'Sentinel-1 (SAR)',
        'resolution': 10,
        'revisit_days': 6,
        'bands': {
            'VV': 'VV',
            'VH': 'VH'
        },
        'scale_factor': 1,
        'offset': 0,
        'cloud_filter': None  # SAR doesn't need cloud filtering
    }
}


class SatelliteSelector:
    """Select best satellite based on query requirements"""
    
    def __init__(self):
        """Initialize selector"""
        self.configs = SATELLITE_CONFIGS
    
    def select_satellite(
        self, 
        query: str, 
        region_size_km2: Optional[float] = None
    ) -> str:
        """
        Auto-select best satellite based on query
        
        Args:
            query: User query
            region_size_km2: Optional region size in square kilometers
            
        Returns:
            Satellite key (e.g., 'LANDSAT8', 'SENTINEL2')
        """
        query_lower = query.lower()
        
        # Explicit satellite mention
        if 'sentinel-2' in query_lower or 'sentinel 2' in query_lower:
            return 'SENTINEL2'
        if 'modis' in query_lower:
            return 'MODIS'
        if 'sentinel-1' in query_lower or 'sentinel 1' in query_lower or 'sar' in query_lower:
            return 'SENTINEL1'
        if 'landsat' in query_lower:
            return 'LANDSAT8'
        
        # Based on requirements
        if 'high resolution' in query_lower or 'detailed' in query_lower or 'fine' in query_lower:
            return 'SENTINEL2'
        
        if 'daily' in query_lower or 'frequent' in query_lower or 'continuous' in query_lower:
            return 'MODIS'
        
        if 'flood' in query_lower or 'water' in query_lower or 'moisture' in query_lower:
            # Sentinel-1 SAR is better for water/flood detection
            return 'SENTINEL1'
            
        # Return None if no specific satellite is inferred
        # This allows the prompt builder to rely on RAG or default to Sentinel-2
        return None
    
    def get_satellite_config(self, satellite_key: str) -> Dict[str, Any]:
        """
        Get configuration for a satellite
        
        Args:
            satellite_key: Satellite key
            
        Returns:
            Configuration dictionary
        """
        return self.configs.get(satellite_key, self.configs['LANDSAT8'])
    
    def get_band_mapping(self, satellite_key: str, index: str) -> Dict[str, str]:
        """
        Get band mapping for calculating an index on a specific satellite
        
        Args:
            satellite_key: Satellite key
            index: Index name (e.g., 'NDVI', 'EVI')
            
        Returns:
            Dictionary mapping generic band names to satellite-specific bands
        """
        config = self.get_satellite_config(satellite_key)
        return config['bands']
    
    def get_satellite_info(self, satellite_key: str) -> str:
        """
        Get human-readable info about a satellite
        
        Args:
            satellite_key: Satellite key
            
        Returns:
            Info string
        """
        config = self.get_satellite_config(satellite_key)
        return (
            f"{config['name']} - "
            f"{config['resolution']}m resolution, "
            f"{config['revisit_days']}-day revisit"
        )
    
    def supports_index(self, satellite_key: str, index: str) -> bool:
        """
        Check if satellite supports calculating an index
        
        Args:
            satellite_key: Satellite key
            index: Index name
            
        Returns:
            True if supported
        """
        config = self.get_satellite_config(satellite_key)
        bands = config['bands']
        
        index_lower = index.lower()
        
        # MODIS has pre-calculated NDVI and EVI
        if satellite_key == 'MODIS':
            return index_lower in ['ndvi', 'evi']
        
        # Sentinel-1 (SAR) doesn't support optical indices
        if satellite_key == 'SENTINEL1':
            return False
        
        # Check if required bands are available
        if index_lower in ['ndvi', 'evi', 'savi', 'ndmi']:
            return 'NIR' in bands and 'RED' in bands
        elif index_lower in ['ndwi', 'mndwi']:
            return 'GREEN' in bands and 'SWIR1' in bands
        elif index_lower in ['bsi', 'ui']:
            return 'NIR' in bands and 'SWIR2' in bands
        elif index_lower == 'nbr':
            return 'NIR' in bands and 'SWIR2' in bands
        
        return True  # Default to True


# Convenience function
def select_best_satellite(query: str) -> str:
    """
    Quick function to select best satellite
    
    Args:
        query: User query
        
    Returns:
        Satellite key
    """
    selector = SatelliteSelector()
    return selector.select_satellite(query)
