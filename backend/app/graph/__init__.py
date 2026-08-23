# app/graph/__init__.py
"""
LangGraph workflow package for Phase 10 Agentic AI.

Exports the compiled agent workflow for use in agent_service.
"""

from app.graph.workflow import agent_workflow

__all__ = ["agent_workflow"]
