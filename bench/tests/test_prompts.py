from __future__ import annotations

from bench.prompts import build_messages, prompt_hashes, question_text, system_prompt
from bench.props import PROPERTY_BY_KEY


def test_all_prompt_files_are_hashed():
    hashes = prompt_hashes()
    assert set(hashes) == {"mode_a.txt", "mode_b.txt", "mode_c.txt", "question.txt"}
    assert all(len(value) == 64 for value in hashes.values())


def test_mode_prompts_state_the_rules():
    a = system_prompt("A")
    b = system_prompt("B")
    c = system_prompt("C")
    assert "no tools" in a.lower()
    assert '{"answer"' in a
    assert '{"tool"' in b
    assert "at most 5 tool calls" in b.lower()
    assert "retry" in c.lower()
    assert "no internet" in b.lower()


def test_question_contains_definition_and_smiles():
    prop = PROPERTY_BY_KEY["molecular_weight"]
    text = question_text(prop, "c1ccccc1")
    assert "SMILES: c1ccccc1" in text
    assert prop.definition in text
    assert prop.format_hint in text
    assert prop.label in text


def test_messages_shape():
    prop = PROPERTY_BY_KEY["ring_count"]
    messages = build_messages("C", prop, "C1=CC=CC=C1")
    assert [m["role"] for m in messages] == ["system", "user"]
    assert "retry" in messages[0]["content"].lower()
