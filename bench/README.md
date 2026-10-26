# bench · LLM modes A/B/C

Harness for `prereg/llm_modes_plan_v1.md` sections 3-6. It answers seven
molecule-property questions per molecule in three modes and logs every request
and every answer. Reference values come from `mcp/rdkit_tool.py`.

## Files

| file | role |
|---|---|
| `select.py` | in-domain filter + 250-molecule sample (seed 20261026), writes `data/` |
| `props.py` | the seven properties, plain-word definitions, reference values |
| `prompts/` | the frozen prompt text (`mode_a/b/c.txt`, `question.txt`) |
| `tools.py` | in-process tool registry (same functions as `mcp/server.py`) |
| `llama_client.py` | OpenAI-compatible client, loopback + port 8099 guard |
| `modes.py` | A/B/C loops, JSON protocol, mode-C verification and one retry |
| `score.py` | deterministic scoring and error categories |
| `logging_jsonl.py` | append-only JSONL writer |
| `run_pilot.py` | CLI for the pilot / confirmatory runs |
| `mock_server.py` | scripted OpenAI-compatible server, tests only |

## JSON protocol

```
{"tool": "<name>", "smiles": "<SMILES>"}   -> harness replies  TOOL RESULT {...}
{"answer": <value>}                        -> final answer, scored
```

At most 5 tool calls per question (shared by the mode-C retry). Only the final
`answer` object is scored; reasoning/"thinking" text is logged and ignored.

## Tool set

The ten functions of `mcp/server.py` (`parse_smiles`, `formula`,
`molecular_weight`, `heavy_atom_count`, `ring_count`, `hbd_lipinski`,
`hbd_plain`, `hba_lipinski`, `hba_plain`, `esol_predict`) plus
`rotatable_bonds`, which section 3.2 needs but the MCP server does not wrap; the
function itself is already tested in `mcp/rdkit_tool.py`.

## Scoring (section 6)

- formula: equal after Hill normalization (element counts; order-insensitive);
- counts: exact integer match (a numeric string such as `"6"` is read as 6);
- molecular weight: `|difference| <= 0.05 g/mol`;
- missing answer or unparseable value: wrong (`parse_failure`).

Error categories are assigned from the tool trace first: `parse_failure`,
`no_tool_call`, `bad_smiles_passed`, `unit_error` (ratio 1000 or 0.001),
`arithmetic_error`, `chemistry_knowledge_error` (mode A, or no tool for the
asked property), `other` (formula copied wrongly after a correct tool call).

## Mode C verification

Three checks: a tool call whose canonical SMILES equals the question molecule;
a call for the asked property; an answer in the required format that agrees
with the tool output within the scoring tolerance. One retry on failure, then
the answer is recorded as given with `verification_failed`. The failure message
never contains the correct value, so the verifier never writes the answer.

## Port guard

`LlamaClient` accepts loopback HTTP on port **8099** only; 8080 and 8081 are
always refused, redirects are not followed, and proxy environment variables are
ignored. Tests pass `require_port_8099=False` to use an ephemeral mock port.

## Tests

```
.\.venv\Scripts\python.exe -m pytest bench/tests -q
```

No test needs a model or network: `mock_server.py` serves scripted responses.
