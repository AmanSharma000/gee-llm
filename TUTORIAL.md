# Geo-GEE-LLM: Complete Step-by-Step Tutorial

**A Natural Language Interface for Google Earth Engine Analysis**

---

## Table of Contents

1. [Introduction](#1-introduction)
2. [Architecture Overview](#2-architecture-overview)
3. [Setup & Installation](#3-setup--installation)
4. [Backend Components](#4-backend-components)
5. [Frontend Interface](#5-frontend-interface)
6. [Advanced Features](#6-advanced-features)
7. [Testing & Debugging](#7-testing--debugging)
8. [Deployment](#8-deployment)

---

## 1. Introduction

### 1.1 What is Geo-GEE-LLM?

Geo-GEE-LLM is an AI-powered geospatial analysis platform that allows users to perform Google Earth Engine (GEE) computations using natural language queries. Instead of writing complex GEE code, users can simply ask questions like:

- "What is the NDVI of Delhi for 2023?"
- "Compare water levels in Mumbai vs Chennai from 2020 to 2024"
- "Show me forest change in Western Ghats from 2015 to 2023"

### 1.2 Key Features

- **Natural Language Processing**: Convert plain English to executable GEE code
- **Retrieval-Augmented Generation (RAG)**: Context-aware code generation using examples
- **Intelligent Satellite Selection**: Automatically chooses best satellite (Sentinel-2, Landsat, MODIS)
- **Self-Correction**: Automatically fixes code errors with multiple retry attempts
- **Comparison Queries**: Compare regions or time periods side-by-side
- **Multi-Format Export**: Export results as CSV, JSON, or GeoJSON
- **Caching System**: Reduces API costs and improves response time

### 1.3 Technologies Used

- **Frontend**: Streamlit (Python web framework)
- **LLM**: Cohere API (text generation)
- **Geospatial**: Google Earth Engine Python API
- **Caching**: DiskCache
- **Data Processing**: Pandas, GeoPandas
- **Geometry**: Shapely, Fiona

---

## 2. Architecture Overview

### 2.1 System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                       USER INTERFACE                         │
│                      (Streamlit App)                         │
└─────────────────┬───────────────────────────────────────────┘
                  │
                  ├──────────► Query Input
                  │
┌─────────────────▼───────────────────────────────────────────┐
│                    QUERY PROCESSING                          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │ Comparison   │  │   Satellite  │  │   Geometry   │      │
│  │   Engine     │  │   Selector   │  │   Parser     │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
└─────────────────┬───────────────────────────────────────────┘
                  │
┌─────────────────▼───────────────────────────────────────────┐
│                      RAG PIPELINE                            │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │   Example    │──►│    Prompt    │──►│   Context    │      │
│  │  Retrieval   │  │   Builder    │  │  Enhancement │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
└─────────────────┬───────────────────────────────────────────┘
                  │
┌─────────────────▼───────────────────────────────────────────┐
│                     LLM GENERATION                           │
│                    (Cohere API)                              │
│                  Generates GEE Code                          │
└─────────────────┬───────────────────────────────────────────┘
                  │
┌─────────────────▼───────────────────────────────────────────┐
│                    CODE EXECUTION                            │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │  GEE Runner  │──►│Self-Corrector│──►│    Cache     │      │
│  │              │  │  (if error)   │  │   Manager    │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
└─────────────────┬───────────────────────────────────────────┘
                  │
┌─────────────────▼───────────────────────────────────────────┐
│                   RESULT VISUALIZATION                       │
│         Charts, Tables, Maps, Export Options                 │
└─────────────────────────────────────────────────────────────┘
```

### 2.2 Data Flow

1. **User Query** → Streamlit UI
2. **Query Processing** → Detect comparison, extract entities, select satellite
3. **RAG Retrieval** → Find similar examples from knowledge base
4. **Prompt Building** → Construct comprehensive prompt with rules + examples
5. **LLM Generation** → Cohere generates Python+GEE code
6. **Code Execution** → Execute code with Earth Engine
7. **Error Handling** → If error occurs, self-correct and retry
8. **Result Display** → Show charts, tables, and export options

---

## 3. Setup & Installation

### 3.1 Prerequisites

- Python 3.8 or higher
- Google Earth Engine account
- Cohere API key
- Git (for cloning repository)

### 3.2 Step-by-Step Installation

#### Step 1: Clone the Repository

```bash
git clone https://github.com/AmanSharma000/geo-gee-llm-adv.git
cd geo-gee-llm-adv
```

#### Step 2: Create Virtual Environment

```bash
# Windows
python -m venv .venv
.venv\Scripts\activate

# Linux/Mac
python3 -m venv .venv
source .venv/bin/activate
```

#### Step 3: Install Dependencies

```bash
pip install -r requirements.txt
```

**requirements.txt contents:**
```txt
streamlit
google-api-python-client
earthengine-api
cohere
pandas
geopandas
shapely
fiona
diskcache
python-dotenv
```

#### Step 4: Authenticate Google Earth Engine

```bash
earthengine authenticate
```

This will open a browser window. Sign in with your Google account and copy the authorization code.

#### Step 5: Configure API Keys

Create `.streamlit/secrets.toml`:

```toml
[secrets]
COHERE_API_KEY = "your-cohere-api-key-here"
```

Or set environment variable:

```bash
# Windows
set COHERE_API_KEY=your-api-key

# Linux/Mac
export COHERE_API_KEY=your-api-key
```

#### Step 6: Run the Application

```bash
streamlit run app.py
```

The app will open at `http://localhost:8501`

---

## 4. Backend Components

### 4.1 RAG Pipeline (`backend/rag/`)

The RAG (Retrieval-Augmented Generation) pipeline enhances LLM responses by providing relevant examples.

#### 4.1.1 Example Retriever (`example_retriever.py`)

**Purpose**: Find similar code examples from the knowledge base based on user query.

**Code:**
```python
import json
from pathlib import Path
from typing import List, Dict, Any

class ExampleRetriever:
    def __init__(self, examples_file: str = "backend/rag/examples.jsonl"):
        self.examples_file = Path(examples_file)
        self.examples = self._load_examples()
    
    def _load_examples(self) -> List[Dict[str, Any]]:
        """Load examples from JSONL file"""
        examples = []
        if not self.examples_file.exists():
            return examples
        
        with open(self.examples_file, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    examples.append(json.loads(line))
        
        return examples
    
    def retrieve_examples(self, query: str, top_k: int = 3) -> List[Dict]:
        """
        Retrieve most relevant examples based on query.
        Uses simple keyword matching.
        """
        query_lower = query.lower()
        scored_examples = []
        
        for example in self.examples:
            score = self._calculate_relevance(query_lower, example)
            scored_examples.append((score, example))
        
        # Sort by score and get top_k
        scored_examples.sort(reverse=True, key=lambda x: x[0])
        return [ex[1] for ex in scored_examples[:top_k]]
    
    def _calculate_relevance(self, query: str, example: Dict) -> float:
        """Calculate relevance score based on keyword matching"""
        score = 0.0
        example_query = example.get('query', '').lower()
        
        # Exact query match
        if query == example_query:
            score += 10.0
        
        # Check for common keywords
        query_words = set(query.split())
        example_words = set(example_query.split())
        common_words = query_words & example_words
        
        score += len(common_words) * 2.0
        
        # Boost for index names
        indices = ['ndvi', 'evi', 'savi', 'ndwi', 'mndwi', 'ui', 'bsi']
        for idx in indices:
            if idx in query and idx in example_query:
                score += 5.0
        
        return score
```

**How it works:**
1. Loads all examples from `examples.jsonl`
2. Scores each example based on keyword overlap with query
3. Returns top-K most relevant examples

#### 4.1.2 Prompt Builder (`prompt_builder.py`)

**Purpose**: Construct comprehensive prompts with instructions, examples, and rules.

**Key Code:**
```python
def build_prompt(query: str, context: str = "", satellite_info: Dict = None) -> str:
    """Build comprehensive prompt for LLM"""
    
    # Get relevant examples
    retriever = ExampleRetriever()
    examples = retriever.retrieve_examples(query, top_k=3)
    
    # Load example code
    examples_text = ""
    for ex in examples:
        code_file = f"backend/rag/{ex['code_file']}"
        if Path(code_file).exists():
            with open(code_file, 'r') as f:
                code = f.read()
            examples_text += f"\n## Example: {ex['query']}\n```python\n{code}\n```\n"
    
    # Build prompt
    prompt = f"""You are an expert Google Earth Engine developer.

USER QUERY: {query}

{context}

CRITICAL RULES:
- Use Earth Engine Python API syntax only
- ALWAYS use the custom India boundaries: ee.FeatureCollection("projects/ee-myresearch/assets/India_sorted")
- Filter by STATE, DISTRICT, or VILLAGE as appropriate
- Use server-side operations (ee.List.map()) instead of Python loops
- CONVERT PYTHON LISTS TO ee.List before calling .map()
  ❌ WRONG: years = range(2020, 2025); result = years.map(func)
  ✅ CORRECT: years = ee.List(list(range(2020, 2025))); result = years.map(func)
- Use .reduceRegion() for statistics, NEVER .sampleRectangle()
- Include proper error handling for empty collections
- Return results in JSON-serializable format

SATELLITE INFO:
{satellite_info if satellite_info else 'Auto-select based on query'}

RELEVANT EXAMPLES:
{examples_text}

Generate complete, executable Python code that accomplishes the query.
"""
    
    return prompt
```

**Critical Instructions in Prompt:**
- Server-side mapping (ee.List.map())
- Python list conversion to ee.List
- Error handling patterns
- Dataset specifications

### 4.2 LLM Client (`llm_client.py`)

**Purpose**: Interact with Cohere API to generate code.

**Code:**
```python
import cohere
import os
import time
from typing import Optional

class LLMClient:
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("COHERE_API_KEY")
        self.client = cohere.Client(self.api_key)
        self.model = "command-r-plus"
    
    def generate_code(self, prompt: str, temperature: float = 0.3) -> str:
        """
        Generate code using Cohere API
        
        Args:
            prompt: The prompt to send
            temperature: Lower = more deterministic (0.0-1.0)
        
        Returns:
            Generated code as string
        """
        try:
            response = self.client.chat(
                model=self.model,
                message=prompt,
                temperature=temperature,
                max_tokens=2000
            )
            
            return response.text
        
        except Exception as e:
            print(f"Error calling LLM: {e}")
            raise
    
    def generate_with_retry(self, prompt: str, max_retries: int = 3) -> str:
        """Generate with exponential backoff retry"""
        for attempt in range(max_retries):
            try:
                return self.generate_code(prompt)
            except Exception as e:
                if attempt == max_retries - 1:
                    raise
                wait_time = 2 ** attempt
                print(f"Retry {attempt + 1}/{max_retries} after {wait_time}s...")
                time.sleep(wait_time)
```

**Features:**
- Exponential backoff retry
- Configurable temperature
- Error handling

### 4.3 GEE Runner (`gee_runner.py`)

**Purpose**: Execute generated code safely with Earth Engine.

**Code:**
```python
import ee
import re
from typing import Any, Dict
from datetime import datetime

def run_gee_code(code: str, custom_geometry=None) -> Dict[str, Any]:
    """
    Execute Google Earth Engine code safely
    
    Args:
        code: Python code string to execute
        custom_geometry: Optional geometry to inject
    
    Returns:
        Dictionary with 'success', 'result', and optionally 'error'
    """
    # Safety checks
    forbidden_modules = ['os', 'subprocess', 'sys', 'eval', 'exec']
    for module in forbidden_modules:
        if f"import {module}" in code or f"from {module}" in code:
            return {
                'success': False,
                'error': f"Security violation: {module} module not allowed"
            }
    
    # Fix common LLM mistakes
    code = _fix_common_patterns(code)
    
    # Create execution environment
    exec_env = {
        "ee": ee,
        "datetime": datetime,
    }
    
    # Inject custom geometry if provided
    if custom_geometry:
        exec_env["geometry"] = custom_geometry
    
    # Add India boundaries
    exec_env["india_boundaries"] = ee.FeatureCollection(
        "projects/ee-myresearch/assets/India_sorted"
    )
    
    try:
        # Execute code
        exec(code, exec_env)
        
        # Extract result
        if 'result' in exec_env:
            return {
                'success': True,
                'result': exec_env['result']
            }
        else:
            return {
                'success': False,
                'error': "Code did not define 'result' variable"
            }
    
    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }


def _fix_common_patterns(code: str) -> str:
    """Fix common LLM code generation mistakes"""
    
    # Fix 1: Replace ee.Date.now() with Python datetime
    code = re.sub(
        r'ee\.Date\.now\(\)',
        'ee.Date(datetime.now().isoformat())',
        code
    )
    
    # Fix 2: Ensure proper geometry variable initialization
    if "geometry =" not in code and "custom_geometry" not in code:
        # Add fallback geometry if none defined
        pass  # Will be caught by exec_env injection
    
    return code
```

**Safety Features:**
- Forbidden module checking (prevents os, subprocess)
- Common pattern fixes (ee.Date.now())
- Controlled execution environment

### 4.4 Self-Corrector (`self_corrector.py`)

**Purpose**: Automatically fix code errors and retry execution.

**Code:**
```python
from typing import Dict, Any
from backend.error_analyzer import ErrorAnalyzer
from backend.llm_client import LLMClient
from backend.gee_runner import run_gee_code

class SelfCorrector:
    def __init__(self, max_attempts: int = 3):
        self.max_attempts = max_attempts
        self.error_analyzer = ErrorAnalyzer()
        self.llm_client = LLMClient()
    
    def execute_with_retry(
        self, 
        code: str, 
        query: str, 
        attempt: int = 1,
        custom_geometry=None
    ) -> Dict[str, Any]:
        """
        Execute code with automatic error correction
        
        Args:
            code: Generated code string
            query: Original user query
            attempt: Current attempt number
            custom_geometry: Optional geometry
        
        Returns:
            Execution result dictionary
        """
        # Execute code
        result = run_gee_code(code, custom_geometry)
        
        if result['success']:
            return result
        
        # If failed and we have retries left
        if attempt < self.max_attempts:
            print(f"Attempt {attempt} failed: {result['error']}")
            print("Attempting automatic correction...")
            
            # Analyze error
            error_analysis = self.error_analyzer.analyze_error(
                result['error'], 
                code
            )
            
            # Generate correction prompt
            correction_prompt = f"""The following code failed with an error.

ORIGINAL QUERY: {query}

GENERATED CODE:
```python
{code}
```

ERROR:
{result['error']}

ERROR ANALYSIS:
{error_analysis['suggestion']}

Please fix the code to resolve this error. Return ONLY the corrected Python code.
"""
            
            # Get corrected code
            try:
                corrected_code = self.llm_client.generate_code(correction_prompt)
                corrected_code = self._extract_code(corrected_code)
                
                # Retry with corrected code
                return self.execute_with_retry(
                    corrected_code, 
                    query, 
                    attempt + 1, 
                    custom_geometry
                )
            
            except Exception as e:
                return {
                    'success': False,
                    'error': f"Self-correction failed: {str(e)}"
                }
        
        # Max retries exhausted
        return result
    
    def _extract_code(self, llm_response: str) -> str:
        """Extract Python code from LLM response"""
        import re
        
        # Try to find code block
        code_match = re.search(r'```python\n(.*?)\n```', llm_response, re.DOTALL)
        if code_match:
            return code_match.group(1)
        
        # If no code block, return as-is
        return llm_response
```

**Self-Correction Flow:**
1. Execute code
2. If error → Analyze error type
3. Generate correction prompt with error details
4. Get corrected code from LLM
5. Retry execution (up to max_attempts)

### 4.5 Error Analyzer (`error_analyzer.py`)

**Purpose**: Identify error patterns and suggest fixes.

**Code:**
```python
import re
from typing import Dict, Any

class ErrorAnalyzer:
    def __init__(self):
        self.error_patterns = [
            {
                'pattern': r"'list' object has no attribute 'map'",
                'type': 'Python_ListMapError',
                'suggestion': 'Convert Python list to ee.List: ee.List(your_list).map(...)',
                'fix_strategy': 'wrap_list_in_ee_list'
            },
            {
                'pattern': r"Computation_TimeoutError",
                'type': 'GEE_Timeout',
                'suggestion': 'Reduce area, increase scale, or use bestEffort=True',
                'fix_strategy': 'optimize_computation'
            },
            {
                'pattern': r"pattern.*not found",
                'type': 'GEE_NotFound',
                'suggestion': 'Check dataset name and filter conditions',
                'fix_strategy': 'verify_dataset'
            },
            {
                'pattern': r"Empty collection",
                'type': 'EmptyCollection',
                'suggestion': 'Check date range and region bounds',
                'fix_strategy': 'adjust_filters'
            }
        ]
    
    def analyze_error(self, error_message: str, code: str = "") -> Dict[str, Any]:
        """
        Analyze error and return suggested fix
        
        Returns:
            {
                'error_type': str,
                'suggestion': str,
                'fix_strategy': str
            }
        """
        error_lower = error_message.lower()
        
        # Check each pattern
        for pattern_info in self.error_patterns:
            if re.search(pattern_info['pattern'], error_message, re.IGNORECASE):
                return {
                    'error_type': pattern_info['type'],
                    'suggestion': pattern_info['suggestion'],
                    'fix_strategy': pattern_info['fix_strategy']
                }
        
        # Unknown error
        return {
            'error_type': 'Unknown',
            'suggestion': 'Review code syntax and GEE API usage',
            'fix_strategy': 'manual_review'
        }
```

**Error Patterns Detected:**
- Python list.map() error
- GEE timeout errors
- Dataset not found
- Empty collections

### 4.6 Comparison Engine (`comparison_engine.py`)

**Purpose**: Handle comparison queries (region vs region, temporal comparisons).

**Key Code:**
```python
import re
from typing import Optional, Dict, Any, List

class ComparisonEngine:
    def __init__(self):
        self.comparison_patterns = [
            r'compare\s+(.+?)\s+vs\s+(.+?)(?:\s+for|\s+from|$)',
            r'(.+?)\s+vs\s+(.+?)\s+comparison',
        ]
    
    def is_comparison_query(self, query: str) -> bool:
        """Check if query is a comparison"""
        query_lower = query.lower()
        keywords = ['compare', 'vs', 'versus', 'comparison']
        return any(kw in query_lower for kw in keywords)
    
    def parse_comparison_entities(self, query: str) -> Optional[Dict[str, Any]]:
        """
        Parse comparison query to extract entities
        
        Returns:
            {
                'type': 'region' or 'temporal',
                'entity1': str,
                'entity2': str,
                'index': str (e.g., 'ndvi'),
                'start_year': int,
                'end_year': int,
                'satellite': str
            }
        """
        query_lower = query.lower()
        
        # Try to match pattern
        for pattern in self.comparison_patterns:
            match = re.search(pattern, query_lower)
            if match:
                entity1 = self._clean_entity(match.group(1))
                entity2 = self._clean_entity(match.group(2))
                
                # Extract index (ndvi, evi, etc.)
                index = self._extract_index(query_lower)
                
                # Extract year range
                year_range = self._extract_year_range(query_lower)
                start_year, end_year = year_range if year_range else (None, None)
                
                # Extract satellite preference
                satellite = self._extract_satellite(query_lower)
                
                return {
                    'type': 'region',
                    'entity1': entity1,
                    'entity2': entity2,
                    'index': index,
                    'start_year': start_year,
                    'end_year': end_year,
                    'satellite': satellite
                }
        
        return None
    
    def _clean_entity(self, entity: str) -> str:
        """Clean entity name"""
        # Remove common words
        stop_words = ['the', 'of', 'in', 'for', 'using', 'with']
        words = entity.split()
        words = [w for w in words if w not in stop_words]
        return ' '.join(words).strip()
    
    def _extract_index(self, query: str) -> str:
        """Extract vegetation/water index from query"""
        indices = ['ndvi', 'evi', 'savi', 'ndwi', 'mndwi', 'ui', 'bsi', 'nbr', 'ndmi']
        for idx in indices:
            if idx in query:
                return idx
        return 'ndvi'  # Default
    
    def _extract_year_range(self, query: str) -> Optional[tuple]:
        """Extract year range like 'from 2020 to 2024'"""
        pattern = r'from\s+(\d{4})\s+to\s+(\d{4})'
        match = re.search(pattern, query)
        if match:
            return (int(match.group(1)), int(match.group(2)))
        return None
    
    def _extract_satellite(self, query: str) -> Optional[str]:
        """Extract satellite preference"""
        if 'sentinel' in query or 's2' in query:
            return 'sentinel-2'
        elif 'landsat' in query or 'l8' in query:
            return 'landsat-8'
        elif 'modis' in query:
            return 'modis'
        return None
```

**Comparison Flow:**
1. Detect comparison query
2. Parse entities (delhi, mumbai)
3. Extract parameters (index, years, satellite)
4. Generate separate queries for each entity
5. Execute both in parallel
6. Display results side-by-side

### 4.7 Cache Manager (`cache_manager.py`)

**Purpose**: Cache GEE and LLM responses to reduce costs and latency.

**Code:**
```python
import diskcache
import hashlib
import json
from pathlib import Path
from typing import Any, Optional

class CacheManager:
    def __init__(self, cache_dir: str = "data/cache"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # Separate caches for different types
        self.gee_cache = diskcache.Cache(str(self.cache_dir / "gee"))
        self.llm_cache = diskcache.Cache(str(self.cache_dir / "llm"))
    
    def _hash_key(self, key: str) -> str:
        """Create SHA256 hash of key"""
        return hashlib.sha256(key.encode()).hexdigest()
    
    def get_gee_result(self, code: str) -> Optional[Any]:
        """Get cached GEE execution result"""
        key = self._hash_key(code)
        return self.gee_cache.get(key)
    
    def set_gee_result(self, code: str, result: Any, ttl: int = 86400):
        """
        Cache GEE result
        
        Args:
            code: The executed code
            result: The result to cache
            ttl: Time to live in seconds (default: 24 hours)
        """
        key = self._hash_key(code)
        self.gee_cache.set(key, result, expire=ttl)
    
    def get_llm_response(self, prompt: str) -> Optional[str]:
        """Get cached LLM response"""
        key = self._hash_key(prompt)
        return self.llm_cache.get(key)
    
    def set_llm_response(self, prompt: str, response: str, ttl: int = 604800):
        """
        Cache LLM response
        
        Args:
            prompt: The input prompt
            response: The LLM response
            ttl: Time to live in seconds (default: 7 days)
        """
        key = self._hash_key(prompt)
        self.llm_cache.set(key, response, expire=ttl)
    
    def clear_all(self):
        """Clear all caches"""
        self.gee_cache.clear()
        self.llm_cache.clear()
    
    def get_stats(self) -> dict:
        """Get cache statistics"""
        return {
            'gee_cache_size': len(self.gee_cache),
            'llm_cache_size': len(self.llm_cache),
            'total_size_mb': (self.gee_cache.volume() + self.llm_cache.volume()) / 1024 / 1024
        }
```

**Caching Strategy:**
- **GEE Results**: 24-hour TTL (data might change)
- **LLM Responses**: 7-day TTL (code patterns stable)
- **Key Hashing**: SHA256 for security and consistency

---

## 5. Frontend Interface

### 5.1 Streamlit App (`app.py`)

**Main Application Structure:**

```python
import streamlit as st
import ee
from backend.engine import QueryEngine
from backend.comparison_engine import ComparisonEngine

# Initialize Earth Engine
try:
    ee.Initialize()
except:
    ee.Authenticate()
    ee.Initialize()

# Page config
st.set_page_config(
    page_title="Geo-GEE-LLM",
    page_icon="🌍",
    layout="wide"
)

# Title
st.title("🌍 GeoAI")
st.write("Type a geospatial query that can be answered using spatial datasets.")

# Examples
with st.expander("📝 Example Queries"):
    st.markdown("""
    - `ndvi index of gurugram city for 5 years with bar chart`
    - `evi of jaipur city using sentinel-2 for 2022`
    - `compare ndvi of delhi vs mumbai for 2023`
    - `savi trend of haryana from 2020 to 2025`
    - `mndwi of jaipur city for 2024`
    """)

# Query input
query = st.text_input("Enter your query:", placeholder="compare ndvi of delhi vs mumbai from 2022 to 2024")

if st.button("🚀 Analyze") and query:
    # Initialize engines
    query_engine = QueryEngine()
    comparison_engine = ComparisonEngine()
    
    # Check if comparison query
    if comparison_engine.is_comparison_query(query):
        handle_comparison_query(query, comparison_engine, query_engine)
    else:
        handle_single_query(query, query_engine)


def handle_single_query(query: str, engine: QueryEngine):
    """Handle single region query"""
    with st.spinner("Processing query..."):
        result = engine.process_query(query)
        
        if result['success']:
            # Display results
            st.success("✅ Analysis Complete")
            
            # Show data table
            if 'result' in result:
                st.subheader("📊 Results")
                st.json(result['result'])
            
            # Show chart if applicable
            if 'chart_data' in result:
                st.line_chart(result['chart_data'])
            
            # Show code
            with st.expander("🧠 View Code"):
                st.code(result['code'], language='python')
            
            # Export options
            st.download_button(
                "📥 Export as JSON",
                data=json.dumps(result['result'], indent=2),
                file_name="gee_result.json",
                mime="application/json"
            )
        else:
            st.error(f"❌ Error: {result['error']}")


def handle_comparison_query(query: str, comp_engine: ComparisonEngine, query_engine: QueryEngine):
    """Handle comparison query"""
    # Parse comparison
    comparison = comp_engine.parse_comparison_entities(query)
    
    if not comparison:
        st.error("Could not parse comparison query")
        return
    
    st.info(f"Comparing: {comparison['entity1']} vs {comparison['entity2']}")
    
    # Create two columns
    col1, col2 = st.columns(2)
    
    # Process entity 1
    with col1:
        st.subheader(f"📊 {comparison['entity1'].title()}")
        query1 = f"{comparison['index']} of {comparison['entity1']} from {comparison['start_year']} to {comparison['end_year']}"
        result1 = query_engine.process_query(query1)
        
        if result1['success']:
            st.line_chart(result1['chart_data'])
            with st.expander("🧠 View Code"):
                st.code(result1['code'], language='python')
    
    # Process entity 2
    with col2:
        st.subheader(f"📊 {comparison['entity2'].title()}")
        query2 = f"{comparison['index']} of {comparison['entity2']} from {comparison['start_year']} to {comparison['end_year']}"
        result2 = query_engine.process_query(query2)
        
        if result2['success']:
            st.line_chart(result2['chart_data'])
            with st.expander("🧠 View Code"):
                st.code(result2['code'], language='python')
    
    # Comparison statistics
    st.subheader("📈 Comparison Analysis")
    stats_col1, stats_col2, stats_col3, stats_col4 = st.columns(4)
    
    # Calculate stats
    avg1 = calculate_average(result1['result'])
    avg2 = calculate_average(result2['result'])
    
    with stats_col1:
        st.metric(f"Avg {comparison['entity1'].title()}", f"{avg1:.4f}")
    with stats_col2:
        st.metric(f"Avg {comparison['entity2'].title()}", f"{avg2:.4f}")
    with stats_col3:
        st.metric("Difference", f"{abs(avg1 - avg2):.4f}")
    with stats_col4:
        change_pct = ((avg1 - avg2) / avg2) * 100 if avg2 != 0 else 0
        st.metric("Change %", f"{abs(change_pct):.2f}%")
```

### 5.2 UI Components

**Key Features:**
- **Query Input**: Text input with placeholder examples
- **Loading Spinner**: Visual feedback during processing
- **Result Display**: Tables, charts, and metrics
- **Code Viewer**: Collapsible code display
- **Export Options**: Download as JSON, CSV, GeoJSON
- **Comparison View**: Side-by-side results with statistics

---

## 6. Advanced Features

### 6.1 Satellite Selection

**Automatic Satellite Selection Based on Query:**

```python
class SatelliteSelector:
    def __init__(self):
        self.satellites = {
            'sentinel-2': {
                'dataset': 'COPERNICUS/S2_SR_HARMONIZED',
                'resolution': 10,
                'bands': {'NIR': 'B8', 'RED': 'B4', 'GREEN': 'B3', 'BLUE': 'B2'},
                'best_for': ['ndvi', 'evi', 'ndwi', 'high-resolution']
            },
            'landsat-8': {
                'dataset': 'LANDSAT/LC08/C02/T1_L2',
                'resolution': 30,
                'bands': {'NIR': 'SR_B5', 'RED': 'SR_B4', 'SWIR1': 'SR_B6'},
                'best_for': ['savi', 'ui', 'bsi', 'long-term-analysis']
            },
            'modis': {
                'dataset': 'MODIS/006/MOD13A1',
                'resolution': 500,
                'bands': {'NDVI': 'NDVI', 'EVI': 'EVI'},
                'best_for': ['large-area', 'frequent-monitoring', 'state-level']
            }
        }
    
    def select_satellite(self, query: str) -> dict:
        """Select best satellite based on query keywords"""
        query_lower = query.lower()
        
        # Explicit satellite mention
        if 'sentinel' in query_lower or 's2' in query_lower:
            return self.satellites['sentinel-2']
        elif 'landsat' in query_lower:
            return self.satellites['landsat-8']
        elif 'modis' in query_lower:
            return self.satellites['modis']
        
        # Index-based selection
        if any(idx in query_lower for idx in ['ndvi', 'evi', 'ndwi']):
            return self.satellites['sentinel-2']  # High resolution for vegetation
        elif any(idx in query_lower for idx in ['ui', 'bsi']):
            return self.satellites['landsat-8']  # Good for urban/soil
        
        # Area-based selection
        if any(word in query_lower for word in ['state', 'country', 'large', 'india']):
            return self.satellites['modis']  # Fast for large areas
        
        # Default
        return self.satellites['sentinel-2']
```

### 6.2 Geometry Parsing

**Support for Multiple Geometry Formats:**

```python
import geopandas as gpd
from shapely.geometry import shape
import json

class GeometryParser:
    def parse_geometry(self, file_path: str, file_type: str) -> ee.Geometry:
        """
        Parse geometry from various formats
        
        Supports:
        - GeoJSON (.geojson, .json)
        - KML (.kml)
        - Shapefile (.shp)
        """
        if file_type in ['geojson', 'json']:
            return self._parse_geojson(file_path)
        elif file_type == 'kml':
            return self._parse_kml(file_path)
        elif file_type == 'shp':
            return self._parse_shapefile(file_path)
        else:
            raise ValueError(f"Unsupported file type: {file_type}")
    
    def _parse_geojson(self, file_path: str) -> ee.Geometry:
        """Parse GeoJSON file"""
        with open(file_path) as f:
            geojson = json.load(f)
        
        # Convert to ee.Geometry
        if geojson['type'] == 'FeatureCollection':
            features = geojson['features']
            geometries = [ee.Geometry(f['geometry']) for f in features]
            return ee.Geometry.MultiPolygon(geometries)
        else:
            return ee.Geometry(geojson['geometry'])
    
    def _parse_kml(self, file_path: str) -> ee.Geometry:
        """Parse KML file using geopandas"""
        gdf = gpd.read_file(file_path, driver='KML')
        geom = gdf.geometry.unary_union
        return ee.Geometry(json.loads(gpd.GeoSeries([geom]).to_json())['features'][0]['geometry'])
    
    def _parse_shapefile(self, file_path: str) -> ee.Geometry:
        """Parse Shapefile"""
        gdf = gpd.read_file(file_path)
        geom = gdf.geometry.unary_union
        return ee.Geometry(json.loads(gpd.GeoSeries([geom]).to_json())['features'][0]['geometry'])
```

### 6.3 Export Formats

**Export handler supporting multiple formats:**

```python
import pandas as pd
import json

class ExportHandler:
    def export_to_csv(self, data: list, filename: str = "result.csv"):
        """Export results to CSV"""
        df = pd.DataFrame(data)
        df.to_csv(filename, index=False)
        return filename
    
    def export_to_json(self, data: any, filename: str = "result.json"):
        """Export results to JSON"""
        with open(filename, 'w') as f:
            json.dump(data, f, indent=2)
        return filename
    
    def export_to_geojson(self, data: list, geometry_field: str = "geometry"):
        """Export results to GeoJSON"""
        features = []
        for item in data:
            feature = {
                'type': 'Feature',
                'geometry': item[geometry_field],
                'properties': {k: v for k, v in item.items() if k != geometry_field}
            }
            features.append(feature)
        
        geojson = {
            'type': 'FeatureCollection',
            'features': features
        }
        
        return json.dumps(geojson, indent=2)
```

---

## 7. Testing & Debugging

### 7.1 Unit Tests

**Example test for RAG retrieval:**

```python
# tests/test_example_retriever.py
import pytest
from backend.rag.example_retriever import ExampleRetriever

def test_retrieve_ndvi_examples():
    retriever = ExampleRetriever()
    examples = retriever.retrieve_examples("ndvi of delhi", top_k=3)
    
    assert len(examples) <= 3
    assert all('query' in ex for ex in examples)
    assert any('ndvi' in ex['query'].lower() for ex in examples)

def test_retrieve_comparison_examples():
    retriever = ExampleRetriever()
    examples = retriever.retrieve_examples("compare ndvi delhi vs mumbai", top_k=3)
    
    assert len(examples) > 0
    # Should retrieve comparison-related examples
    assert any('compar' in ex['query'].lower() for ex in examples)
```

**Run tests:**
```bash
pytest tests/ -v
```

### 7.2 Debugging Tips

**Enable detailed logging:**

```python
import logging

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/debug.log'),
        logging.StreamHandler()
    ]
)
```

**Common Issues and Solutions:**

| Issue | Cause | Solution |
|-------|-------|----------|
| `'list' has no attribute 'map'` | Python list instead of ee.List | Wrap: `ee.List(your_list).map(...)` |
| `Computation timed out` | Query too large/complex | Increase scale, add bestEffort=True |
| `Empty collection` | No data for date/region | Check date range and bounds |
| `Authentication failed` | GEE not authenticated | Run `earthengine authenticate` |

### 7.3 Cache Clearing

**Clear cache when needed:**

```python
# clear_cache.py
from backend.cache_manager import CacheManager

cache = CacheManager()
cache.clear_all()
print("Cache cleared!")
```

Or manually:
```bash
# Windows
rmdir /s /q data\cache
mkdir data\cache

# Linux/Mac
rm -rf data/cache
mkdir -p data/cache
```

---

## 8. Deployment

### 8.1 Local Deployment

Already covered in Setup section. Quick recap:

```bash
streamlit run app.py
```

### 8.2 Cloud Deployment (Streamlit Cloud)

**Step 1: Prepare Repository**

Ensure you have:
- `requirements.txt`
- `.streamlit/secrets.toml` (in .gitignore)
- `app.py`

**Step 2: Push to GitHub**

```bash
git add .
git commit -m "Prepare for deployment"
git push origin main
```

**Step 3: Deploy on Streamlit Cloud**

1. Go to [share.streamlit.io](https://share.streamlit.io)
2. Connect GitHub account
3. Select repository: `your-username/geo-gee-llm-adv`
4. Main file: `app.py`
5. Add secrets in dashboard:
   ```toml
   [secrets]
   COHERE_API_KEY = "your-key"
   ```
6. Click "Deploy"

**Step 4: Configure GEE Authentication**

For cloud deployment, you need to use a service account:

```python
# In app.py
import ee
import json

# Load service account credentials
service_account = 'your-service-account@your-project.iam.gserviceaccount.com'
credentials = ee.ServiceAccountCredentials(service_account, 'privatekey.json')
ee.Initialize(credentials)
```

### 8.3 Docker Deployment

**Dockerfile:**

```dockerfile
FROM python:3.9-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    libgdal-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Expose port
EXPOSE 8501

# Health check
HEALTHCHECK CMD curl --fail http://localhost:8501/_stcore/health

# Run app
CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
```

**Build and run:**

```bash
docker build -t geo-gee-llm .
docker run -p 8501:8501 \
  -e COHERE_API_KEY=your-key \
  -v $(pwd)/data:/app/data \
  geo-gee-llm
```

---

## Appendix

### A. Complete Code Example

**Full working example for NDVI calculation:**

```python
import ee
from datetime import datetime

# Initialize Earth Engine
ee.Initialize()

# Load custom India boundaries
india_boundaries = ee.FeatureCollection("projects/ee-myresearch/assets/India_sorted")

# Filter for Delhi
delhi = india_boundaries.filter(ee.Filter.eq('STATE', 'DELHI')).first()
geometry = delhi.geometry()

# Define year range
years = ee.List([2020, 2021, 2022, 2023, 2024])

def compute_yearly_ndvi(year):
    """Compute mean NDVI for a single year"""
    year = ee.Number(year)
    start = ee.Date.fromYMD(year, 1, 1)
    end = ee.Date.fromYMD(year, 12, 31)
    
    # Load Sentinel-2 data
    s2 = ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED') \
        .filterDate(start, end) \
        .filterBounds(geometry) \
        .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 20))
    
    # Calculate NDVI
    def add_ndvi(img):
        ndvi = img.normalizedDifference(['B8', 'B4']).rename('NDVI')
        return img.addBands(ndvi)
    
    s2_ndvi = s2.map(add_ndvi)
    median = s2_ndvi.median()
    
    # Calculate mean NDVI over region
    stats = median.select('NDVI').reduceRegion(
        reducer=ee.Reducer.mean(),
        geometry=geometry,
        scale=10,
        bestEffort=True,
        maxPixels=1e13
    )
    
    return ee.Feature(None, {
        'year': year,
        'NDVI': stats.get('NDVI')
    })

# Server-side mapping
result_fc = ee.FeatureCollection(years.map(compute_yearly_ndvi))

# Get results
result = result_fc.getInfo()["features"]
result = [
    {
        'year': f['properties']['year'],
        'ndvi': round(f['properties']['NDVI'], 4)
    } 
    for f in result
]

print(result)
```

### B. Common Indices Formulas

| Index | Formula | Purpose |
|-------|---------|---------|
| NDVI | (NIR - RED) / (NIR + RED) | Vegetation health |
| EVI | 2.5 × ((NIR - RED) / (NIR + 6×RED - 7.5×BLUE + 1)) | Enhanced vegetation |
| SAVI | ((NIR - RED) / (NIR + RED + L)) × (1 + L), L=0.5 | Soil-adjusted vegetation |
| NDWI | (GREEN - NIR) / (GREEN + NIR) | Water bodies |
| MNDWI | (GREEN - SWIR1) / (GREEN + SWIR1) | Modified water index |
| UI | (SWIR2 - NIR) / (SWIR2 + NIR) | Urban areas |
| BSI | ((RED + SWIR) - (NIR + BLUE)) / ((RED + SWIR) + (NIR + BLUE)) | Bare soil |

### C. Dataset Reference

**Sentinel-2:**
- Dataset: `COPERNICUS/S2_SR_HARMONIZED`
- Resolution: 10m
- Bands: B2 (Blue), B3 (Green), B4 (Red), B8 (NIR)
- Temporal: 5-day revisit

**Landsat 8:**
- Dataset: `LANDSAT/LC08/C02/T1_L2`
- Resolution: 30m
- Bands: SR_B2 (Blue), SR_B4 (Red), SR_B5 (NIR), SR_B6 (SWIR1)
- Temporal: 16-day revisit

**MODIS:**
- Dataset: `MODIS/006/MOD13A1`
- Resolution: 500m
- Bands: NDVI, EVI (pre-computed)
- Temporal: 16-day composite

---

## Conclusion

This tutorial covered the complete Geo-GEE-LLM system from architecture to deployment. Key takeaways:

1. **RAG Pipeline**: Retrieves relevant examples to improve LLM accuracy
2. **Self-Correction**: Automatically fixes common coding errors
3. **Comparison Engine**: Handles complex comparative analyses
4. **Caching**: Reduces costs and improves performance
5. **Modular Design**: Easy to extend and maintain

**Next Steps:**
- Add more examples to RAG knowledge base
- Implement user authentication
- Add support for custom datasets
- Create API endpoints for programmatic access

**Resources:**
- [Google Earth Engine Docs](https://developers.google.com/earth-engine)
- [Cohere API Docs](https://docs.cohere.com)
- [Streamlit Docs](https://docs.streamlit.io)

---

**Created by**: Aman Sharma  
**Version**: 2.0  
**Last Updated**: November 2025
