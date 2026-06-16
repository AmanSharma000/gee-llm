
import unittest
from unittest.mock import MagicMock, patch
import sys
import os
import ee

# Add backend to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Mock cohere before importing backend.llm_client
sys.modules['cohere'] = MagicMock()

from backend.gee_runner import _convert
from backend.comparison_engine import ComparisonEngine
from backend.llm_client import _call_with_retry

class TestRobustness(unittest.TestCase):

    def test_gee_safety_guard(self):
        """Test that _convert blocks ee.Image and ee.ImageCollection"""
        print("\nTesting GEE Safety Guard...")
        
        # Mock ee objects
        mock_image = MagicMock(spec=ee.Image)
        mock_collection = MagicMock(spec=ee.ImageCollection)
        mock_feature = MagicMock(spec=ee.Feature)
        
        # Should raise RuntimeError for Image
        with self.assertRaises(RuntimeError) as cm:
            _convert(mock_image)
        self.assertIn("Result is too large", str(cm.exception))
        print("[OK] Blocked ee.Image")

        # Should raise RuntimeError for ImageCollection
        with self.assertRaises(RuntimeError) as cm:
            _convert(mock_collection)
        self.assertIn("Result is too large", str(cm.exception))
        print("[OK] Blocked ee.ImageCollection")

        # Should NOT raise for Feature (simulating small object)
        # Note: _convert calls .getInfo(), so we mock that
        mock_feature.getInfo.return_value = {"type": "Feature"}
        try:
            res = _convert(mock_feature)
            self.assertEqual(res, {"type": "Feature"})
            print("[OK] Allowed ee.Feature")
        except RuntimeError:
            self.fail("Should not block ee.Feature")

    def test_comparison_logic_dynamic(self):
        """Test that comparison engine handles unknown indices"""
        print("\nTesting Dynamic Comparison Logic...")
        engine = ComparisonEngine()
        
        # Case 1: Standard NDVI
        res1 = [{"year": 2020, "ndvi": 0.5}, {"year": 2021, "ndvi": 0.6}]
        res2 = [{"year": 2020, "ndvi": 0.4}, {"year": 2021, "ndvi": 0.5}]
        diff = engine.calculate_difference(res1, res2)
        self.assertAlmostEqual(diff['average1'], 0.55)
        self.assertAlmostEqual(diff['average2'], 0.45)
        print("[OK] Handled NDVI")

        # Case 2: Unknown Index (e.g., NDWI)
        res3 = [{"year": 2020, "ndwi": 0.1}, {"year": 2021, "ndwi": 0.2}]
        res4 = [{"year": 2020, "ndwi": 0.3}, {"year": 2021, "ndwi": 0.4}]
        diff_ndwi = engine.calculate_difference(res3, res4)
        self.assertAlmostEqual(diff_ndwi['average1'], 0.15)
        self.assertAlmostEqual(diff_ndwi['average2'], 0.35)
        print("[OK] Handled Unknown Index (NDWI)")

    def test_llm_retries(self):
        """Test LLM retry logic"""
        print("\nTesting LLM Retries...")
        
        mock_client = MagicMock()
        
        # Case 1: Success on first try
        mock_client.chat.return_value = "Success"
        res = _call_with_retry(mock_client, "model", [])
        self.assertEqual(res, "Success")
        print("[OK] Success on first try")
        
        # Case 2: Fail once with 500, then success
        mock_client.chat.reset_mock()
        mock_client.chat.side_effect = [Exception("500 Internal Error"), "Success"]
        res = _call_with_retry(mock_client, "model", [])
        self.assertEqual(res, "Success")
        self.assertEqual(mock_client.chat.call_count, 2)
        print("[OK] Retried on 500 Error")
        
        # Case 3: Fail with 400 (Bad Request) - Should NOT retry
        mock_client.chat.side_effect = Exception("400 Bad Request")
        mock_client.chat.reset_mock()
        with self.assertRaises(Exception):
            _call_with_retry(mock_client, "model", [])
        self.assertEqual(mock_client.chat.call_count, 1)
        print("[OK] Did NOT retry on 400 Error")

if __name__ == '__main__':
    unittest.main()
