# AlgoCoach

AlgoCoach is a local, evidence-first debugging tutor for DSA learners. It runs a learner's Python function against a small problem-specific test suite, shows a concrete failing case, suggests a likely bug, and reveals three progressively stronger hints when the learner chooses them.

This is a runnable starter project for the EnjoyAlgorithms IPL brief. It uses Python's standard library only and does not call an external LLM or send code over the network.

## Run it

1. Install Python 3.10 or newer.
2. Open a terminal in this folder.
3. Run `python app.py`.
4. Open `http://127.0.0.1:8765` if a browser does not open automatically.
5. Paste a function named `solve` using the selected problem's input arguments, then choose **Debug my code**.

To use a different local port, set `ALGOCOACH_PORT` before starting the app. Stop the server with Ctrl+C.

## What is included

- A browser interface with 10 classic DSA problems.
- Fixed tests for normal cases, boundaries, empty inputs where relevant, duplicates, and negative values.
- A subprocess runner with a time limit, a restricted builtin set, AST checks, and an import/private-attribute denylist.
- Separate orchestration, test, diagnosis, complexity, and hint responsibilities, with a visible session trace.
- A three-level hint ladder that the learner advances manually.
- A 30-submission labeled buggy-code benchmark and a small evaluation script.
- `DESIGN.md` describing architecture, evaluation, trade-offs, risks, and a week-wise build plan.

## Try a sample

Choose **Two Sum** and replace the starter with:

```python
def solve(nums, target):
    for x in nums:
        if target - x in nums:
            return [x, target - x]
```

It returns values instead of indices. The tutor should show a failing test and a hint directing attention to what the function must return.

## Evaluation

Run `python evaluation.py` to check whether each labeled buggy submission is caught by the current fixed test suite. This is a first benchmark pass, not a complete judgement of diagnosis accuracy or hint quality. Use the rubric in `DESIGN.md` to score diagnosis, hints, and solution leakage with human reviewers, and report the results with sample counts.

The current system uses deterministic, problem-specific diagnosis and hints. It does not yet include a single-prompt LLM baseline, generated tests, learner memory, empirical timing on growing inputs, C++/Java support, or a measured latency/cost study. Do not report those as completed features.

## Safety notes

The app binds to `127.0.0.1` and runs submitted code in a separate Python process with a 2.5-second wall-clock limit, a restricted builtin namespace, and syntax checks. This reduces risk for a local classroom prototype; it is **not a hardened sandbox**. Python-level restrictions are not a security boundary against determined hostile code, and this app must not be exposed to the public internet or used for sensitive submissions. For a real hosted service, put execution in disposable OS containers or VMs with no network, non-root users, read-only filesystems, CPU/memory/process limits, and strict lifecycle cleanup.

## Project map

- `app.py` — local web app, runner, and deterministic agents
- `problems.json` — problem statements, starter code, and test suites
- `benchmark.json` — 30 intentionally buggy submissions with labeled root causes
- `evaluation.py` — fixed-suite bug detection summary
- `DESIGN.md` — architecture, evaluation plan, trade-offs, and implementation plan
