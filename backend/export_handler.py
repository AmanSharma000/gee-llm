"""
Export handler for results in multiple formats.
Supports CSV, JSON, and PNG exports.
"""
import json
import io
from typing import Any, Dict, Optional
import pandas as pd
from backend.logging_config import setup_logger, log_with_context

logger = setup_logger('backend.export_handler')


class ExportHandler:
    """Handles exporting results to various formats."""
    
    def to_csv(self, result: Any, query: str) -> Optional[bytes]:
        """
        Export result to CSV format.
        
        Args:
            result: The result data
            query: The original query
            
        Returns:
            CSV data as bytes or None if not applicable
        """
        try:
            # Check if result is a list of dicts (time-series data)
            if isinstance(result, list) and len(result) > 0:
                if all(isinstance(item, dict) for item in result):
                    df = pd.DataFrame(result)
                    
                    # Convert to CSV
                    csv_buffer = io.StringIO()
                    df.to_csv(csv_buffer, index=False)
                    csv_data = csv_buffer.getvalue().encode('utf-8')
                    
                    log_with_context(
                        logger, 20, "Exported to CSV",
                        rows=len(df),
                        columns=len(df.columns)
                    )
                    
                    return csv_data
            
            # Check if result is a dict of lists (e.g. {'years': [], 'ndvi': []})
            elif isinstance(result, dict) and all(isinstance(v, list) for v in result.values()):
                # Check if values are lists of same length
                lengths = [len(v) for v in result.values()]
                if len(set(lengths)) == 1 and lengths[0] > 0:
                    df = pd.DataFrame(result)
                    
                    # Convert to CSV
                    csv_buffer = io.StringIO()
                    df.to_csv(csv_buffer, index=False)
                    csv_data = csv_buffer.getvalue().encode('utf-8')
                    
                    log_with_context(
                        logger, 20, "Exported dict-of-lists to CSV",
                        rows=len(df),
                        columns=len(df.columns)
                    )
                    
                    return csv_data
            
            # If result is a single dict with numeric values
            elif isinstance(result, dict):
                df = pd.DataFrame([result])
                csv_buffer = io.StringIO()
                df.to_csv(csv_buffer, index=False)
                csv_data = csv_buffer.getvalue().encode('utf-8')
                
                log_with_context(
                    logger, 20, "Exported dict to CSV",
                    columns=len(df.columns)
                )
                
                return csv_data
            
            log_with_context(
                logger, 30, "Result not suitable for CSV export",
                result_type=type(result).__name__
            )
            return None
            
        except Exception as e:
            log_with_context(
                logger, 40, "CSV export failed",
                error=str(e)
            )
            return None
    
    def to_json(self, result: Any, query: str, code: str = "") -> bytes:
        """
        Export result to JSON format with metadata.
        
        Args:
            result: The result data
            query: The original query
            code: The generated code (optional)
            
        Returns:
            JSON data as bytes
        """
        try:
            from datetime import datetime
            
            export_data = {
                'query': query,
                'result': result,
                'timestamp': datetime.now().isoformat(),
                'code': code if code else None
            }
            
            json_str = json.dumps(export_data, indent=2, ensure_ascii=False)
            json_data = json_str.encode('utf-8')
            
            log_with_context(
                logger, 20, "Exported to JSON",
                size_bytes=len(json_data)
            )
            
            return json_data
            
        except Exception as e:
            log_with_context(
                logger, 40, "JSON export failed",
                error=str(e)
            )
            # Return minimal JSON on error
            return json.dumps({'error': str(e)}).encode('utf-8')
    
    def to_geojson(self, result: Any, query: str) -> Optional[bytes]:
        """
        Export result to GeoJSON format (for spatial features).
        
        Args:
            result: The result data
            query: The original query
            
        Returns:
            GeoJSON data as bytes or None if not applicable
        """
        try:
            # Check if result has GeoJSON structure
            if isinstance(result, dict) and 'type' in result:
                if result['type'] in ['Feature', 'FeatureCollection']:
                    geojson_str = json.dumps(result, indent=2)
                    geojson_data = geojson_str.encode('utf-8')
                    
                    log_with_context(
                        logger, 20, "Exported to GeoJSON",
                        type=result['type']
                    )
                    
                    return geojson_data
            
            log_with_context(
                logger, 30, "Result not suitable for GeoJSON export",
                result_type=type(result).__name__
            )
            return None
            
        except Exception as e:
            log_with_context(
                logger, 40, "GeoJSON export failed",
                error=str(e)
            )
            return None


# Global export handler instance
export_handler = ExportHandler()


def export_to_csv(result: Any, query: str) -> Optional[bytes]:
    """Convenience function to export to CSV."""
    return export_handler.to_csv(result, query)


def export_to_json(result: Any, query: str, code: str = "") -> bytes:
    """Convenience function to export to JSON."""
    return export_handler.to_json(result, query, code)


def export_to_geojson(result: Any, query: str) -> Optional[bytes]:
    """Convenience function to export to GeoJSON."""
    return export_handler.to_geojson(result, query)
