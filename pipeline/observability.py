"""
Dore OS v2.0 — Observability Module
LangFuse integration for LLM call tracing and pipeline monitoring.
"""
import os
from typing import Optional, Dict, Any
from datetime import datetime


class Observability:
    """LangFuse-based observability for Dore OS pipeline."""

    def __init__(self):
        self.enabled = bool(os.getenv("LANGFUSE_PUBLIC_KEY"))
        self.tracer = None

        if self.enabled:
            self._init_langfuse()

    def _init_langfuse(self):
        """Initialize LangFuse client."""
        try:
            from langfuse import Langfuse
            self.tracer = Langfuse(
                public_key=os.getenv("LANGFUSE_PUBLIC_KEY", ""),
                secret_key=os.getenv("LANGFUSE_SECRET_KEY", ""),
                host=os.getenv("LANGFUSE_HOST", "http://localhost:3000"),
            )
        except ImportError:
            self.enabled = False
            print("⚠ langfuse not installed. Observability disabled.")
        except Exception as e:
            self.enabled = False
            print(f"⚠ LangFuse init failed: {e}")

    def trace(self, name: str, metadata: Dict = None) -> Optional[Any]:
        """Create a LangFuse trace for a pipeline operation."""
        if not self.enabled or not self.tracer:
            return None
        return self.tracer.trace(name=name, metadata=metadata)

    def log_llm_call(self, trace_id: str, model: str, prompt: str,
                     response: str, tokens: int = 0, cost: float = 0.0,
                     metadata: Dict = None):
        """Log an LLM call within a trace."""
        if not self.enabled or not self.tracer:
            return

        trace = self.tracer.get_trace(trace_id)
        if trace:
            trace.generation(
                name=f"llm_{model}",
                model=model,
                input=prompt[:5000],
                output=response[:5000],
                usage={
                    "input_tokens": tokens // 2,
                    "output_tokens": tokens // 2,
                    "total_tokens": tokens,
                },
                metadata={
                    "cost": cost,
                    "timestamp": datetime.utcnow().isoformat(),
                    **(metadata or {})
                }
            )

    def log_agent_action(self, trace_id: str, agent_name: str,
                         action: str, input_data: Dict, output_data: Dict):
        """Log an agent action within a trace."""
        if not self.enabled or not self.tracer:
            return

        trace = self.tracer.get_trace(trace_id)
        if trace:
            trace.span(
                name=f"agent_{agent_name}",
                input=input_data,
                output=output_data,
                metadata={"action": action, "agent": agent_name}
            )

    def log_error(self, trace_id: str, error_type: str, message: str,
                  stack_trace: str = ""):
        """Log an error within a trace."""
        if not self.enabled or not self.tracer:
            return

        trace = self.tracer.get_trace(trace_id)
        if trace:
            trace.event(
                name="error",
                metadata={
                    "error_type": error_type,
                    "message": message,
                    "stack_trace": stack_trace[:2000],
                }
            )

    def flush(self):
        """Flush all pending traces."""
        if self.tracer:
            self.tracer.flush()


# Singleton
_obs_instance = None


def get_observability() -> Observability:
    global _obs_instance
    if _obs_instance is None:
        _obs_instance = Observability()
    return _obs_instance
