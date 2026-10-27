"""AlgoCoach: a local, evidence-grounded DSA debugging tutor.

Run with: python app.py
The server binds to localhost only. The execution guard is defense-in-depth for
classroom demos, not a substitute for an OS/container security boundary.
"""
from __future__ import annotations

import ast
import json
import os
import subprocess
import sys
import tempfile
import threading
import time
import traceback
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent
PROBLEMS = json.loads((ROOT / "problems.json").read_text(encoding="utf-8"))
PORT = int(os.environ.get("ALGOCOACH_PORT", "8765"))

PAGE = r'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>AlgoCoach | Debug with understanding</title>
<style>
:root{--ink:#17251f;--muted:#64756d;--paper:#f4f7f2;--card:#fff;--green:#176b4a;--line:#dce6dd;--red:#a63232;--amber:#855d0c}*{box-sizing:border-box}body{margin:0;background:var(--paper);color:var(--ink);font:15px/1.5 ui-sans-serif,system-ui,Segoe UI,sans-serif}header{background:#123c2d;color:white;padding:20px max(24px,calc((100% - 1160px)/2));display:flex;justify-content:space-between;align-items:center}header strong{font-size:20px}header span{color:#c4dfce;font-size:13px}.wrap{max-width:1160px;margin:26px auto;padding:0 20px}.intro{margin-bottom:18px}.intro h1{font-size:26px;margin:0 0 4px}.intro p{color:var(--muted);margin:0}.layout{display:grid;grid-template-columns:340px 1fr;gap:18px;align-items:start}.card{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:18px;box-shadow:0 5px 20px #193f2810}.card h2{font-size:16px;margin:0 0 12px}.stack{display:grid;gap:14px}label{font-size:13px;font-weight:650;display:block;margin-bottom:6px}select,textarea,input{width:100%;border:1px solid #cbd8ce;border-radius:9px;padding:10px;background:white;color:var(--ink);font:inherit}textarea{resize:vertical}#code{font:13px/1.55 ui-monospace,SFMono-Regular,Consolas,monospace;min-height:300px;background:#101e19;color:#e2f2e7;border-color:#101e19}#question{min-height:72px}.statement{color:#354b40;font-size:14px}.constraints{color:var(--muted);font-size:12px;margin-top:8px}.btn{border:0;border-radius:9px;padding:11px 16px;background:var(--green);color:white;font-weight:700;cursor:pointer}.btn:disabled{opacity:.55;cursor:wait}.secondary{background:#e8f2eb;color:#145338}.hint-row{display:flex;gap:8px;flex-wrap:wrap;margin-top:10px}.status{font-size:13px;color:var(--muted)}.result{margin-top:18px;display:none}.pill{display:inline-block;padding:3px 9px;border-radius:100px;background:#e8f2eb;color:#145338;font-size:12px;font-weight:700}.pill.fail{background:#faeaea;color:var(--red)}pre{white-space:pre-wrap;overflow-wrap:anywhere;background:#f1f5f2;border-radius:9px;padding:12px;font:13px/1.5 ui-monospace,Consolas,monospace}.panel{border-top:1px solid var(--line);padding-top:14px;margin-top:14px}.hint{border-left:3px solid #61a883;background:#f3faf5;padding:11px 13px;border-radius:0 8px 8px 0}.trace{font-size:13px;color:#45594e}.trace li{margin:6px 0}footer{margin:22px 0;color:var(--muted);font-size:12px}.error{color:var(--red)}@media(max-width:800px){.layout{grid-template-columns:1fr}header{padding:16px 20px}}
</style></head><body>
<header><strong>AlgoCoach</strong><span>Debug with understanding</span></header>
<main class="wrap"><section class="intro"><h1>Your code. Your next step.</h1><p>Find a counterexample, understand the bug, then ask for hints one level at a time.</p></section>
<div class="layout"><aside class="card stack"><div><label for="problem">Choose a problem</label><select id="problem"></select></div><div id="statement" class="statement"></div><div><label for="question">What are you wondering? <span class="status">(optional)</span></label><textarea id="question" placeholder="Why does my solution fail on duplicates?"></textarea></div><div class="constraints">Code runs in a restricted subprocess with a short time limit. Do not submit sensitive code.</div></aside>
<section class="stack"><div class="card"><label for="code">Your Python code</label><textarea id="code" spellcheck="false"></textarea><div style="display:flex;justify-content:space-between;align-items:center;margin-top:12px"><span id="status" class="status">Ready when you are.</span><button id="debug" class="btn">Debug my code</button></div></div>
<section id="result" class="card result"><div id="verdict"></div><div id="evidence" class="panel"></div><div id="diagnosis" class="panel"></div><div class="panel"><h2>Hint ladder</h2><div id="hint" class="hint">Start by running your code to see what happens.</div><div class="hint-row"><button class="btn secondary" data-level="1">Nudge</button><button class="btn secondary" data-level="2">Direction</button><button class="btn secondary" data-level="3">Near-solution</button></div></div><div id="complexity" class="panel"></div><div id="trace" class="panel trace"></div></section></section></div>
<footer>AlgoCoach teaching demo · Evidence first, hints second. This prototype is not a hardened public code execution service.</footer></main>
<script>
const $=s=>document.querySelector(s);let current=null, currentHint=0;
async function init(){const r=await fetch('/api/problems');const p=await r.json();const sel=$('#problem');p.forEach(x=>{const o=document.createElement('option');o.value=x.id;o.textContent=x.title;sel.append(o)});sel.onchange=showProblem;showProblem()}
async function showProblem(){const p=(await (await fetch('/api/problems')).json()).find(x=>x.id===$('#problem').value);$('#statement').innerHTML='<b>'+escapeHtml(p.title)+'</b><p>'+escapeHtml(p.statement)+'</p><div class="constraints">'+escapeHtml(p.constraints)+'</div>';$('#code').value=p.starter;$('#result').style.display='none'}
function escapeHtml(x){return String(x).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]))}
$('#debug').onclick=async()=>{const b=$('#debug');b.disabled=true;$('#status').textContent='Running checks and tracing the failure…';$('#result').style.display='block';$('#verdict').textContent='Analyzing…';try{const r=await fetch('/api/debug',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({problem:$('#problem').value,code:$('#code').value,question:$('#question').value})});current=await r.json();currentHint=0;if(!r.ok)throw Error(current.error||'Request failed');render(current);$('#status').textContent='Analysis complete.'}catch(e){$('#verdict').innerHTML='<span class="error">'+escapeHtml(e.message)+'</span>';$('#status').textContent='Could not complete analysis.'}finally{b.disabled=false}};
function render(d){$('#verdict').innerHTML='<span class="pill '+(d.passed?'':'fail')+'">'+(d.passed?'All checks passed':'A failing case was found')+'</span>';$('#evidence').innerHTML='<h2>Test evidence</h2>'+d.evidence.map(e=>'<p><b>'+escapeHtml(e.label)+'</b></p><pre>'+escapeHtml(e.text)+'</pre>').join('');$('#diagnosis').innerHTML='<h2>Likely diagnosis</h2><p>'+escapeHtml(d.diagnosis)+'</p>';$('#hint').textContent='Choose a hint level when you are ready.';$('#complexity').innerHTML='<h2>Complexity check</h2><p>'+escapeHtml(d.complexity)+'</p>';$('#trace').innerHTML='<h2>Session trace</h2><ol>'+d.trace.map(x=>'<li>'+escapeHtml(x)+'</li>').join('')+'</ol>';document.querySelectorAll('[data-level]').forEach(b=>b.onclick=()=>{const n=Number(b.dataset.level);$('#hint').textContent=d.hints[n-1];currentHint=n})}
init();
</script></body></html>'''

class GuardError(Exception):
    pass


class SafetyVisitor(ast.NodeVisitor):
    """Reject imports, private attributes, dynamic execution and risky syntax."""
    DENIED_NODES = (ast.Import, ast.ImportFrom, ast.Global, ast.Nonlocal, ast.With,
                    ast.AsyncWith, ast.AsyncFunctionDef, ast.Await, ast.Lambda,
                    ast.ClassDef, ast.Try, ast.Raise, ast.Delete)

    def generic_visit(self, node: ast.AST) -> None:
        if isinstance(node, self.DENIED_NODES):
            raise GuardError(f"Restricted Python construct: {type(node).__name__}")
        super().generic_visit(node)

    def visit_Attribute(self, node: ast.Attribute) -> None:
        if node.attr.startswith("_"):
            raise GuardError("Private or dunder attributes are not allowed")
        self.generic_visit(node)

    def visit_Name(self, node: ast.Name) -> None:
        if node.id in {"eval", "exec", "compile", "open", "input", "__import__",
                       "globals", "locals", "vars", "getattr", "setattr", "delattr"}:
            raise GuardError(f"Restricted name: {node.id}")


WORKER = r'''import ast,json,sys,traceback
payload=json.loads(sys.stdin.read()); code=payload['code']; tests=payload['tests']
SAFE={'abs':abs,'all':all,'any':any,'bool':bool,'dict':dict,'enumerate':enumerate,'float':float,'int':int,'len':len,'list':list,'max':max,'min':min,'range':range,'reversed':reversed,'round':round,'set':set,'sorted':sorted,'str':str,'sum':sum,'tuple':tuple,'zip':zip,'True':True,'False':False,'None':None}
try:
 tree=ast.parse(code)
 for node in ast.walk(tree):
  if isinstance(node,(ast.Import,ast.ImportFrom,ast.Global,ast.Nonlocal,ast.With,ast.AsyncWith,ast.AsyncFunctionDef,ast.Await,ast.Lambda,ast.ClassDef,ast.Try,ast.Raise,ast.Delete)): raise ValueError('Restricted syntax: '+type(node).__name__)
  if isinstance(node,ast.Attribute) and node.attr.startswith('_'): raise ValueError('Private/dunder attributes are restricted')
  if isinstance(node,ast.Name) and node.id in {'eval','exec','compile','open','input','__import__','globals','locals','vars','getattr','setattr','delattr'}: raise ValueError('Restricted name: '+node.id)
 ns={'__builtins__':SAFE}; exec(compile(tree,'<learner>','exec'),ns,ns)
 fn=ns.get(payload['function'])
 if not callable(fn): raise ValueError('Could not find function '+payload['function'])
 results=[]
 for t in tests:
  try:
   got=fn(*t['args']); results.append({'label':t['label'],'args':t['args'],'expected':t['expected'],'actual':got,'passed':got==t['expected']})
  except BaseException as e: results.append({'label':t['label'],'args':t['args'],'expected':t['expected'],'actual':type(e).__name__+': '+str(e),'passed':False})
 print(json.dumps({'ok':True,'results':results}))
except BaseException as e: print(json.dumps({'ok':False,'error':type(e).__name__+': '+str(e)}))
'''


def run_submission(code: str, problem: dict[str, Any]) -> dict[str, Any]:
    try:
        tree = ast.parse(code)
        SafetyVisitor().visit(tree)
    except (SyntaxError, GuardError) as exc:
        return {"ok": False, "error": f"Code check: {exc}"}
    payload = {"code": code, "function": problem["function"], "tests": problem["tests"]}
    try:
        result = subprocess.run([sys.executable, "-I", "-S", "-c", WORKER],
                                input=json.dumps(payload), capture_output=True,
                                text=True, timeout=2.5, cwd=tempfile.gettempdir(),
                                env={"PATH": os.environ.get("PATH", "")})
        if result.returncode != 0:
            return {"ok": False, "error": "Runner exited unexpectedly."}
        return json.loads(result.stdout)
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": "Execution timed out (2.5 seconds)."}
    except Exception as exc:
        return {"ok": False, "error": f"Runner error: {type(exc).__name__}"}


def analyze(problem: dict[str, Any], code: str, question: str = "") -> dict[str, Any]:
    started = time.perf_counter()
    run = run_submission(code, problem)
    trace = ["Orchestrator selected the problem test suite and safe runner."]
    if not run.get("ok"):
        error = run.get("error", "Could not execute the submission.")
        diagnosis = "The submission could not be analyzed: " + error
        evidence = [{"label": "Execution status", "text": error}]
        hints = ["Check that your code uses the expected function signature.",
                 "Read the execution message and simplify the function until it runs.",
                 f"Define {problem['function']} with the arguments shown in the starter code, then return the required result."]
        trace.append("Safety and execution checks stopped test analysis.")
        passed = False
    else:
        results = run["results"]
        failures = [r for r in results if not r["passed"]]
        trace.append(f"Test agent ran {len(results)} fixed tests; {len(failures)} failed.")
        if failures:
            f = failures[0]
            diagnosis = diagnose(problem["id"], code, f)
            evidence = [{"label": f["label"], "text": f"Input: {f['args']}\nExpected: {f['expected']}\nActual: {f['actual']}"}]
            trace.append("Diagnosis agent matched the counterexample against common bug patterns.")
            hints = hints_for(problem["id"], diagnosis, f)
            trace.append("Hint agent prepared three progressively more specific clues.")
            passed = False
        else:
            diagnosis = "All fixed tests passed. That is good evidence, but it does not prove correctness on every possible input."
            evidence = [{"label": "Fixed suite", "text": f"Passed {len(results)} of {len(results)} tests."}]
            hints = ["Try constructing an input at the smallest allowed size.", "Check duplicate values and boundary values against the constraints.", "Generate randomized cases and compare your output with a trusted reference implementation."]
            trace.extend(["Diagnosis agent found no failure in the fixed suite.", "Hint agent suggested next validation steps."])
            passed = True
        trace.append("Complexity agent estimated complexity from code structure; runtime claims require a separate growing-input benchmark.")
    elapsed_ms = (time.perf_counter() - started) * 1000
    if question.strip():
        trace.append("Learner question was recorded as context; this prototype does not call an external language model.")
    complexity = complexity_note(code, problem["id"])
    return {"passed": passed, "evidence": evidence, "diagnosis": diagnosis,
            "hints": hints, "complexity": complexity,
            "trace": trace + [f"Local analysis completed in {elapsed_ms:.0f} ms."],
            "latency_ms": round(elapsed_ms, 1)}


def diagnose(pid: str, code: str, failure: dict[str, Any]) -> str:
    a = failure["args"]
    actual = failure["actual"]
    if isinstance(actual, str) and ("Error:" in actual or actual.endswith("Error")):
        return f"The failing input {a} raises {actual}. Check the operation that runs on this boundary case."
    patterns = {
        "two_sum": "The failing case suggests the pair lookup or duplicate handling is incorrect. Check whether you compare a value with itself before the required second index exists.",
        "valid_parentheses": "The failing case suggests a mismatch between opening and closing brackets, or an incorrect empty-stack check before popping.",
        "binary_search": "The failing case suggests a boundary update or midpoint condition can skip the target or fail to shrink the search interval.",
        "max_subarray": "The failing case suggests the running sum is not reset or compared at the right point, especially when values are negative.",
        "contains_duplicate": "The failing case suggests duplicate detection or the empty/single-item case is handled incorrectly.",
        "reverse_string": "The failing case suggests the two-pointer swap boundaries or the returned value is incorrect.",
        "fizz_buzz": "The failing case suggests divisibility precedence or the combined multiple-of-3-and-5 case is missing.",
        "merge_sorted": "The failing case suggests one input's remaining values are not appended after the other pointer reaches its end.",
        "climb_stairs": "The failing case suggests the base cases or recurrence initialization are off by one.",
        "first_unique": "The failing case suggests the code returns the first character rather than the first character whose count is one, or mishandles no-result input.",
    }
    return patterns.get(pid, f"The counterexample {a} returns {actual}, which differs from the expected result. Inspect the branch that handles this input.")


def hints_for(pid: str, diagnosis: str, failure: dict[str, Any]) -> list[str]:
    specific = {
        "two_sum": ["Look at the smallest failing pair and ask what the lookup structure contains at each iteration.", "The complement check should use a value seen earlier, while still allowing equal numbers at different indices.", "Store previously visited values with their indices; for each value, check whether its complement was seen before adding the current value."],
        "valid_parentheses": ["Trace the stack after each character in the failing string.", "A closing bracket needs a matching most-recent opening bracket; an empty stack cannot be popped.", "Map each closing bracket to its opener, reject a mismatch or empty stack, and finish by checking the stack is empty."],
        "binary_search": ["Write down low, high, and mid for the failing target.", "After checking mid, ensure the remaining interval excludes mid and gets smaller.", "Use an inclusive interval with low <= high; update low to mid + 1 or high to mid - 1."],
        "max_subarray": ["Trace the running sum through the failing values.", "A negative prefix may be worse than starting a fresh subarray at the next value.", "At each value, compare starting fresh with extending the current sum, then update the best sum."],
        "contains_duplicate": ["Check how your code behaves with one item and with the same item twice.", "Compare the number of distinct values with the original list length.", "Return whether the set size differs from the list size."],
        "reverse_string": ["Trace the left and right indices on a list of length one and length two.", "Stop once the two indices meet; swap the elements at those positions.", "Use left < right, swap in place, move both pointers inward, and return the list."],
        "fizz_buzz": ["Test a value divisible by both 3 and 5.", "Check the combined multiple before checking either individual multiple.", "Use if divisible by 15, elif by 3, elif by 5, else the number as a string."],
        "merge_sorted": ["Try one empty list and one non-empty list.", "The main merge loop ends when either pointer reaches its list's end; the other tail still matters.", "After the comparison loop, append the remaining slice from both inputs."],
        "climb_stairs": ["List the answers for 1, 2, and 3 steps and compare them to your initial state.", "The number of ways at n is the sum of the previous two counts.", "Use base counts for n=1 and n=2, then iterate forward with a two-value recurrence."],
        "first_unique": ["Check a string where every character repeats and one where the first character is unique.", "Count all characters first, then scan the original string in order.", "Return the index of the first character with count one; return -1 if none exists."],
    }
    return specific.get(pid, ["Focus on the smallest failing input.", "Trace the relevant branch using the expected and actual values.", diagnosis])


def complexity_note(code: str, pid: str) -> str:
    try:
        tree = ast.parse(code)
        loops = sum(isinstance(n, (ast.For, ast.While)) for n in ast.walk(tree))
        if loops >= 2:
            return "Static scan found nested or multiple loops. This is only a rough structural signal; review whether they are nested and measure on growing inputs."
        if loops == 1:
            return "Static scan found a loop. Runtime is likely at least linear in the iterated input, but this prototype does not infer data-structure costs or run timing trials."
        return "No loop was found by the simple static scan. Calls to built-ins or recursion can still do substantial work; confirm with code review and measurements."
    except SyntaxError:
        return "Complexity could not be estimated because the code did not parse."


class Handler(BaseHTTPRequestHandler):
    def _send(self, data: bytes, status: int = 200, kind: str = "application/json") -> None:
        self.send_response(status)
        self.send_header("Content-Type", kind + "; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Content-Security-Policy", "default-src 'self' 'unsafe-inline'; connect-src 'self'")
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self) -> None:
        if self.path == "/":
            self._send(PAGE.encode(), kind="text/html")
        elif self.path == "/api/problems":
            info = [{k: v for k, v in p.items() if k not in {"tests", "reference"}} for p in PROBLEMS]
            self._send(json.dumps(info).encode())
        else:
            self._send(b'{"error":"Not found"}', 404)

    def do_POST(self) -> None:
        if self.path != "/api/debug":
            self._send(b'{"error":"Not found"}', 404)
            return
        if int(self.headers.get("Content-Length", "0")) > 50000:
            self._send(b'{"error":"Request too large"}', 413)
            return
        try:
            data = json.loads(self.rfile.read(int(self.headers.get("Content-Length", "0"))))
            problem = next(p for p in PROBLEMS if p["id"] == data.get("problem"))
            code = data.get("code", "")
            if not isinstance(code, str) or not code.strip():
                raise ValueError("Paste a Python function first.")
            result = analyze(problem, code, str(data.get("question", ""))[:1000])
            self._send(json.dumps(result).encode())
        except StopIteration:
            self._send(b'{"error":"Unknown problem"}', 400)
        except (ValueError, json.JSONDecodeError) as exc:
            self._send(json.dumps({"error": str(exc)}).encode(), 400)
        except Exception:
            self._send(b'{"error":"Analysis failed unexpectedly"}', 500)

    def log_message(self, fmt: str, *args: Any) -> None:
        print("[AlgoCoach] " + fmt % args)


def main() -> None:
    server = ThreadingHTTPServer(("127.0.0.1", PORT), Handler)
    print(f"AlgoCoach is available at http://127.0.0.1:{PORT}")
    print("Press Ctrl+C to stop. Code execution uses a restricted subprocess; do not expose this demo publicly.")
    threading.Timer(0.8, lambda: webbrowser.open(f"http://127.0.0.1:{PORT}")).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping AlgoCoach.")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
