"""
Model Performance Tracker for Jarvis/DevMind
Inspired by pguilp25/jarvis - tracks model performance and optimizes selection
"""
import os
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional
from collections import defaultdict

PERFORMANCE_LOG = Path(".jarvis") / "model_performance.json"
PERFORMANCE_LOG.parent.mkdir(parents=True, exist_ok=True)

# Constants
DEFAULT_MODEL = "gemini-2.0-flash"
MIN_CALLS_FOR_RELIABILITY = 3
MIN_CALLS_FOR_RECOMMENDATIONS = 5

class ModelPerformanceTracker:
    def __init__(self):
        self.performance_data = defaultdict(lambda: {
            "total_calls": 0,
            "successful_calls": 0,
            "failed_calls": 0,
            "total_tokens": 0,
            "total_time": 0,
            "success_rate": 0.0,
            "avg_time": 0.0,
            "task_types": defaultdict(lambda: {
                "count": 0,
                "success": 0,
                "fail": 0
            })
        })
        self.load_performance_data()

    def load_performance_data(self):
        """Load performance data from file"""
        if PERFORMANCE_LOG.exists():
            try:
                with open(PERFORMANCE_LOG, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for model, stats in data.items():
                        self.performance_data[model] = stats
                        # Convert task_types back to defaultdict
                        if "task_types" in stats:
                            self.performance_data[model]["task_types"] = defaultdict(
                                lambda: {"count": 0, "success": 0, "fail": 0},
                                stats["task_types"]
                            )
            except Exception as e:
                print(f"[PERFORMANCE] Failed to load performance data: {e}")

    def save_performance_data(self):
        """Save performance data to file"""
        # Convert defaultdicts to regular dicts for JSON serialization
        serializable_data = {}
        for model, stats in self.performance_data.items():
            serializable_data[model] = dict(stats)
            serializable_data[model]["task_types"] = dict(stats["task_types"])
        
        with open(PERFORMANCE_LOG, 'w', encoding='utf-8') as f:
            json.dump(serializable_data, f, indent=2)

    def record_call(self, model: str, success: bool, task_type: str = "general", 
                    tokens: int = 0, time_taken: float = 0.0):
        """Record a model call"""
        stats = self.performance_data[model]
        
        stats["total_calls"] += 1
        if success:
            stats["successful_calls"] += 1
            stats["task_types"][task_type]["success"] += 1
        else:
            stats["failed_calls"] += 1
            stats["task_types"][task_type]["fail"] += 1
        
        stats["task_types"][task_type]["count"] += 1
        stats["total_tokens"] += tokens
        stats["total_time"] += time_taken
        
        # Recalculate derived metrics
        if stats["total_calls"] > 0:
            stats["success_rate"] = stats["successful_calls"] / stats["total_calls"]
        if stats["total_calls"] > 0:
            stats["avg_time"] = stats["total_time"] / stats["total_calls"]
        
        self.save_performance_data()

    def get_best_model_for_task(self, task_type: str) -> str:
        """Get the best performing model for a specific task type"""
        best_model = self._find_best_by_task_type(task_type)
        
        if not best_model:
            best_model = self._find_best_overall()
        
        return best_model or DEFAULT_MODEL

    def _find_best_by_task_type(self, task_type: str) -> Optional[str]:
        """Find best model for specific task type"""
        best_model = None
        best_score = -1
        
        for model, stats in self.performance_data.items():
            task_stats = stats["task_types"].get(task_type, {"count": 0, "success": 0, "fail": 0})
            
            if task_stats["count"] < MIN_CALLS_FOR_RELIABILITY:
                continue
            
            score = self._calculate_score(task_stats, stats)
            
            if score > best_score:
                best_score = score
                best_model = model
        
        return best_model

    def _find_best_overall(self) -> Optional[str]:
        """Find best model by overall success rate"""
        best_model = None
        best_score = -1
        
        for model, stats in self.performance_data.items():
            if stats["total_calls"] >= MIN_CALLS_FOR_RELIABILITY:
                if stats["success_rate"] > best_score:
                    best_score = stats["success_rate"]
                    best_model = model
        
        return best_model

    def _calculate_score(self, task_stats: Dict, stats: Dict) -> float:
        """Calculate performance score"""
        success_rate = task_stats["success"] / task_stats["count"] if task_stats["count"] > 0 else 0
        avg_time = stats["avg_time"] if stats["avg_time"] > 0 else 1.0
        return (success_rate * 0.7) + ((1.0 / avg_time) * 0.3)

    def get_performance_report(self, model: str = None) -> Dict:
        """Get performance report for a specific model or all models"""
        if model:
            return dict(self.performance_data[model])
        else:
            return {m: dict(s) for m, s in self.performance_data.items()}

    def get_recommendations(self) -> List[str]:
        """Get recommendations based on performance data"""
        recommendations = []
        
        for model, stats in self.performance_data.items():
            if stats["total_calls"] < MIN_CALLS_FOR_RECOMMENDATIONS:
                continue
            
            recommendations.extend(self._check_model_performance(model, stats))
        
        return recommendations

    def _check_model_performance(self, model: str, stats: Dict) -> List[str]:
        """Check model performance and return recommendations"""
        recommendations = []
        
        if stats["success_rate"] < 0.7:
            recommendations.append(self._format_low_success_warning(model, stats))
        
        if stats["avg_time"] > 10.0:
            recommendations.append(self._format_slow_response_warning(model, stats))
        
        recommendations.extend(self._check_task_failures(model, stats))
        
        return recommendations

    def _format_low_success_warning(self, model: str, stats: Dict) -> str:
        """Format low success rate warning"""
        return "⚠️ {} has low success rate ({:.1%}). Consider using alternative models.".format(
            model, stats['success_rate']
        )

    def _format_slow_response_warning(self, model: str, stats: Dict) -> str:
        """Format slow response warning"""
        return "⚠️ {} is slow (avg {:.1f}s). Consider faster alternatives.".format(
            model, stats['avg_time']
        )

    def _check_task_failures(self, model: str, stats: Dict) -> List[str]:
        """Check for high failure rates on specific task types"""
        recommendations = []
        
        for task_type, task_stats in stats["task_types"].items():
            if task_stats["count"] >= MIN_CALLS_FOR_RECOMMENDATIONS:
                fail_rate = task_stats["fail"] / task_stats["count"]
                if fail_rate > 0.5:
                    recommendations.append(
                        "⚠️ {} fails frequently on {} tasks ({:.1%}). Consider using different model for this task type.".format(
                            model, task_type, fail_rate
                        )
                    )
        
        return recommendations

    def reset_model_data(self, model: str):
        """Reset performance data for a specific model"""
        self.performance_data[model] = defaultdict(lambda: {
            "total_calls": 0,
            "successful_calls": 0,
            "failed_calls": 0,
            "total_tokens": 0,
            "total_time": 0,
            "success_rate": 0.0,
            "avg_time": 0.0,
            "task_types": defaultdict(lambda: {"count": 0, "success": 0, "fail": 0})
        })
        self.save_performance_data()

# Global performance tracker instance
performance_tracker = ModelPerformanceTracker()

def track_model_call(model: str, success: bool, task_type: str = "general", 
                    tokens: int = 0, time_taken: float = 0.0):
    """Public interface to track model calls"""
    performance_tracker.record_call(model, success, task_type, tokens, time_taken)

def get_best_model(task_type: str = "general") -> str:
    """Get the best model for a specific task type"""
    return performance_tracker.get_best_model_for_task(task_type)

def get_performance_report(model: str = None) -> Dict:
    """Get performance report"""
    return performance_tracker.get_performance_report(model)

def get_recommendations() -> List[str]:
    """Get performance-based recommendations"""
    return performance_tracker.get_recommendations()

if __name__ == "__main__":
    # Test performance tracker
    print("Testing Model Performance Tracker")
    print("=" * 50)
    
    # Simulate some calls
    track_model_call("gemini-2.0-flash", True, "code_generation", 1000, 2.5)
    track_model_call("gemini-2.0-flash", True, "code_generation", 1200, 2.3)
    track_model_call("gemini-2.0-flash", False, "code_generation", 800, 2.1)
    track_model_call("gpt-4o-mini", True, "code_generation", 900, 1.8)
    track_model_call("gpt-4o-mini", True, "code_generation", 1100, 1.9)
    track_model_call("gpt-4o-mini", True, "code_generation", 950, 1.7)
    
    # Get best model
    best = get_best_model("code_generation")
    print("Best model for code_generation: {}".format(best))
    
    # Get report
    report = get_performance_report()
    print("\nPerformance Report:")
    for model, stats in report.items():
        print("  {}: {:.1%} success, {:.1f}s avg".format(model, stats['success_rate'], stats['avg_time']))
    
    # Get recommendations
    recommendations = get_recommendations()
    if recommendations:
        print("\nRecommendations:")
        for rec in recommendations:
            print("  {}".format(rec))
    else:
        print("\nNo recommendations - all models performing well!")
