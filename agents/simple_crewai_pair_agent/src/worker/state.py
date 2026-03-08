from typing import Annotated, Any
from langgraph.graph.message import add_messages
from typing_extensions import TypedDict


class AgentState(TypedDict):
    job_id: str
    requirement: str
    messages: Annotated[list[Any], add_messages]
    tool_calls: list[dict]
    output: str | None
    error: str | None
