"""
Multi-agent orchestration.

Coordinates multiple AI agents for complex tasks,
managing task distribution and result aggregation.
"""

from __future__ import annotations

import asyncio
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable


@dataclass
class AgentTask:
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])
    name: str = ""
    status: str = "pending"
    result: Any = None
    error: str = ""


@dataclass
class Agent:
    id: str
    name: str
    capabilities: list[str] = field(default_factory=list)
    handler: Callable | None = None


class Orchestrator:
    """Coordinates multi-agent task execution."""

    def __init__(self):
        self._agents: dict[str, Agent] = {}
        self._tasks: dict[str, AgentTask] = {}

    def register_agent(self, agent: Agent) -> None:
        self._agents[agent.id] = agent

    def unregister_agent(self, agent_id: str) -> None:
        self._agents.pop(agent_id, None)

    async def submit_task(self, task_name: str, payload: dict, required_capability: str = "") -> AgentTask:
        task = AgentTask(name=task_name)
        self._tasks[task.id] = task

        # Find capable agent
        agent = self._find_agent(required_capability)
        if not agent or not agent.handler:
            task.status = "failed"
            task.error = f"No agent available for: {required_capability or task_name}"
            return task

        try:
            task.status = "running"
            if asyncio.iscoroutinefunction(agent.handler):
                task.result = await agent.handler(payload)
            else:
                task.result = agent.handler(payload)
            task.status = "completed"
        except Exception as e:
            task.status = "failed"
            task.error = str(e)
        return task

    async def run_pipeline(self, tasks: list[tuple[str, dict, str]]) -> list[AgentTask]:
        """Run a sequence of tasks, passing results forward."""
        results = []
        context: dict = {}
        for name, payload, capability in tasks:
            payload["_context"] = context
            result = await self.submit_task(name, payload, capability)
            results.append(result)
            if result.status == "completed":
                context[name] = result.result
            else:
                break
        return results

    def _find_agent(self, capability: str) -> Agent | None:
        if not capability:
            agents = list(self._agents.values())
            return agents[0] if agents else None
        for agent in self._agents.values():
            if capability in agent.capabilities:
                return agent
        return None

    def list_agents(self) -> list[dict]:
        return [{"id": a.id, "name": a.name, "capabilities": a.capabilities} for a in self._agents.values()]


orchestrator = Orchestrator()
