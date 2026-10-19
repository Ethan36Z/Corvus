# Web experiment reports

Chronological index, ordered by date and experiment sequence. A blocked or
control-repair verdict is not evidence of reliable live search or grounded answers.
Related baseline hashes below identify the Lab checkout used by the experiments;
that code is not published by this reporting branch.

| Experiment ID | Date | Objective | Verdict | Report | Important limitations | Related baseline commit |
| --- | --- | --- | --- | --- | --- | --- |
| W1 | 2026-10-18 | Compare DDGS and SearXNG retrieval and assess grounded conversational synthesis | `W1_BLOCKED_WITH_REASON` | [Live validation](2026-10-18-w1-live-validation.md) | Stopped after one DDGS plan; unexpected destination blocked; no SearXNG search or Qwen turns; no comparative reliability conclusion | `975645963291ec992d64df0474a3ee9d0ba33dcd` |
| W1.1 | 2026-10-18 | Repair isolated provider selection, fail-stop controls and cumulative accounting | `W1_1_READY_FOR_RESUME` | [Control repair](2026-10-18-w1-1-control-repair.md) | 15 offline tests passed; no live validation; new authorization required; SearXNG internal HTTP traffic cannot be strictly capped through its query interface | `975645963291ec992d64df0474a3ee9d0ba33dcd` |
| W1.2a | 2026-10-18 | Evaluate Chinese/English grounded synthesis from verified cached official documentation | `W1_2A_BLOCKED_WITH_REASON` | [Grounded synthesis](2026-10-18-w1-2a-grounded-synthesis.md) | Two HTTP-error attempts; zero answers or quality scores; English template rejects second system message; no model-capability conclusion | `975645963291ec992d64df0474a3ee9d0ba33dcd` |
| W1.2a-R1 | 2026-10-18 | Retry Chinese/English single-source explanation with Corvus’s existing composer | `W1_2A_R1_PASS_WITH_CONSTRAINTS` | [Grounded synthesis retry](2026-10-18-w1-2a-r1-grounded-synthesis.md) | Two complete answers; mixed grounding with unsupported material claims; qualitative single-source judgments only | `975645963291ec992d64df0474a3ee9d0ba33dcd` |
| W1.2a-R2 | 2026-10-18 | Test a minimal grounding-instruction revision without losing useful natural explanation | `W1_2A_R2_PASS_WITH_CONSTRAINTS` | [Grounding instruction comparison](2026-10-18-w1-2a-r2-grounding-improvement.md) | Mixed grounding change; English dependency/performance claims remain; two single-source samples only; return to real retrieval evaluation | `975645963291ec992d64df0474a3ee9d0ba33dcd` |

## Future entries

Follow the [archive conventions](../README.md). Add one sanitized report per
experiment checkpoint and one index row containing all columns above. Preserve
historical verdicts; link a later repair or acceptance report rather than rewriting
an earlier failure into a success.
