from __future__ import annotations

import json

from bench.llama_client import LlamaClient
from bench.mock_server import MockLlamaServer
from bench.modes import MISSING, Item, ModeConfig, run_item
from bench.props import PROPERTY_BY_KEY

FORMULA = PROPERTY_BY_KEY["formula"]


def item() -> Item:
    return Item(molecule_id="BENZENE", smiles="c1ccccc1", prop=FORMULA)


def client_for(server):
    return LlamaClient(server.base_url, require_port_8099=False)


def test_mode_a_answers_without_tools():
    with MockLlamaServer(['{"answer": "C6H6"}']) as server:
        result = run_item(client_for(server), ModeConfig(mode="A"), item())
        assert result.answer == "C6H6"
        assert result.trace == []
        assert result.verified is False  # verification is mode C only


def test_mode_b_tool_then_answer():
    with MockLlamaServer(
        ['{"tool": "formula", "smiles": "c1ccccc1"}', '{"answer": "C6H6"}']
    ) as server:
        result = run_item(client_for(server), ModeConfig(mode="B"), item())
        assert result.answer == "C6H6"
        assert len(result.trace) == 1
        assert result.trace[0]["canonical_match"] is True
        assert result.trace[0]["value"] == "C6H6"


def test_mode_b_no_tool_is_still_an_answer():
    with MockLlamaServer(['{"answer": "C6H6"}']) as server:
        result = run_item(client_for(server), ModeConfig(mode="B"), item())
        assert result.answer == "C6H6"
        assert result.trace == []


def test_mode_c_retry_fixes_a_wrong_smiles_call():
    script = [
        '{"tool": "formula", "smiles": "CC"}',          # wrong molecule
        '{"answer": "C2H6"}',                            # wrong answer -> verification fails
        '{"tool": "formula", "smiles": "c1ccccc1"}',     # retry: correct molecule
        '{"answer": "C6H6"}',
    ]
    with MockLlamaServer(script) as server:
        result = run_item(client_for(server), ModeConfig(mode="C"), item())
        assert result.retry_used is True
        assert result.verified is True
        assert result.verification_failed is False
        assert len(result.trace) == 2
        assert result.trace[1]["canonical_match"] is True
        retry_message = server.requests[2]["messages"][-1]["content"]
        assert retry_message.startswith("VERIFICATION FAILED")
        assert "C6H6" not in retry_message  # the verifier never writes the answer


def test_mode_c_marks_verification_failed_after_one_retry():
    script = [
        '{"tool": "formula", "smiles": "CC"}',
        '{"answer": "C2H6"}',
        '{"tool": "formula", "smiles": "CC"}',
        '{"answer": "C2H6"}',
    ]
    with MockLlamaServer(script) as server:
        result = run_item(client_for(server), ModeConfig(mode="C"), item())
        assert result.retry_used is True
        assert result.verified is False
        assert result.verification_failed is True
        assert len(server.requests) == 4  # exactly one retry, no loop


def test_tool_budget_is_enforced():
    script = ['{"tool": "parse_smiles", "smiles": "c1ccccc1"}'] * 6 + ['{"answer": "10"}']
    with MockLlamaServer(script) as server:
        result = run_item(client_for(server), ModeConfig(mode="B"), item())
        assert len(result.trace) == 5
        assert result.answer == "10"
        budget_messages = [
            message["content"]
            for request in server.requests
            for message in request["messages"]
            if "TOOL BUDGET EXHAUSTED" in message.get("content", "")
        ]
        assert len(budget_messages) == 1


def test_malformed_output_becomes_missing_answer():
    with MockLlamaServer(["I think the answer is C6H6."]) as server:
        result = run_item(client_for(server), ModeConfig(mode="B"), item())
        assert result.answer is MISSING
        assert result.nudges == 3
        assert len(server.requests) == 3


def test_thinking_text_is_ignored_for_scoring():
    with MockLlamaServer(
        [{"content": '{"answer": "C6H6"}', "reasoning_content": 'maybe {"answer": "C7H8"}'}]
    ) as server:
        result = run_item(client_for(server), ModeConfig(mode="A"), item())
        assert result.answer == "C6H6"
        assert result.responses[0]["reasoning"].startswith("maybe")


def test_trace_records_unknown_tool_cleanly():
    with MockLlamaServer(
        ['{"tool": "not_a_tool", "smiles": "c1ccccc1"}', '{"answer": "C6H6"}']
    ) as server:
        result = run_item(client_for(server), ModeConfig(mode="B"), item())
        assert result.trace[0]["ok"] is False
        assert "unknown tool" in result.trace[0]["error"]
        assert result.answer == "C6H6"


def test_json_objects_are_extracted_from_noise():
    from bench.modes import extract_json_objects, last_answer

    assert extract_json_objects('prefix {"a": 1} middle {"b": {"c": 2}}') == [
        {"a": 1},
        {"b": {"c": 2}},
    ]
    assert last_answer('x {"answer": 1} {"answer": 2}') == 2
    assert json.loads('{"answer": "C6H6"}')["answer"] == "C6H6"
