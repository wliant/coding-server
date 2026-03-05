"""Unit tests for CodingAgentResult."""

import dataclasses
from pathlib import Path

import pytest

from simple_crewai_pair_agent.result import CodingAgentResult


def test_fields_accessible() -> None:
    result = CodingAgentResult(code="x = 1", review="LGTM", output_file=Path("/tmp/out.py"))
    assert result.code == "x = 1"
    assert result.review == "LGTM"
    assert result.output_file == Path("/tmp/out.py")


def test_frozen_raises_on_mutation() -> None:
    result = CodingAgentResult(code="x = 1", review="LGTM", output_file=Path("/tmp/out.py"))
    with pytest.raises(dataclasses.FrozenInstanceError):
        result.code = "changed"  # type: ignore[misc]


def test_is_frozen_dataclass() -> None:
    assert dataclasses.is_dataclass(CodingAgentResult)
    assert dataclasses.fields(CodingAgentResult)  # has fields
    # frozen dataclasses have __hash__ derived automatically
    result = CodingAgentResult(code="a", review="b", output_file=Path("/x"))
    assert hash(result) is not None
