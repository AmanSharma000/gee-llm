import unittest
import sys
import os

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from backend.comparison_engine import ComparisonEngine

class TestComparisonParsing(unittest.TestCase):

    def setUp(self):
        self.engine = ComparisonEngine()

    def test_range_parsing_current_behavior(self):
        """Test how the engine currently parses a range query."""
        query = "compare ndvi of delhi vs mumbai from 2020 to 2025"
        result = self.engine.parse_comparison_entities(query)
        
        print(f"\nQuery: {query}")
        print(f"Parsed: {result}")
        
        # Currently, it likely extracts just one year or fails to capture the range
        # We want to see what it does now
        if result:
            print(f"Extracted Year: {result.get('year')}")

    def test_create_queries(self):
        """Test query generation."""
        # Simulate what we WANT to happen
        info = {
            'type': 'region',
            'entity1': 'Delhi',
            'entity2': 'Mumbai',
            'index': 'NDVI',
            'start_year': 2020,
            'end_year': 2025,
            'satellite': 'Sentinel-2'
        }
        
        # This will fail/behave wrongly until we update the method, 
        # but let's see what the CURRENT method does with extra keys (it should ignore them)
        q1, q2 = self.engine.create_comparison_queries(info)
        print(f"\nGenerated Queries (with hypothetical start/end keys):")
        print(f"Q1: {q1}")
        print(f"Q2: {q2}")

if __name__ == '__main__':
    unittest.main()
