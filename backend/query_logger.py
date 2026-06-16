"""
Query lifecycle logger - tracks complete query execution from input to result.
"""
import json
import time
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any
from .logging_config import setup_logger, log_with_context


logger = setup_logger(__name__, "query_history.log")

# Create query history directory
QUERY_HISTORY_DIR = Path(__file__).parent.parent / "data" / "query_history"
QUERY_HISTORY_DIR.mkdir(parents=True, exist_ok=True)


class QueryLogger:
    """Tracks a single query's lifecycle."""
    
    def __init__(self, query: str):
        self.query = query
        self.query_id = f"{int(time.time() * 1000)}"
        self.start_time = time.time()
        self.stages = {}
        self.result = None
        self.error = None
        
        log_with_context(
            logger, 
            20,  # INFO
            "Query started",
            query_id=self.query_id,
            query=query
        )
    
    def log_stage(self, stage_name: str, data: Dict[str, Any], duration: Optional[float] = None):
        """Log a stage of query processing."""
        stage_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "data": data
        }
        if duration is not None:
            stage_data["duration_ms"] = round(duration * 1000, 2)
        
        self.stages[stage_name] = stage_data
        
        log_with_context(
            logger,
            20,  # INFO
            f"Stage completed: {stage_name}",
            query_id=self.query_id,
            stage=stage_name,
            duration_ms=stage_data.get("duration_ms")
        )
    
    def log_rag_retrieval(self, examples: list, scores: list, duration: float):
        """Log RAG retrieval results."""
        self.log_stage("rag_retrieval", {
            "num_examples": len(examples),
            "top_scores": scores[:3] if scores else [],
            "example_queries": [ex.get("query", "") for ex in examples[:3]]
        }, duration)
    
    def log_llm_call(self, prompt_length: int, response_length: int, duration: float):
        """Log LLM interaction."""
        self.log_stage("llm_generation", {
            "prompt_length": prompt_length,
            "response_length": response_length,
        }, duration)
    
    def log_gee_execution(self, code_length: int, success: bool, duration: float):
        """Log GEE code execution."""
        self.log_stage("gee_execution", {
            "code_length": code_length,
            "success": success,
        }, duration)
    
    def log_result(self, result: Any):
        """Log successful result."""
        self.result = "success"
        total_duration = time.time() - self.start_time
        
        log_with_context(
            logger,
            20,  # INFO
            "Query completed successfully",
            query_id=self.query_id,
            total_duration_ms=round(total_duration * 1000, 2)
        )
        
        self._save_to_file()
    
    def log_error(self, error: Exception):
        """Log query failure."""
        self.error = str(error)
        total_duration = time.time() - self.start_time
        
        log_with_context(
            logger,
            40,  # ERROR
            "Query failed",
            query_id=self.query_id,
            error=str(error),
            total_duration_ms=round(total_duration * 1000, 2)
        )
        
        self._save_to_file()
    
    def _save_to_file(self):
        """Save complete query log to file."""
        log_data = {
            "query_id": self.query_id,
            "query": self.query,
            "start_time": datetime.fromtimestamp(self.start_time).isoformat(),
            "total_duration_ms": round((time.time() - self.start_time) * 1000, 2),
            "stages": self.stages,
            "result": self.result,
            "error": self.error
        }
        
        # Save to dated file
        date_str = datetime.now().strftime("%Y-%m-%d")
        file_path = QUERY_HISTORY_DIR / f"queries_{date_str}.jsonl"
        
        with open(file_path, "a") as f:
            f.write(json.dumps(log_data) + "\n")
