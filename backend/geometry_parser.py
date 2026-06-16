"""
Geometry Parser for GeoAI
Parses uploaded geometry files (GeoJSON, KML, Shapefile) and converts to EE Geometry
"""

import json
import ee
import geopandas as gpd
from typing import Union, Dict, Any
from io import BytesIO
import tempfile
import os


class GeometryParser:
    """Parse various geometry file formats"""
    
    def __init__(self):
        """Initialize parser"""
        pass
    
    def parse_geojson(self, file_content: Union[str, bytes]) -> ee.Geometry:
        """
        Parse GeoJSON file and convert to EE geometry
        
        Args:
            file_content: GeoJSON file content (string or bytes)
            
        Returns:
            ee.Geometry object
        """
        if isinstance(file_content, bytes):
            file_content = file_content.decode('utf-8')
        
        data = json.loads(file_content)
        
        # Handle different GeoJSON structures
        if data['type'] == 'FeatureCollection':
            # Use first feature
            if len(data['features']) > 0:
                geometry = data['features'][0]['geometry']
                return ee.Geometry(geometry)
            else:
                raise ValueError("FeatureCollection is empty")
                
        elif data['type'] == 'Feature':
            return ee.Geometry(data['geometry'])
            
        elif data['type'] in ['Point', 'LineString', 'Polygon', 'MultiPoint', 
                              'MultiLineString', 'MultiPolygon', 'GeometryCollection']:
            return ee.Geometry(data)
            
        else:
            raise ValueError(f"Unknown GeoJSON type: {data['type']}")
    
    def parse_kml(self, file_content: bytes) -> ee.Geometry:
        """
        Parse KML file and convert to EE geometry
        
        Args:
            file_content: KML file content (bytes)
            
        Returns:
            ee.Geometry object
        """
        # Use geopandas to read KML
        with tempfile.NamedTemporaryFile(delete=False, suffix='.kml') as tmp:
            tmp.write(file_content)
            tmp_path = tmp.name
        
        try:
            # Read KML using geopandas
            gdf = gpd.read_file(tmp_path, driver='KML')
            
            # Convert to GeoJSON
            geojson = json.loads(gdf.to_json())
            
            # Parse as GeoJSON
            if geojson['features']:
                geometry = geojson['features'][0]['geometry']
                return ee.Geometry(geometry)
            else:
                raise ValueError("KML file contains no geometries")
                
        finally:
            # Clean up temp file
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
    
    def parse_shapefile(self, file_content: bytes) -> ee.Geometry:
        """
        Parse Shapefile and convert to EE geometry
        Note: Shapefiles are actually multiple files (.shp, .shx, .dbf, .prj)
        This expects a ZIP file containing all components
        
        Args:
            file_content: ZIP file content containing shapefile components
            
        Returns:
            ee.Geometry object
        """
        with tempfile.NamedTemporaryFile(delete=False, suffix='.zip') as tmp:
            tmp.write(file_content)
            tmp_path = tmp.name
        
        try:
            # Read shapefile from ZIP
            gdf = gpd.read_file(f"zip://{tmp_path}")
            
            # Convert to GeoJSON
            geojson = json.loads(gdf.to_json())
            
            # Parse as GeoJSON
            if geojson['features']:
                geometry = geojson['features'][0]['geometry']
                return ee.Geometry(geometry)
            else:
                raise ValueError("Shapefile contains no geometries")
                
        finally:
            # Clean up temp file
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
    
    def parse_file(self, file_content: bytes, file_extension: str) -> ee.Geometry:
        """
        Auto-detect file type and parse accordingly
        
        Args:
            file_content: File content (bytes)
            file_extension: File extension (e.g., '.geojson', '.kml', '.zip')
            
        Returns:
            ee.Geometry object
        """
        ext = file_extension.lower()
        
        if ext in ['.geojson', '.json']:
            return self.parse_geojson(file_content)
        elif ext == '.kml':
            return self.parse_kml(file_content)
        elif ext in ['.zip', '.shp']:
            return self.parse_shapefile(file_content)
        else:
            raise ValueError(f"Unsupported file format: {ext}")
    
    def geometry_to_dict(self, geometry: ee.Geometry) -> Dict[str, Any]:
        """
        Convert EE Geometry to dictionary for storage/display
        
        Args:
            geometry: EE Geometry object
            
        Returns:
            Dictionary representation
        """
        return geometry.getInfo()
    
    def get_geometry_bounds(self, geometry: ee.Geometry) -> Dict[str, float]:
        """
        Get bounding box of geometry
        
        Args:
            geometry: EE Geometry object
            
        Returns:
            Dict with 'west', 'south', 'east', 'north' keys
        """
        bounds = geometry.bounds().getInfo()
        coords = bounds['coordinates'][0]
        
        lons = [c[0] for c in coords]
        lats = [c[1] for c in coords]
        
        return {
            'west': min(lons),
            'south': min(lats),
            'east': max(lons),
            'north': max(lats)
        }
    
    def get_geometry_center(self, geometry: ee.Geometry) -> tuple:
        """
        Get center point of geometry
        
        Args:
            geometry: EE Geometry object
            
        Returns:
            (lat, lon) tuple
        """
        centroid = geometry.centroid().coordinates().getInfo()
        return (centroid[1], centroid[0])  # Return as (lat, lon)


# Convenience function
def parse_uploaded_geometry(file_content: bytes, filename: str) -> ee.Geometry:
    """
    Quick function to parse uploaded geometry file
    
    Args:
        file_content: File content (bytes)
        filename: Original filename
        
    Returns:
        ee.Geometry object
    """
    parser = GeometryParser()
    ext = os.path.splitext(filename)[1]
    return parser.parse_file(file_content, ext)
