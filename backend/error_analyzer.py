"""
Error analyzer for GEE code execution.
Detects common error patterns and suggests fixes.
"""
import re
from typing import Dict, List, Optional, Tuple
from backend.logging_config import setup_logger, log_with_context

logger = setup_logger('backend.error_analyzer')


class ErrorAnalyzer:
    """Analyzes GEE execution errors and suggests corrections."""
    
    # Common error patterns and their fixes
    ERROR_PATTERNS = [
        {
            'pattern': r"name '(\w+)' is not defined",
            'type': 'NameError',
            'suggestion': 'Variable {0} is not defined. Check if it needs to be created or imported.',
            'fix_strategy': 'add_variable_definition'
        },
        {
            'pattern': r"'NoneType' object has no attribute",
            'type': 'AttributeError',
            'suggestion': 'Attempting to access attribute on None. Check if previous operation returned valid data.',
            'fix_strategy': 'add_null_check'
        },
        {
            'pattern': r"No features contain non-null values of property",
            'type': 'GEE_PropertyError',
            'suggestion': 'Property not found in features. Verify property name or filter features.',
            'fix_strategy': 'fix_property_name'
        },
        {
            'pattern': r"Image\.select: (?:Band )?pattern '(\w+)' did not match any bands",
            'type': 'GEE_BandError',
            'suggestion': 'Band {0} not found. Check band names for the dataset.',
            'fix_strategy': 'fix_band_name'
        },
        {
            'pattern': r"Geometry.* parameter 'coordinates' must be",
            'type': 'GEE_GeometryError',
            'suggestion': 'Invalid geometry coordinates. Check coordinate format and order.',
            'fix_strategy': 'fix_geometry'
        },
        {
            'pattern': r"Collection.* parameter 'collection' must be",
            'type': 'GEE_CollectionError',
            'suggestion': 'Invalid collection. Verify collection ID or ensure collection exists.',
            'fix_strategy': 'fix_collection_id'
        },
        {
            'pattern': r"User memory limit exceeded",
            'type': 'GEE_MemoryError',
            'suggestion': 'Memory limit exceeded. Reduce region size, increase scale, or use sampling.',
            'fix_strategy': 'reduce_computation'
        },
        {
            'pattern': r"Computation timed out",
            'type': 'GEE_TimeoutError',
            'suggestion': 'Computation timed out. Simplify query or reduce data volume.',
            'fix_strategy': 'simplify_computation'
        },
        {
            'pattern': r"Image.* parameter 'image' must be",
            'type': 'GEE_ImageError',
            'suggestion': 'Invalid image object. Check if image collection needs .first() or .mosaic().',
            'fix_strategy': 'fix_image_type'
        },
        {
            'pattern': r"Invalid date",
            'type': 'GEE_DateError',
            'suggestion': 'Invalid date format. Use ee.Date() or proper date string format.',
            'fix_strategy': 'fix_date_format'
        },
        {
            'pattern': r"type object 'Date' has no attribute 'now'",
            'type': 'GEE_DateNowError',
            'suggestion': 'ee.Date.now() does not exist in Earth Engine Python API. Use Python datetime.now() or hardcode the year.',
            'fix_strategy': 'fix_date_now'
        },
        {
            'pattern': r"'ImageCollection' object has no attribute 'sampleRectangle'",
            'type': 'GEE_SampleRectangleError',
            'suggestion': 'ImageCollection has no sampleRectangle() method. Reduce the collection to an Image first (e.g., .median(), .mean(), .first()) or use reduceRegion().',
            'fix_strategy': 'reduce_collection_before_sample'
        },
        {
            'pattern': r"'list' object has no attribute 'map'",
            'type': 'Python_ListMapError',
            'suggestion': 'You are trying to call .map() on a Python list. Python lists do not have a .map() method. You MUST convert it to an Earth Engine list first: `ee.List(your_list).map(...)`.',
            'fix_strategy': 'wrap_list_in_ee_list'
        },
        {
            'pattern': r"'ComputedObject' object has no attribute '(\w+)'",
            'type': 'GEE_ComputedObjectTypeError',
            'suggestion': "The 'ComputedObject' object has no attribute '{0}'. This is because server-side control-flow functions (like ee.Algorithms.If) return a generic ee.ComputedObject. You must explicitly cast the returned object to the correct GEE type (e.g., ee.Image(your_object), ee.Feature(your_object), ee.FeatureCollection(your_object), or ee.List(your_object)) before calling type-specific methods.",
            'fix_strategy': 'cast_computed_object'
        },
        {
            'pattern': r"FeatureCollection\.geometry",
            'type': 'GEE_CollectionGeometryError',
            'suggestion': 'Cannot get geometry of a FeatureCollection directly. Use .first().geometry() to get the geometry of the first feature, or .geometry() on the union if intended.',
            'fix_strategy': 'use_first_geometry'
        },
        {
            'pattern': r"Element\.geometry: Parameter 'feature' is required and may not be null",
            'type': 'GEE_NullFeatureError',
            'suggestion': 'The geocoded feature is null. This usually means the region boundary was not found due to a spelling mismatch or invalid field (e.g., check STATE vs DISTRICT vs VILLAGE). For Bangalore, use "BENGALURU URBAN".',
            'fix_strategy': 'fix_region_geocoding'
        },
        {
            'pattern': r"Scientific validation failed: The calculated (\w+) value ([\d.-]+) is outside the valid physical range of (\[[\d.,\s-]+\])",
            'type': 'GEE_ScientificValidationError',
            'suggestion': 'The calculated remote sensing index {0} returned {1}, which is outside the physically valid range {2}. Ensure bands are properly scaled (e.g., multiplying Sentinel-2 bands by 0.0001) and the correct formula is used.',
            'fix_strategy': 'fix_index_calculation'
        }
    ]
    
    def analyze_error(self, error_message: str, code: str) -> Dict:
        """
        Analyze an error and return diagnostic information.
        
        Args:
            error_message: The error message from execution
            code: The code that caused the error
            
        Returns:
            Dictionary with error analysis and suggestions
        """
        log_with_context(
            logger, 20, "Analyzing error",
            error_length=len(error_message),
            code_length=len(code)
        )
        
        # Find matching error pattern
        matched_pattern = None
        extracted_values = []
        
        for pattern_info in self.ERROR_PATTERNS:
            match = re.search(pattern_info['pattern'], error_message, re.IGNORECASE)
            if match:
                matched_pattern = pattern_info
                extracted_values = list(match.groups())
                break
        
        if matched_pattern:
            suggestion = matched_pattern['suggestion'].format(*extracted_values)
            error_type = matched_pattern['type']
            fix_strategy = matched_pattern['fix_strategy']
            
            log_with_context(
                logger, 20, "Error pattern matched",
                error_type=error_type,
                fix_strategy=fix_strategy
            )
        else:
            # Context Awareness: Check code for specific keywords if error is generic
            if "sampleRectangle" in code and "ImageCollection" in error_message:
                 suggestion = "You are trying to use sampleRectangle on an ImageCollection. Reduce it to an Image first."
                 error_type = "GEE_SampleRectangleError"
                 fix_strategy = "reduce_collection_before_sample"
            elif ".geometry()" in code and "FeatureCollection" in error_message:
                 suggestion = "You are likely trying to get geometry from a FeatureCollection. Use .first().geometry()."
                 error_type = "GEE_CollectionGeometryError"
                 fix_strategy = "use_first_geometry"
            elif "ee.Algorithms.If" in code and "ComputedObject" in error_message:
                 suggestion = "You are likely calling a method on a ComputedObject returned by ee.Algorithms.If(). You must explicitly cast the returned object to the correct GEE class (e.g., ee.Image(your_object), ee.Feature(your_object), ee.FeatureCollection(your_object), or ee.List(your_object)) before calling its methods."
                 error_type = "GEE_ComputedObjectTypeError"
                 fix_strategy = "cast_computed_object"
            else:
                # Generic error
                suggestion = "Unknown error. Review the error message and code carefully."
                error_type = "UnknownError"
                fix_strategy = "manual_review"
            
            log_with_context(
                logger, 30, "No regex pattern matched, used context or fallback",
                error_preview=error_message[:200],
                final_error_type=error_type
            )
        
        return {
            'error_type': error_type,
            'error_message': error_message,
            'suggestion': suggestion,
            'fix_strategy': fix_strategy,
            'matched_values': extracted_values,
            'code': code
        }
    
    def generate_correction_prompt(self, analysis: Dict, original_query: str) -> str:
        """
        Generate a prompt for the LLM to correct the code.
        
        Args:
            analysis: Error analysis from analyze_error()
            original_query: The original user query
            
        Returns:
            Correction prompt for LLM
        """
        prompt = f"""The following Google Earth Engine Python code produced an error. Please fix it.

**Original Query:** {original_query}

**Error Type:** {analysis['error_type']}
**Error Message:** {analysis['error_message']}

**Suggestion:** {analysis['suggestion']}

**Failed Code:**
```python
{analysis['code']}
```

**Instructions:**
1. Analyze the error and identify the root cause
2. Fix the code to resolve the error
3. Ensure the corrected code still answers the original query
4. Return ONLY the corrected Python code, no explanations
5. Make sure to define the 'result' variable at the end

**Corrected Code:**
```python
"""
        
        log_with_context(
            logger, 20, "Generated correction prompt",
            prompt_length=len(prompt),
            error_type=analysis['error_type']
        )
        
        return prompt


def analyze_and_suggest_fix(error_message: str, code: str, query: str) -> Tuple[Dict, str]:
    """
    Convenience function to analyze error and generate correction prompt.
    
    Args:
        error_message: The error message
        code: The failed code
        query: The original user query
        
    Returns:
        Tuple of (analysis dict, correction prompt)
    """
    analyzer = ErrorAnalyzer()
    analysis = analyzer.analyze_error(error_message, code)
    correction_prompt = analyzer.generate_correction_prompt(analysis, query)
    
    return analysis, correction_prompt
