"""
Comparison Engine for GeoAI
Handles comparison queries (region vs region, time vs time)
"""

import re
from typing import Dict, Any, Optional, Tuple, List


class ComparisonEngine:
    """Handle comparison queries"""
    
    def __init__(self):
        """Initialize comparison engine"""
        self.comparison_keywords = [
            'compare', 'vs', 'versus', 'vs.', 'difference between',
            'compare between', 'comparison of'
        ]
    
    def detect_comparison_query(self, query: str) -> bool:
        """
        Detect if query is asking for comparison
        
        Args:
            query: User query
            
        Returns:
            True if comparison query
        """
        query_lower = query.lower()
        return any(kw in query_lower for kw in self.comparison_keywords)
    
    def parse_comparison_entities(self, query: str) -> Optional[Dict[str, Any]]:
        """
        Extract entities to compare from query
        
        Args:
            query: User query
            
        Returns:
            Dictionary with comparison details or None
        """
        query_lower = query.lower()
        
        # Pattern 2: "X in YEAR1 vs YEAR2" - Checked first to handle temporal comparisons accurately
        pattern2 = r'(.+?)\s+in\s+(\d{4})\s+(?:vs|versus|vs\.)\s+(\d{4})'
        match = re.search(pattern2, query_lower)
        
        if match:
            raw_entity = match.group(1).strip()
            year1 = int(match.group(2))
            year2 = int(match.group(3))
            
            # Extract index
            index = self._extract_index(raw_entity)
            # Clean region
            region = self._clean_entity(raw_entity)
            
            # Extract satellite preference
            satellite = self._extract_satellite(query_lower)
            
            return {
                'type': 'temporal',
                'region': region,
                'year1': year1,
                'year2': year2,
                'index': index,
                'satellite': satellite
            }

        # Pattern 1: "compare X vs Y" or "X vs Y"
        pattern1 = r'compare\s+(.+?)\s+(?:vs|versus|vs\.)\s+(.+?)(?:\s+for|\s+in|\s+from|$)'
        match = re.search(pattern1, query_lower)
        
        if match:
            raw_entity1 = match.group(1).strip()
            raw_entity2 = match.group(2).strip()
            
            # Extract index if mentioned
            index = self._extract_index(query_lower)
            
            # Clean entities
            entity1 = self._clean_entity(raw_entity1)
            entity2 = self._clean_entity(raw_entity2)
            
            # Extract satellite preference
            satellite = self._extract_satellite(query_lower)
            
            # Extract year range or single year
            year_range = self._extract_year_range(query_lower)
            year = None
            start_year = None
            end_year = None
            
            if year_range:
                start_year, end_year = year_range
            else:
                year = self._extract_year(query)
            
            return {
                'type': 'region',
                'entity1': entity1,
                'entity2': entity2,
                'index': index,
                'year': year,
                'start_year': start_year,
                'end_year': end_year,
                'satellite': satellite
            }
        
        # Pattern 3: "difference between X and Y"
        pattern3 = r'difference\s+between\s+(.+?)\s+and\s+(.+?)(?:\s+for|\s+in|$)'
        match = re.search(pattern3, query_lower)
        
        if match:
            raw_entity1 = match.group(1).strip()
            raw_entity2 = match.group(2).strip()
            index = self._extract_index(query_lower)
            
            # Clean entities
            entity1 = self._clean_entity(raw_entity1)
            entity2 = self._clean_entity(raw_entity2)
            
            # Extract satellite preference
            satellite = self._extract_satellite(query_lower)
            
            # Extract year range or single year
            year_range = self._extract_year_range(query_lower)
            year = None
            start_year = None
            end_year = None
            
            if year_range:
                start_year, end_year = year_range
            else:
                year = self._extract_year(query)

            return {
                'type': 'region',
                'entity1': entity1,
                'entity2': entity2,
                'index': index,
                'year': year,
                'start_year': start_year,
                'end_year': end_year,
                'satellite': satellite
            }
        
        return None

    def _clean_entity(self, text: str) -> str:
        """Remove index names, 'of', comparison keywords, and years from entity name"""
        # Remove index names
        cleaned = re.sub(r'\b(ndvi|evi|savi|ndmi|nbr|mndwi|ui|bsi|ndwi)\b', '', text, flags=re.IGNORECASE).strip()
        # Remove comparison phrases
        for kw in ['compare between', 'difference between', 'comparison of', 'compare', 'versus', 'vs\\.', 'vs']:
            cleaned = re.sub(r'\b' + kw + r'\b', '', cleaned, flags=re.IGNORECASE).strip()
        # Remove 'of', 'for', 'in' followed by digits
        cleaned = re.sub(r'\b(of|for|in)\b\s*\d{4}', '', cleaned, flags=re.IGNORECASE).strip()
        # Remove 'of'
        cleaned = re.sub(r'\bof\b', '', cleaned, flags=re.IGNORECASE).strip()
        # Remove standalone years
        cleaned = re.sub(r'\b20\d{2}\b', '', cleaned).strip()
        # Clean extra spaces
        cleaned = re.sub(r'\s+', ' ', cleaned).strip()
        return cleaned
    
    def _extract_index(self, text: str) -> Optional[str]:
        """Extract index name from text"""
        indices = ['ndvi', 'evi', 'savi', 'ndmi', 'nbr', 'mndwi', 'ui', 'bsi', 'ndwi']
        
        for index in indices:
            if index in text.lower():
                return index.upper()
        
        return 'NDVI'  # Default
    
    def _extract_year(self, text: str) -> Optional[int]:
        """Extract year from text"""
        # Look for 4-digit year
        match = re.search(r'\b(20\d{2})\b', text)
        if match:
            return int(match.group(1))
        return None

    def _extract_year_range(self, text: str) -> Optional[Tuple[int, int]]:
        """Extract year range from text (e.g. '2020-2025', 'from 2020 to 2025')"""
        # Pattern 1: "from 2020 to 2025"
        match = re.search(r'from\s+(20\d{2})\s+to\s+(20\d{2})', text)
        if match:
            return int(match.group(1)), int(match.group(2))
        
        # Pattern 2: "2020-2025"
        match = re.search(r'(20\d{2})-(20\d{2})', text)
        if match:
            return int(match.group(1)), int(match.group(2))
            
        return None

    def _extract_satellite(self, text: str) -> Optional[str]:
        """Extract satellite preference from text"""
        text_lower = text.lower()
        if 'modis' in text_lower:
            return 'MODIS'
        if 'sentinel-2' in text_lower or 'sentinel 2' in text_lower:
            return 'Sentinel-2'
        if 'sentinel-1' in text_lower or 'sentinel 1' in text_lower:
            return 'Sentinel-1'
        if 'landsat' in text_lower:
            return 'Landsat'
        return None
    
    def create_comparison_queries(
        self, 
        comparison_info: Dict[str, Any]
    ) -> Tuple[str, str]:
        """
        Create two separate queries from comparison info
        
        Args:
            comparison_info: Parsed comparison information
            
        Returns:
            Tuple of (query1, query2)
        """
        comp_type = comparison_info['type']
        index = comparison_info.get('index', 'NDVI')
        satellite = comparison_info.get('satellite')
        
        satellite_str = f" using {satellite}" if satellite else ""
        
        if comp_type == 'region':
            entity1 = comparison_info['entity1']
            entity2 = comparison_info['entity2']
            year = comparison_info.get('year')
            start_year = comparison_info.get('start_year')
            end_year = comparison_info.get('end_year')
            
            if start_year and end_year:
                query1 = f"{index} of {entity1} from {start_year} to {end_year}{satellite_str}"
                query2 = f"{index} of {entity2} from {start_year} to {end_year}{satellite_str}"
            elif year:
                query1 = f"{index} of {entity1} for {year}{satellite_str}"
                query2 = f"{index} of {entity2} for {year}{satellite_str}"
            else:
                query1 = f"{index} of {entity1}{satellite_str}"
                query2 = f"{index} of {entity2}{satellite_str}"
            
            return (query1, query2)
        
        elif comp_type == 'temporal':
            region = comparison_info['region']
            year1 = comparison_info['year1']
            year2 = comparison_info['year2']
            
            query1 = f"{index} of {region} for {year1}{satellite_str}"
            query2 = f"{index} of {region} for {year2}{satellite_str}"
            
            return (query1, query2)
        
        return ("", "")
    
    def calculate_difference(
        self, 
        result1: Any, 
        result2: Any
    ) -> Dict[str, Any]:
        """
        Calculate difference between two results, supporting mixed types (e.g. one histogram, one scalar)
        
        Args:
            result1: First result
            result2: Second result
            
        Returns:
            Difference statistics
        """
        def is_hist_array(val):
            return isinstance(val, list) and len(val) > 0 and isinstance(val[0], list) and len(val[0]) >= 2

        def calculate_weighted_avg(hist_list):
            total_count = sum(r[1] for r in hist_list)
            if total_count == 0:
                return 0.0
            weighted_sum = sum(r[0] * r[1] for r in hist_list)
            return weighted_sum / total_count

        def get_result_avg(result: Any) -> float:
            if isinstance(result, (int, float)):
                return float(result)
                
            if isinstance(result, list):
                if not result:
                    return 0.0
                if isinstance(result[0], dict):
                    hist_vals = []
                    scalar_vals = []
                    for row in result:
                        for k, v in row.items():
                            if k.lower() not in ['year', 'years', 'region', 'satellite']:
                                if is_hist_array(v):
                                    hist_vals.append(calculate_weighted_avg(v))
                                elif isinstance(v, (int, float)):
                                    scalar_vals.append(float(v))
                    if hist_vals:
                        return sum(hist_vals) / len(hist_vals)
                    if scalar_vals:
                        return sum(scalar_vals) / len(scalar_vals)
                elif isinstance(result[0], (int, float)):
                    return sum(result) / len(result)
                elif is_hist_array(result):
                    return calculate_weighted_avg(result)
                    
            if isinstance(result, dict):
                for k, v in result.items():
                    if k.lower() not in ['year', 'years', 'region', 'satellite']:
                        if is_hist_array(v):
                            return calculate_weighted_avg(v)
                for k, v in result.items():
                    if k.lower() not in ['year', 'years', 'region', 'satellite']:
                        if isinstance(v, list) and len(v) > 0:
                            if isinstance(v[0], (int, float)):
                                return sum(v) / len(v)
                            elif is_hist_array(v[0]):
                                h_avgs = [calculate_weighted_avg(h) for h in v]
                                return sum(h_avgs) / len(h_avgs)
                for k, v in result.items():
                    if k.lower() not in ['year', 'years', 'region', 'satellite']:
                        if isinstance(v, (int, float)):
                            return float(v)
            return 0.0

        avg1 = get_result_avg(result1)
        avg2 = get_result_avg(result2)
        
        diff = avg2 - avg1
        percent_change = (diff / avg1 * 100) if avg1 != 0 else 0
        
        # Determine if they represent averages or raw values
        is_ts_or_hist = lambda r: isinstance(r, list) or (isinstance(r, dict) and any(isinstance(v, list) for k, v in r.items() if k.lower() not in ['year', 'years', 'region', 'satellite']))
        
        label = 'average' if (is_ts_or_hist(result1) or is_ts_or_hist(result2)) else 'value'
        
        if label == 'average':
            return {
                'average1': round(avg1, 4),
                'average2': round(avg2, 4),
                'absolute_difference': round(abs(diff), 4),
                'percent_change': round(abs(percent_change), 2)
            }
        else:
            return {
                'value1': round(avg1, 4),
                'value2': round(avg2, 4),
                'absolute_difference': round(abs(diff), 4),
                'percent_change': round(abs(percent_change), 2)
            }


# Convenience function
def is_comparison_query(query: str) -> bool:
    """
    Quick function to check if query is comparison
    
    Args:
        query: User query
        
    Returns:
        True if comparison query
    """
    engine = ComparisonEngine()
    return engine.detect_comparison_query(query)
