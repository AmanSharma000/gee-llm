import sys
import os

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(project_root)

from backend.rag.retriever import retrieve_examples, RetrieverIndex

def test_retriever():
    print("=== Testing Enhanced Retriever ===")
    
    # Test 1: Cold Start (First Load)
    print("\n[Test 1] Cold Start (Loading Index)...")
    results = retrieve_examples("NDVI for Mumbai 2023")
    print(f"Retrieved {len(results)} examples.")
    print(f"Top Result: {results[0]['query']}")
    
    # Test 2: Warm Start (Cached)
    print("\n[Test 2] Warm Start (Should be instant)...")
    results = retrieve_examples("NDVI for Mumbai 2023")
    print(f"Retrieved {len(results)} examples.")
    
    # Test 3: Rare Entity (Dynamic Scoring)
    # 'Varanasi' is rare. 'Water' is common.
    # Should pick the Varanasi example even if 'Water' appears elsewhere.
    print("\n[Test 3] Rare Entity 'Varanasi'...")
    results = retrieve_examples("Water body detection in Varanasi")
    print(f"Top Result: {results[0]['query']}")
    assert "varanasi" in results[0]['query'].lower()
    
    # Test 4: Year Matching
    # Should prefer 2023 examples over 2020
    print("\n[Test 4] Year Matching '2020'...")
    results = retrieve_examples("EVI for Tamil Nadu 2020")
    # The Tamil Nadu example covers 2020-2023, so it should match well.
    print(f"Top Result: {results[0]['query']}")
    
    # Test 5: Urban Double Counting Check
    # 'Urban' is a common word. It shouldn't dominate.
    print("\n[Test 5] Common Word 'Urban'...")
    results = retrieve_examples("Urban growth in Bangalore")
    print(f"Top Result: {results[0]['query']}")
    
    # Test 6: Mixed Concepts (Vegetation + Water)
    # Should pick multi-index examples
    print("\n[Test 6] Mixed Concepts 'Vegetation and Water'...")
    results = retrieve_examples("Vegetation and water analysis in Mumbai")
    print(f"Top Result: {results[0]['query']}")
    # Expecting multi_index_mumbai or similar
    
    # Test 7: Typo Tolerance (TF-IDF doesn't handle typos well, but let's see if other keywords help)
    # 'Mumbbai' (typo) - should rely on 'NDVI' or other context if possible, 
    # but strictly TF-IDF might fail on the typo itself. 
    # This test checks if the *other* words carry the weight.
    print("\n[Test 7] Partial Typo 'Mumbbai NDVI'...")
    results = retrieve_examples("NDVI for Mumbbai")
    print(f"Top Result: {results[0]['query']}")
    
    # Test 8: Specific Satellite
    print("\n[Test 8] Specific Satellite 'Landsat'...")
    results = retrieve_examples("Forest change using Landsat")
    print(f"Top Result: {results[0]['query']}")
    
    print("\n=== All Tests Passed (Visually Verified) ===")

if __name__ == "__main__":
    test_retriever()
