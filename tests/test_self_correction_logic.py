import unittest
from unittest.mock import MagicMock, patch
import sys
import os

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Mock dependencies before importing backend modules
sys.modules['cohere'] = MagicMock()
sys.modules['streamlit'] = MagicMock()

from backend.error_analyzer import ErrorAnalyzer
from backend.self_corrector import SelfCorrector

class TestSelfCorrectionLogic(unittest.TestCase):

    def setUp(self):
        self.analyzer = ErrorAnalyzer()
        self.corrector = SelfCorrector(max_retries=1, use_cache=False)

    def test_sample_rectangle_pattern(self):
        """Test detection of sampleRectangle error."""
        error_msg = "'ImageCollection' object has no attribute 'sampleRectangle'"
        code = "col.sampleRectangle()"
        analysis = self.analyzer.analyze_error(error_msg, code)
        self.assertEqual(analysis['error_type'], 'GEE_SampleRectangleError')
        self.assertIn("Reduce the collection", analysis['suggestion'])

    def test_feature_collection_geometry_pattern(self):
        """Test detection of FeatureCollection.geometry error."""
        error_msg = "FeatureCollection.geometry: The geometry of a collection is the union..."
        code = "fc.geometry()"
        analysis = self.analyzer.analyze_error(error_msg, code)
        self.assertEqual(analysis['error_type'], 'GEE_CollectionGeometryError')
        self.assertIn("Use .first().geometry()", analysis['suggestion'])

    def test_computed_object_pattern(self):
        """Test detection of ComputedObject attribute error."""
        error_msg = "AttributeError: 'ComputedObject' object has no attribute 'normalizedDifference'"
        code = "median.normalizedDifference(['B8', 'B4'])"
        analysis = self.analyzer.analyze_error(error_msg, code)
        self.assertEqual(analysis['error_type'], 'GEE_ComputedObjectTypeError')
        self.assertIn("explicitly cast the returned object", analysis['suggestion'])

    def test_context_awareness_fallback(self):
        """Test context awareness when regex fails but keywords match."""
        error_msg = "AttributeError: object has no attribute 'sampleRectangle'" # Generic error
        code = "my_collection.sampleRectangle()"
        # Mocking context where regex might fail but context catches it
        # Note: The regex I added is specific, but let's test the context logic
        # by using a message that DOESN'T match the regex but has keywords if I force it
        
        # Actually, let's test the specific context logic path
        # I need to bypass the regex match to test the else block
        # So I'll use an error message that doesn't match any regex
        error_msg_generic = "Some generic error about ImageCollection"
        code_with_context = "x = col.sampleRectangle()"
        
        analysis = self.analyzer.analyze_error(error_msg_generic, code_with_context)
        # It should catch it via context
        self.assertEqual(analysis['error_type'], 'GEE_SampleRectangleError')

    def test_fail_fast_memory_error(self):
        """Test that memory errors cause immediate failure."""
        with patch('backend.self_corrector.run_gee_code') as mock_run:
            mock_run.side_effect = Exception("User memory limit exceeded")
            
            result = self.corrector.execute_with_retry("code", "query")
            
            self.assertFalse(result['success'])
            self.assertTrue(result.get('fail_fast', False))
            self.assertEqual(result['attempts'], 1) # Should not retry

    def test_line_number_extraction(self):
        """Test extraction of line numbers from traceback."""
        with patch('backend.self_corrector.run_gee_code') as mock_run:
            # Simulate an error with a traceback
            try:
                exec("raise ValueError('Test Error')")
            except Exception as e:
                mock_run.side_effect = e
            
            # We need to mock log_with_context to check if line_number was passed
            with patch('backend.self_corrector.log_with_context') as mock_log:
                self.corrector.execute_with_retry("code", "query")
                
                # Check calls to find the one with line_number
                found = False
                for call in mock_log.call_args_list:
                    if 'line_number' in call.kwargs:
                        found = True
                        break
                self.assertTrue(found, "Line number should be extracted and logged")

if __name__ == '__main__':
    unittest.main()
