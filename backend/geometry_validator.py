"""
Geometry Validator for GeoAI
Validates uploaded geometries for size, complexity, and validity
"""

import ee
from typing import Tuple, Optional


class GeometryValidator:
    """Validate geometries before processing"""
    
    # Maximum area in square kilometers
    MAX_AREA_KM2 = 1000000  # 1 million km²
    
    # Maximum number of vertices
    MAX_VERTICES = 10000
    
    def __init__(self):
        """Initialize validator"""
        pass
    
    def validate_geometry(self, geometry: ee.Geometry) -> Tuple[bool, Optional[str]]:
        """
        Validate a geometry
        
        Args:
            geometry: EE Geometry to validate
            
        Returns:
            (is_valid, error_message) tuple
        """
        try:
            # Check if geometry is valid
            if geometry is None:
                return False, "Geometry is None"
            
            # Check geometry type
            geom_type = geometry.type().getInfo()
            if geom_type not in ['Point', 'LineString', 'Polygon', 'MultiPoint', 
                                'MultiLineString', 'MultiPolygon', 'GeometryCollection']:
                return False, f"Invalid geometry type: {geom_type}"
            
            # Check area (only for polygons)
            if geom_type in ['Polygon', 'MultiPolygon']:
                is_valid, msg = self.check_geometry_size(geometry)
                if not is_valid:
                    return False, msg
            
            # Check complexity
            is_valid, msg = self.check_geometry_complexity(geometry)
            if not is_valid:
                return False, msg
            
            return True, None
            
        except Exception as e:
            return False, f"Validation error: {str(e)}"
    
    def check_geometry_size(self, geometry: ee.Geometry) -> Tuple[bool, Optional[str]]:
        """
        Check if geometry size is within limits
        
        Args:
            geometry: EE Geometry to check
            
        Returns:
            (is_valid, error_message) tuple
        """
        try:
            # Get area in square meters
            area_m2 = geometry.area().getInfo()
            
            # Convert to square kilometers
            area_km2 = area_m2 / 1_000_000
            
            if area_km2 > self.MAX_AREA_KM2:
                return False, f"Geometry too large: {area_km2:.2f} km² (max: {self.MAX_AREA_KM2} km²)"
            
            return True, None
            
        except Exception as e:
            return False, f"Error checking size: {str(e)}"
    
    def check_geometry_complexity(self, geometry: ee.Geometry) -> Tuple[bool, Optional[str]]:
        """
        Check if geometry complexity is within limits
        
        Args:
            geometry: EE Geometry to check
            
        Returns:
            (is_valid, error_message) tuple
        """
        try:
            # Get geometry info
            geom_info = geometry.getInfo()
            
            # Count vertices
            vertex_count = self._count_vertices(geom_info)
            
            if vertex_count > self.MAX_VERTICES:
                return False, f"Geometry too complex: {vertex_count} vertices (max: {self.MAX_VERTICES})"
            
            return True, None
            
        except Exception as e:
            return False, f"Error checking complexity: {str(e)}"
    
    def _count_vertices(self, geom_info: dict) -> int:
        """
        Count vertices in a geometry
        
        Args:
            geom_info: Geometry info dict
            
        Returns:
            Number of vertices
        """
        geom_type = geom_info['type']
        coords = geom_info['coordinates']
        
        if geom_type == 'Point':
            return 1
        elif geom_type == 'LineString':
            return len(coords)
        elif geom_type == 'Polygon':
            return sum(len(ring) for ring in coords)
        elif geom_type == 'MultiPoint':
            return len(coords)
        elif geom_type == 'MultiLineString':
            return sum(len(line) for line in coords)
        elif geom_type == 'MultiPolygon':
            return sum(sum(len(ring) for ring in polygon) for polygon in coords)
        elif geom_type == 'GeometryCollection':
            return sum(self._count_vertices(g) for g in geom_info['geometries'])
        else:
            return 0
    
    def simplify_if_needed(
        self, 
        geometry: ee.Geometry, 
        max_error: float = 100
    ) -> Tuple[ee.Geometry, bool]:
        """
        Simplify geometry if it's too complex
        
        Args:
            geometry: EE Geometry to simplify
            max_error: Maximum error in meters for simplification
            
        Returns:
            (simplified_geometry, was_simplified) tuple
        """
        is_valid, msg = self.check_geometry_complexity(geometry)
        
        if is_valid:
            return geometry, False
        else:
            # Simplify geometry
            simplified = geometry.simplify(maxError=max_error)
            return simplified, True
    
    def get_geometry_stats(self, geometry: ee.Geometry) -> dict:
        """
        Get statistics about a geometry
        
        Args:
            geometry: EE Geometry
            
        Returns:
            Dictionary with stats
        """
        try:
            geom_info = geometry.getInfo()
            geom_type = geom_info['type']
            
            stats = {
                'type': geom_type,
                'vertices': self._count_vertices(geom_info)
            }
            
            # Add area for polygons
            if geom_type in ['Polygon', 'MultiPolygon']:
                area_m2 = geometry.area().getInfo()
                stats['area_km2'] = area_m2 / 1_000_000
            
            # Add perimeter for polygons
            if geom_type in ['Polygon', 'MultiPolygon']:
                perimeter_m = geometry.perimeter().getInfo()
                stats['perimeter_km'] = perimeter_m / 1000
            
            # Add length for lines
            if geom_type in ['LineString', 'MultiLineString']:
                length_m = geometry.length().getInfo()
                stats['length_km'] = length_m / 1000
            
            return stats
            
        except Exception as e:
            return {'error': str(e)}


# Convenience function
def validate_uploaded_geometry(geometry: ee.Geometry) -> Tuple[bool, Optional[str]]:
    """
    Quick function to validate uploaded geometry
    
    Args:
        geometry: EE Geometry to validate
        
    Returns:
        (is_valid, error_message) tuple
    """
    validator = GeometryValidator()
    return validator.validate_geometry(geometry)
