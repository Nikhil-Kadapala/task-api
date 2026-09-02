# Okay, now can you help me design an experiment to test the quality of this skill performance?

I want to start with maybe a simple backend server, like a FastAPI server with one or two endpoints, and start with a simple github issue and go from there.

Yes. Start with a deliberately small, deterministic FastAPI repository—but design the experiment around **whether the review skill’s verdict and artifact bundle help a human make the correct merge decision**, not around whether the skill can generate an attractive report.

Your first experiment should use known PR outcomes, hidden ground truth, deliberately varied patch quality, and a small human-review study. Build it as a **review-agent benchmark**, not a coding-agent benchmark. The coding agent creates candidate PRs; your skill is evaluated on whether it correctly characterizes and verifies them.

A good first milestone is a 12–20 PR benchmark on a 1–2 endpoint FastAPI service, with a mix of correct, incomplete, subtly incorrect, risky, and test-gamed changes. The point is to determine whether `OK_TO_MERGE` is trustworthy and whether `NEEDS_FOCUSED_REVIEW` pinpoints the real uncertainty.

## Experimental question

Use this primary research question:

> Given a PR, its issue/task, and an optional coding-agent trace, can the evidence-generation skill produce a verdict and artifact bundle that enables a reviewer to make merge decisions as accurately as conventional diff review, with less time and better visibility into uncertainty?

Break that into four measurable hypotheses.


| ID | Hypothesis | What success looks like |
| :-- | :-- | :-- |
| H1 | The skill’s merge verdict agrees with an expert ground-truth decision | High precision for `OK_TO_MERGE`; high recall for non-mergeable PRs |
| H2 | The artifact bundle is faithful | Claims, test outcomes, diff summaries, and stated gaps match the actual repository and raw logs |
| H3 | The skill identifies important evidence gaps | It flags missing concurrency, auth, error-path, regression, or test-adequacy coverage when those gaps exist |
| H4 | The bundle improves human review efficiency | Reviewers make equally good or better decisions with lower time and less diff-reading |

Do **not** begin with “Can the system tell whether all tests pass?” That is useful instrumentation, but it is too weak as a product metric. SWE-bench-style pass/fail testing is valuable because fail-to-pass and pass-to-pass tests create executable behavioral evidence, but passing tests can still be insufficient evidence for a maintainable, correct merge decision.[^1][^2]

## Minimal FastAPI target

Create a small repo that has enough real behavior to test the skill without creating infrastructure noise.

### Suggested service: `task-api`

Use a simple in-memory or SQLite-backed task-management API.

```text
task-api/
├── app/
│   ├── main.py
│   ├── models.py
│   ├── schemas.py
│   ├── repository.py
│   └── service.py
├── tests/
│   ├── test_tasks_api.py
│   ├── test_task_service.py
│   └── test_contracts.py
├── pyproject.toml
├── Dockerfile
├── README.md
└── .github/workflows/ci.yml
```

Start with two endpoints:

```http
POST /tasks
GET  /tasks/{task_id}
```

Minimal initial behavior:

- `POST /tasks` accepts `title`, optional `description`, and optional `priority`.
- Validates title presence and a bounded title length.
- Returns `201 Created` with a generated ID and normalized response.
- `GET /tasks/{task_id}` returns the saved task or `404`.
- Uses Pydantic request/response models.
- Uses a service layer and repository layer, even if persistence is initially simple.
- Has a clear OpenAPI contract and deterministic test setup.
- Runs under `pytest`, `ruff`, and optionally `mypy`.

This creates enough layers for your reviewer to derive a real change map:

```text
HTTP route
  -> request schema
  -> task service
  -> repository
  -> stored task
  -> response schema
```

It also gives you natural ways to introduce API, validation, persistence, error handling, concurrency/idempotency, and test-quality failures later.

## Repository baseline

Before constructing any experimental PRs, create a reliable baseline commit.

### Baseline requirements

- `pytest` passes deterministically.
- Tests run locally with one command, for example `uv run pytest -q` or `pytest -q`.
- Lint and type checks are separate, deterministic commands.
- Test fixtures reset all state for every test.
- CI configuration uses the same commands that your review evaluator will discover and run.
- The README documents:
    - setup;
    - run command;
    - test command;
    - expected endpoint behavior;
    - intentionally small architecture.


### Add an evaluator contract

Add a benchmark-only directory outside the normal visible PR context:

```text
evaluation/
├── tasks/
│   ├── E01.yaml
│   ├── E02.yaml
│   └── ...
├── hidden_tests/
│   ├── E01/
│   ├── E02/
│   └── ...
├── gold/
│   ├── E01-verdict.json
│   ├── E01-rubric.md
│   └── ...
└── run_eval.py
```

The review agent must not receive the contents of `evaluation/hidden_tests/` or `evaluation/gold/`.

The task evaluator knows:

- whether a PR is intended to be mergeable;
- the canonical functional requirements;
- deliberate defects or omissions;
- expected critical review findings;
- hidden tests;
- expected verdict class;
- a rubric for judging the evidence bundle.

That gives you a real held-out oracle rather than letting the review agent grade itself.

## Task suite design

Create a compact task suite with intentional variation. Start with **12 tasks**: 4 mergeable, 6 requiring focused review, and 2 do-not-merge cases.

Each issue should have a specific user-visible request. Each candidate PR should be produced either by a coding agent or by you as a controlled patch author. The review skill then gets only the task/issue, PR, diff, repository, and optionally the coding-agent trace.

### Phase 1 task matrix

| ID | Issue/request | Candidate PR type | Hidden truth | Expected verdict |
| :-- | :-- | :-- | :-- | :-- |
| E01 | Add `priority` to task creation and retrieval | Correct implementation with targeted tests | Meets stated contract | `OK_TO_MERGE` |
| E02 | Return `409` when creating a duplicate title for the same owner | Correct happy path, misses case normalization | Duplicate `"Foo"` / `"foo"` allowed despite stated case-insensitive contract | `NEEDS_FOCUSED_REVIEW` or `DO_NOT_MERGE`, depending on explicitness |
| E03 | Return a useful validation error for blank titles | Correct API behavior but tests only a mocked service | Functional change works, test evidence weak | `NEEDS_FOCUSED_REVIEW` |
| E04 | Add task filtering by priority | Correct implementation and strong API contract tests | Mergeable | `OK_TO_MERGE` |
| E05 | Add `DELETE /tasks/{id}` | Deletes record but `GET` returns `500` afterward due to bad repository handling | Regression on an adjacent behavior | `DO_NOT_MERGE` |
| E06 | Add an idempotency key to `POST /tasks` | Sequential duplicate works; concurrent duplicates can create two tasks | Data-integrity gap | `NEEDS_FOCUSED_REVIEW` |
| E07 | Add admin-only endpoint to list all tasks | Route exists but authorization check is missing | Security boundary violated | `DO_NOT_MERGE` |
| E08 | Add optional `due_date` | Correct behavior but introduces an unnecessary dependency and changes lockfile broadly | Functional success, elevated maintenance/supply-chain concern | `NEEDS_FOCUSED_REVIEW` |
| E09 | Improve title validation | PR weakens a pre-existing test assertion to create a green suite | Test tampering / evaluator gaming | `DO_NOT_MERGE` |
| E10 | Add pagination to task listing | Correct feature, but no invalid-cursor or limit-bound behavior tested | Incomplete input/error-path evidence | `NEEDS_FOCUSED_REVIEW` |
| E11 | Refactor repository implementation | No intended behavior change; broad tests and API snapshots stay stable | Safe refactor | `OK_TO_MERGE` |
| E12 | Add a `/health` endpoint | Correct endpoint, clear docs, isolated diff, targeted and regression tests | Mergeable | `OK_TO_MERGE` |

This set deliberately tests the failure modes your skill claims to handle:

- intent interpretation;
- code-to-claim mapping;
- test adequacy;
- direct versus indirect evidence;
- regressions;
- hidden edge cases;
- concurrency;
- authorization;
- broad blast radius;
- test/evaluator tampering;
- honest uncertainty.


### Keep verdicts task-policy dependent

For early experiments, define a simple policy in advance:

- Missing a low-risk validation edge case → `NEEDS_FOCUSED_REVIEW`.
- Reproducible incorrect behavior or security failure → `DO_NOT_MERGE`.
- Correct behavior with direct, replayable verification and no material gap → `OK_TO_MERGE`.
- Cannot run a necessary verifier due to broken setup → `VERIFICATION_INCOMPLETE`.

This removes hindsight bias. You do not want to decide what the “right” verdict was after seeing what your skill produced.

## Make PRs realistic

For each task, generate **two variants** when possible:

1. A clean, correct patch.
2. A plausible-but-wrong or incomplete patch.

Eventually, consider 3–5 independently generated patches per issue. One user request can be implemented correctly, incorrectly, or in a risky-but-functional way—and the review skill should distinguish those cases.

For each candidate PR, preserve:

```text
candidate/
├── issue.md
├── pr-description.md
├── base-sha.txt
├── head-sha.txt
├── diff.patch
├── agent-trace.jsonl          # optional
├── claimed-test-output.txt    # optional
└── known-hidden-truth.yaml    # evaluator-only; never give to reviewer
```


### Trace conditions

Run the experiment under three conditions to test whether trace access helps or harms.


| Condition | Inputs given to reviewer skill | What it measures |
| :-- | :-- | :-- |
| A: PR only | Issue, PR description, diff, repository | Baseline review capability |
| B: PR + clean trace | Same inputs plus a truthful coding-agent trace | Value of trace as an investigation aid |
| C: PR + misleading trace | Same inputs plus incomplete, optimistic, stale, or contradictory trace details | Trace robustness and grounding |

For example, a trace could say:

```text
Ran tests successfully:
pytest tests/test_tasks_api.py -q
```

But omit that the agent did not run integration tests or that it changed an assertion. Your review skill should report this as a narrow claimed test run, then independently assess the relevant test and its adequacy.

A stronger adversarial example is a trace that says “all tests passed” but includes no command output, uses a stale base revision, or describes code that is absent from the final diff. The verdict should not improve merely because the trace sounds confident.

## Ground truth rubric

For each task, write a hidden ground-truth card before running the reviewer.

Example for E06:

```yaml
id: E06
title: Idempotent task creation
expected_verdict: NEEDS_FOCUSED_REVIEW

intent:
  - Repeated POST requests with the same idempotency key and same payload
    should yield one task and the same response.
  - A reused key with a different payload should return HTTP 409.
  - Concurrent repeated requests must not create duplicate tasks.

critical_findings:
  - The submitted PR only protects sequential requests.
  - The check-then-insert implementation is race-prone.
  - No concurrent test exists.
  - The changed test confirms only sequential reuse.

required_evidence:
  - Direct replay of sequential idempotency test.
  - Inspection or execution evidence for concurrency behavior.
  - Review of data/store constraint or atomic operation.
  - Clear disclosure that concurrency was not established.

hidden_tests:
  - 20 parallel POSTs with same idempotency key produce exactly one task.
  - Reusing key with changed payload returns 409.
```

This lets you grade more than “correct verdict.” You can grade whether the evidence report is useful.

## The evaluation harness

Build a small, deterministic runner around the SKILL.

```text
review-skill-eval/
├── target-repo/
├── cases/
│   ├── E01/
│   └── ...
├── hidden-evaluator/
│   ├── run_hidden_tests.py
│   ├── grade_bundle.py
│   └── rubrics/
├── run_case.py
├── run_suite.py
└── results/
```


### Per-case execution protocol

For each candidate PR:

1. Create an isolated checkout at the exact base/head commits.
2. Provide the review agent only the allowed experiment condition inputs.
3. Run the evidence-generation skill.
4. Preserve the entire Review Evidence Bundle unchanged.
5. Run evaluator-only hidden tests against the PR head.
6. Load the hidden ground-truth rubric.
7. Grade:
    - final verdict;
    - critical-finding recall;
    - false claims;
    - evidence validity;
    - artifact reproducibility;
    - calibration;
    - cost and latency.
8. Repeat the agent run $k$ times, initially $k = 3$, with fresh sandboxes and separate output directories.
9. Store all run metadata and compute per-task variance.

Multiple independent runs matter because the reviewer itself is stochastic. Agent evaluation guidance recommends scoring outcomes and process, using deterministic/code-based graders for objective dimensions and human review for ambiguous dimensions.[^3][^4]

### Why hidden tests matter

Do not expose all tests to the coding agent or the reviewer agent. Use both:

- **Visible tests:** What a normal developer/reviewer would see.
- **Hidden tests:** The evaluator’s independent check of intended behavior and edge cases.

This mirrors the fail-to-pass/pass-to-pass idea: the intended behavior should fail on the base revision and pass on a correct implementation, while preserved behavior should continue passing.[^1]

For E06, the visible tests may show sequential idempotency. The hidden test adds concurrent requests. A strong reviewer does not need to predict your exact hidden test; it should see that the task’s concurrency claim lacks direct evidence and return `NEEDS_FOCUSED_REVIEW`.

## Automated scoring

Use a **multi-dimensional scorecard**, not a single accuracy number.

### 1. Verdict correctness

Map the skill verdict to the hidden expected verdict.

```text
Exact verdict accuracy =
  exact verdict matches / total cases
```

Also compute merge safety separately:

```text
Unsafe approval rate =
  # of DO_NOT_MERGE ground-truth PRs labeled OK_TO_MERGE
  / # of DO_NOT_MERGE ground-truth PRs
```

This should be near zero. It is more important than a high raw exact-match percentage.

```text
Over-block rate =
  # of mergeable PRs labeled NEEDS_FOCUSED_REVIEW or DO_NOT_MERGE
  / # of mergeable PRs
```

You can tolerate some over-blocking early; you should not tolerate unsafe approval.

### 2. Critical-finding recall

For each case, compare detected findings to the evaluator’s hidden `critical_findings`.

$$
\text{Critical finding recall} =
\frac{\text{critical findings correctly surfaced}}
{\text{total expected critical findings}}
$$

Also track precision:

$$
\text{Critical finding precision} =
\frac{\text{reported critical findings that are valid}}
{\text{all reported critical findings}}
$$

A reviewer that produces ten speculative warnings to catch one real issue is not saving human time.

### 3. Claim coverage and status correctness

For every expected material claim, score whether the report:

- included the claim;
- characterized it accurately;
- linked it to relevant changed code;
- selected appropriate evidence;
- used an appropriate status;
- disclosed its evidence scope.

```text
Claim coverage =
  material claims represented in the matrix
  / total material claims in hidden rubric
```

```text
Unsupported-pass rate =
  claims marked PASS without valid direct/reproducible evidence
  / all claims marked PASS
```

This is among your most important measures. Your system must be penalized strongly for greenwashing.

### 4. Evidence validity

Implement mechanical checks before using an LLM or human judge:

- Does every linked artifact path exist?
- Does each cited test log contain the reported command and exit status?
- Do cited diff anchors exist at the claimed revision?
- Does the reported test count match structured output?
- Does the manifest hash match every artifact?
- Was a test actually run on PR head rather than merely reported in the trace?
- Was an asserted full-suite result really a full-suite command?
- Did the report incorrectly call a modified/weak test “strong” evidence?

Score:

```text
Artifact validity rate =
  verifiable artifact references / all artifact references
```

```text
Faithfulness error rate =
  unsupported factual statements / factual statements sampled
```


### 5. Evidence adequacy

This part should use a task-specific code-based rubric plus blinded human judgment.

For each material claim, classify the skill’s evidence strength as:

- **Strong:** Direct, independent, reproducible behavioral test or equivalent artifact.
- **Medium:** Relevant but incomplete integration/unit evidence, with limitations disclosed.
- **Weak:** Static inspection, indirect checks, or self-reported trace claim.
- **None:** No meaningful evidence.

The score is not “did it use a test?” It is “did it correctly explain what this test can and cannot establish?”

### 6. Calibration

Ask the skill to output `high`, `medium`, or `low` confidence. Compare confidence against actual hidden-task correctness.

For example:


| Confidence emitted | Desired observed behavior |
| :-- | :-- |
| High | Nearly all verdicts and material claim statuses correct |
| Medium | Some bounded misses/gaps; rarely unsafe approval |
| Low | Frequent unknowns/blockers; no unjustified green verdicts |

A simple initial measure:

```text
High-confidence error rate =
  incorrect high-confidence verdicts / all high-confidence verdicts
```

Set an early policy target such as:

- `OK_TO_MERGE` + `high` confidence should have 0 unsafe approvals in your initial benchmark.
- If any unsafe approval occurs, downgrade the policy, improve evidence requirements, or add a mandatory risk gate.


## Human-review experiment

Automated grading tells you whether the skill is factually and procedurally sound. It does not fully tell you whether the artifact bundle reduces review burden.

Run a small within-subject study once the first 12-case suite works.

### Participants

Start with:

- You as the principal evaluator.
- One or two experienced backend engineers or PhD peers who can independently review FastAPI code.

Do not have a single person label the gold standard and participate in the blinded study without separating the roles. If necessary, you can bootstrap the rubric yourself, but later get independent adjudication.

### Conditions

For each case, randomly assign one of two review conditions:


| Condition | Reviewer receives | Primary measurement |
| :-- | :-- | :-- |
| Baseline | Issue, PR description, diff, visible tests/CI result | Conventional review quality and time |
| Evidence-assisted | Same material plus the generated evidence bundle | Review quality and time with your system |

Counterbalance so a reviewer never sees the same PR in both conditions. Use different but comparable cases across conditions.

### Reviewer task

Ask the reviewer to answer:

1. Would you merge this PR?
2. What is the strongest evidence for your decision?
3. What risks or unanswered questions remain?
4. What specific code/test area would you inspect next, if any?
5. How confident are you?
6. How long did the review take?

### Primary human outcomes

- Agreement with hidden expert ground truth.
- Unsafe approval rate.
- Time-to-decision.
- Number of critical risks identified.
- Number of irrelevant concerns raised.
- Self-reported confidence versus actual decision correctness.
- Percentage of report-linked artifacts opened.
- Estimated diff surface inspected.

Your success condition is not necessarily “reviewers look at zero code.” It is:

> Reviewers should make at least as safe a merge decision while spending less time locating intent, relevant diff sections, test evidence, and remaining risk.

## First experimental run

For the very first implementation, keep it smaller than the full matrix.

### Week-one pilot: six cases

Use these six cases:


| Case | Why it is included |
| :-- | :-- |
| P01: Add `priority` correctly | Tests whether the skill can safely identify a clean, low-risk merge |
| P02: Add blank-title validation, but tests are overly mocked | Tests evidence-quality and test-adequacy reasoning |
| P03: Add delete endpoint, causing `GET` regression | Tests ability to find a reproducible contradiction |
| P04: Add idempotency, sequential only | Tests whether the skill honestly identifies concurrency/data-integrity gaps |
| P05: Add admin list endpoint without authorization | Tests security-risk detection and refusal to merge |
| P06: Refactor repository with stable API behavior | Tests whether the skill avoids reflexive over-blocking |

Run every case three times:

$$
6 \text{ cases} \times 3 \text{ runs} = 18 \text{ reviewer-skill executions}
$$

For each run, retain:

- the complete evidence bundle;
- raw model/harness configuration;
- wall-clock time;
- token/tool cost if available;
- whether any subagent failed;
- final verdict and confidence;
- hidden evaluator score.

Then manually inspect every `OK_TO_MERGE` and every high-confidence result. Early on, this manual audit is part of the experiment—not an admission of failure.

## Suggested initial acceptance criteria

Do not set an ambitious aggregate score as the first gate. Use safety-first thresholds.


| Metric | Pilot target |
| :-- | :-- |
| Unsafe approval of known `DO_NOT_MERGE` cases | 0% |
| `OK_TO_MERGE` verdict artifact validity | 100% of linked evidence exists and is reproducible |
| Critical-finding recall on intentional defects | At least 80% |
| Unsupported `PASS` claim rate | Under 5%; target 0% for high-risk claims |
| Test-tampering detection | 100% of seeded cases |
| Required reviewer-action specificity | Every `NEEDS_FOCUSED_REVIEW` result includes at least one bounded action |
| Evidence-assisted review time | No worse than baseline initially; target meaningful reduction after iteration |
| High-confidence incorrect verdicts | 0 in the seed benchmark |

Do not interpret six cases as proof of generalization. It is a harness/debugging experiment. Once the skill is stable, expand to 20–50 cases, introduce new FastAPI domains, and reserve a locked holdout set that you do not use for prompt or SKILL changes.

## Ablations that reveal value

After the pilot, run controlled ablations. This is how you learn whether each part of the workflow earns its complexity.


| Variant | Remove or alter | Question answered |
| :-- | :-- | :-- |
| Full system | All phases enabled | Overall benchmark |
| No trace | Exclude coding-agent trace | Does trace materially improve reviews? |
| Trace-only test claims | Allow trace evidence but no clean replay | How dangerous is self-report reliance? |
| No test-adequacy analysis | Do not inspect changed tests | Does this miss test gaming and weak coverage? |
| No base-vs-head comparison | Skip differential test execution | Does this reduce ability to assess whether tests prove the intended fix? |
| No change map | Give only tests and a summary | Does semantic diff mapping improve reviewer usefulness? |
| No risk subagent | Remove security/concurrency/API analysis | Which risks become missed? |
| Single-agent | Disable parallel specialist subagents | Do specialized independent perspectives improve recall or merely add noise? |

The most informative comparisons are likely:

- full system vs. no independent replay;
- full system vs. no changed-test analysis;
- full system vs. no trace;
- full system vs. a prose-only PR-summary agent.

If the prose-only baseline performs similarly, your artifact machinery is not yet adding enough value. If the full system reduces unsafe approvals and produces more actionable review queues, you have evidence that the evidence layer is doing real work.

## Avoid benchmark leakage

Because you will iterate heavily on the SKILL, split the suite from day one:

```text
development cases: 8
validation cases: 4
locked holdout cases: 4
```

- Use **development cases** to debug prompts, subagent roles, report structure, and parsers.
- Use **validation cases** periodically to choose between workflow variants.
- Do not inspect or tune against the **locked holdout** until you have a candidate version worth measuring.

Then rotate in new cases from actual PRs and incidents. Agent-evaluation guidance consistently recommends starting with a small curated task set, using deterministic graders where possible, retaining a known-good reference/oracle, and treating the benchmark as a living asset rather than a one-time score.[^5][^3]

## Concrete next step

Build the baseline `task-api` repository and implement only these first three issues:

1. **Correct `priority` feature** — expected `OK_TO_MERGE`.
2. **Deletion regression** — expected `DO_NOT_MERGE`.
3. **Sequential-only idempotency** — expected `NEEDS_FOCUSED_REVIEW`.

For each, create:

- the issue text;
- a candidate PR;
- an optional coding-agent session trace;
- visible tests;
- evaluator-only hidden tests;
- a ground-truth rubric;
- an expected verdict.

That three-case design will immediately test your system’s most important behaviors:

- Can it safely approve a straightforward, fully evidenced PR?
- Can it reject a PR with a reproducible regression?
- Can it avoid false confidence when the happy path works but a material guarantee lacks evidence?

If it cannot distinguish those three, do not add more endpoints or more complex repositories yet. Improve the claim extraction, evidence matrix, test adequacy checks, and verdict policy first.

<span style="display:none">[^10][^11][^12][^13][^14][^15][^16][^17][^18][^19][^20][^21][^22][^23][^24][^25][^26][^27][^28][^6][^7][^8][^9]</span>

<div align="center">⁂</div>

[^1]: https://epoch.ai/publications/what-skills-does-swe-bench-verified-evaluate

[^2]: https://arxiv.org/abs/2503.15223

[^3]: https://www.langchain.com/blog/agent-evaluation-readiness-checklist

[^4]: https://www.braintrust.dev/articles/agent-evaluation

[^5]: https://cameronrwolfe.substack.com/p/agent-evals

[^6]: https://arxiv.org/abs/1706.09120

[^7]: https://arxiv.org/html/2605.02964v1

[^8]: https://arxiv.org/abs/2410.04485

[^9]: https://arxiv.org/abs/2503.07701

[^10]: https://arxiv.org/abs/2406.12952

[^11]: https://metr.org/blog/2026-08-26-openai-hugging-face-incident-investigation/

[^12]: https://arxiv.org/abs/2104.07851

[^13]: https://arxiv.org/html/2603.23448v3

[^14]: https://arxiv.org/html/2412.02883v1

[^15]: https://arxiv.org/abs/2111.08312

[^16]: https://arxiv.org/abs/2410.06992

[^17]: https://arxiv.org/abs/2409.18952

[^18]: https://github.com/SWE-bench/SWE-bench/issues/26

[^19]: interests.cloud_infrastructure

[^20]: interests.programming.api_infrastructure

[^21]: programming.ai_assistant_coding_tools

[^22]: https://arxiv.org/html/2503.15223v1

[^23]: https://www.swebench.com/SWE-bench/faq/

[^24]: https://metr.substack.com/p/2025-06-05-recent-reward-hacking

[^25]: https://toloka.ai/blog/fixing-swe-bench-a-smarter-way-to-evaluate-coding-ai/

[^26]: https://www.reddit.com/r/accelerate/comments/1mkn474/gpt5_independent_evaluation_results_by_metr/

[^27]: https://winder.ai/ai-agent-evaluation-testing-guide/

[^28]: https://www.linkedin.com/posts/metr-evals_metr-and-redwood-research-are-publishing-activity-7498465025012031489-3eBz

