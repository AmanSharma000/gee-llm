import json
import os
import re
import time
import math
from collections import Counter
from typing import List, Dict, Set, Tuple
from ..logging_config import setup_logger, log_with_context

logger = setup_logger(__name__)

# -----------------------------------------------------------------------------
# CONSTANTS & STOPWORDS
# -----------------------------------------------------------------------------
STOPWORDS = {
    "the", "a", "an", "in", "on", "at", "for", "to", "of", "and", "or", "with",
    "by", "from", "using", "use", "calculate", "compute", "get", "find", "show",
    "map", "trend", "analysis", "monitoring", "detection", "change", "over",
    "between", "vs", "versus", "year", "years", "monthly", "daily", "annual",
    "time", "series", "data", "code", "python", "gee", "google", "earth", "engine"
}

class RetrieverIndex:
    """
    Singleton-style index for RAG examples.
    Handles loading, caching, and TF-IDF statistics.
    """
    _instance = None

    def __init__(self):
        self.examples: List[Dict] = []
        self.idf: Dict[str, float] = {}
        self.corpus_size = 0
        self.is_loaded = False

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def load(self):
        """Load examples and precompute TF-IDF stats if not already loaded."""
        if self.is_loaded:
            return

        start_time = time.time()
        
        # 1. Load Examples
        path = os.path.join(os.path.dirname(__file__), "examples.jsonl")
        loaded_examples = []
        
        try:
            with open(path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    ex = json.loads(line)
                    
                    # Load code snippet
                    snippet_path = os.path.join(os.path.dirname(__file__), ex["code_file"])
                    with open(snippet_path, "r", encoding="utf-8") as code_f:
                        ex["code"] = code_f.read()
                    
                    # Precompute tokens
                    text = (ex["query"] + " " + ex["description"]).lower()
                    tokens = self._tokenize(text)
                    ex["tokens"] = tokens
                    ex["tf"] = self._compute_tf(tokens)
                    
                    # Precompute years
                    ex["years"] = set(re.findall(r"\b(19[0-9]{2}|20[0-9]{2})\b", ex["query"]))
                    
                    loaded_examples.append(ex)
        except Exception as e:
            logger.error(f"Failed to load examples: {e}")
            raise

        self.examples = loaded_examples
        self.corpus_size = len(loaded_examples)
        
        # 2. Compute IDF
        self._compute_idf()
        
        self.is_loaded = True
        duration = time.time() - start_time
        logger.info(f"RetrieverIndex loaded {self.corpus_size} examples in {duration:.4f}s")

    def _tokenize(self, text: str) -> List[str]:
        """Simple tokenizer: lowercase, strip punctuation, remove stopwords."""
        # Replace punctuation with space
        text = re.sub(r'[^\w\s]', ' ', text)
        tokens = text.split()
        return [t for t in tokens if t not in STOPWORDS and len(t) > 1]

    def _compute_tf(self, tokens: List[str]) -> Dict[str, float]:
        """Compute Term Frequency (TF) for a document."""
        tf = Counter(tokens)
        total = len(tokens)
        return {t: count / total for t, count in tf.items()}

    def _compute_idf(self):
        """Compute Inverse Document Frequency (IDF) for the corpus."""
        doc_counts = Counter()
        for ex in self.examples:
            unique_tokens = set(ex["tokens"])
            doc_counts.update(unique_tokens)
        
        self.idf = {}
        for token, count in doc_counts.items():
            # IDF = log(N / (df + 1))
            self.idf[token] = math.log(self.corpus_size / (count + 1)) + 1

    def score(self, query: str, ex: Dict) -> float:
        """
        Score an example against a query using TF-IDF + Heuristics.
        """
        query_tokens = self._tokenize(query.lower())
        score = 0.0
        
        # 1. TF-IDF Score
        # Sum of (TF in doc * IDF) for matching query terms
        for token in query_tokens:
            if token in ex["tf"]:
                # TF-IDF match
                tf_val = ex["tf"][token]
                idf_val = self.idf.get(token, 0)
                score += (tf_val * idf_val) * 10.0  # Scale up for visibility
        
        # 2. Year Boosting (Critical for temporal queries)
        query_years = set(re.findall(r"\b(19[0-9]{2}|20[0-9]{2})\b", query))
        shared_years = query_years.intersection(ex["years"])
        score += len(shared_years) * 2.0  # +2.0 per matched year
        
        # 3. Exact Phrase Bonus (Optional but helpful)
        # If the exact query structure matches, give a small boost
        # (Skipping for now to keep it simple, TF-IDF handles most)

        return score

# -----------------------------------------------------------------------------
# PUBLIC API
# -----------------------------------------------------------------------------

def retrieve_examples(query: str, k: int = 2) -> List[Dict]:
    """
    Retrieve top-k examples using TF-IDF scoring.
    """
    start_time = time.time()
    
    # Get singleton index
    index = RetrieverIndex.get_instance()
    if not index.is_loaded:
        index.load()
    
    # Score all examples
    scored = []
    for ex in index.examples:
        s = index.score(query, ex)
        scored.append((s, ex))
    
    # Sort descending
    scored.sort(key=lambda x: x[0], reverse=True)
    
    # Select top k
    top_results = scored[:k]
    top_examples = [ex for _, ex in top_results]
    top_scores = [round(s, 3) for s, _ in top_results]
    
    # Log
    duration = time.time() - start_time
    log_with_context(
        logger,
        20, # INFO
        "RAG retrieval completed",
        query=query,
        num_candidates=index.corpus_size,
        num_retrieved=len(top_examples),
        top_scores=top_scores,
        duration_ms=round(duration * 1000, 2)
    )
    
    return top_examples
