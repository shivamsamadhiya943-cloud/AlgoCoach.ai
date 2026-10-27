# AlgoCoach design note

## Goal

AlgoCoach helps a DSA learner make progress without immediately replacing their work with a complete answer. It uses program output as evidence, explains the likely failure, and lets the learner request progressively more specific hints.

## Session flow

```text
Problem + learner code + optional question
                  |
             Orchestrator
                  |
    Safety checks and subprocess runner
                  |
       Fixed problem test suite
                  |
       Counterexample or pass result
          /          |          \
     Diagnosis   Complexity    Hint ladder
          \          |          /
               Session trace
```

1. The browser sends the selected problem and source to the local server.
2. The orchestrator looks up the problem's tests and expected function name.
3. The guard parses the source and rejects imports, private/dunder attributes, dynamic evaluation, and selected risky syntax.
4. A separate interpreter process executes the function in a reduced builtin namespace and is terminated after 2.5 seconds.
5. The test agent returns expected and actual outputs for each case.
6. A deterministic problem-specific diagnosis suggests likely failure areas. The hint agent supplies a three-step ladder. The learner chooses when to reveal each level.
7. The complexity agent offers a deliberately rough static loop scan. It explicitly avoids presenting that scan as a measured time-complexity result.
8. The UI shows test evidence, diagnosis, complexity note, and a short trace.

## Agent responsibilities and trade-offs

| Role | Current implementation | Trade-off |
| --- | --- | --- |
| Orchestrator | Calls guard, runner, tests, diagnosis, complexity and hints in order | Easy to understand and reproduce; not an adaptive LLM planner |
| Test agent | Runs fixed test cases stored per problem | Deterministic and fast; does not generate inputs or prove correctness |
| Diagnosis agent | Uses problem-specific diagnosis text and test evidence | Predictable, low cost, no hallucinated model output; cannot deeply inspect arbitrary logic |
| Complexity agent | Counts loop nodes and provides caveated feedback | Transparent but intentionally weak; not empirical complexity analysis |
| Hint agent | Provides three problem-specific hints | Prevents an automatic full solution; hint helpfulness still needs human evaluation |
| Progress memory | Not implemented | Future bonus; would need consent, retention limits and an evaluation plan |

The prototype requires no API key and sends no source code to a model provider. The learner's optional question is retained as trace context only; answering free-form questions with an LLM is a future extension.

## Safety boundary

Source is limited to 50 KB at the HTTP handler. The server only listens on the loopback interface. The runner uses a new interpreter subprocess, an isolated mode, no site initialization, a restricted builtin namespace, syntax checks, and a wall-clock timeout. It runs with the current operating-system user's permissions and Python process isolation is not a hardened security boundary. A production or internet-facing deployment must use a proper container/VM sandbox with network disabled, resource and process limits, a disposable filesystem, and non-root credentials. The present app is a local demonstration only.

## Evaluation plan

### Automated benchmark

`benchmark.json` contains 30 buggy submissions, three per problem across 10 problems. Each has an ID, the affected problem, and a human-authored actual-bug label. `evaluation.py` runs every submission against that problem's fixed test suite and reports how many known-bug submissions produce at least one failing result. This measures bug reproduction by the current suite, not whether the diagnosis names the exact root cause.

### Human-rated quality

For diagnosis and hint quality, have at least two reviewers score each sampled session independently:

- Diagnosis correctness: 0 = wrong, 1 = partly right, 2 = correct and supported by evidence.
- Hint usefulness: 1 = unhelpful, 2 = somewhat useful, 3 = useful and appropriately scoped, 4 = strongly supports the next learner step.
- Solution leakage: 0 = no full solution disclosed, 1 = gives away most of the fix, 2 = effectively supplies the complete solution.

Report sample count, mean/median scores, reviewer agreement, and representative disagreements. Do not claim a high hint score from a handful of cherry-picked examples.

### Baselines and measurements to add

Compare against a simple single-prompt assistant on the same bugs, using the same scoring rubric. Add generated edge cases, a trusted reference implementation, and growing input sizes before reporting empirical complexity. Record end-to-end latency across multiple runs and report median and p95. Model cost is zero for the current local deterministic prototype; if a model is added, record actual provider usage and price separately.

## Known limitations

- Python only; the code expects a function named `solve`.
- Fixed tests only. Passing them does not establish correctness.
- Diagnosis and hints are curated by problem, not a general code-understanding model.
- The complexity note does not measure runtime and cannot correctly infer every algorithm.
- No persistence, accounts, learner profiles, or progress memory.
- No hardened hostile-code isolation.
- Human hint and leakage scores have not been collected yet.

## Suggested week-wise implementation plan

| Week | Deliverable |
| --- | --- |
| 1 | Agree on problem/function schema; implement local UI, problem catalog, and safe runner prototype |
| 2 | Add test, diagnosis, hint, and trace components; review sandbox boundary |
| 3 | Label and validate at least 30 buggy submissions across 10 problems; build evaluation script |
| 4 | Run human hint/diagnosis review and baseline comparison; improve weak cases |
| 5 | Polish documentation, record the five-minute demo, and prepare a live review deployment using hardened isolation |

Adjust the schedule to the actual team size and competition timeline.
