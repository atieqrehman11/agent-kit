# Agent — conformance checklist

The audit list for [`agent`](../agent.md). Walked by a reviewer, by the delivery gates, and by anyone auditing an existing supervisor.

This is payload, not a guideline: it carries no frontmatter and is never invocable. It lives apart from the rules so that whoever is *writing* code loads the rules without the checklist, and whoever is *auditing* loads the checklist without the rules. Every item below is defined in `agent.md` — read it there when a check needs interpreting.

**Instructions and tool descriptions are the product.** A diff touching only `instructions.md` or a tool `description` is a behaviour change with no compile step and no test to break — the routing and eval sections below are exactly the ones that must not be skipped for it. Skip any section with no matching surface in the diff; never flag its absence.

---

Layout and deploy:

- [ ] The supervisor is defined by `supervisor.yml` plus `instructions.md` — no per-agent Python and no hand-written tool loop.
- [ ] CI holds no logic of its own; each stage runs `validate.py` or `deploy.py`, so every gating check also runs locally.
- [ ] `deploy.py` calls the same `validate.check()` before touching a workspace.
- [ ] Tool attachment falls back from `create_tool` to `update_tool`, so a redeploy converges instead of erroring.
- [ ] Deploy prints the working query URL.

Identity:

- [ ] The repo stores **no supervisor id** — identity is `display_name` plus the authenticated workspace.
- [ ] Every environment is name-suffixed, prod included.
- [ ] Deploy resolves by name: one match updates, none creates, more than one is a hard failure.

Instructions:

- [ ] Routing rules are stated as **observable conditions**, not topics.
- [ ] Out-of-scope behaviour is explicit: what is declined, and what is said when declining.
- [ ] The grounding rule is stated — answer only from tool output, and say so when a tool returns nothing.
- [ ] A tie-break rule exists for the case where two tools both look applicable.
- [ ] One instruction per line, imperative — not prose paragraphs.

Tool descriptions:

- [ ] Each description says what the tool covers **and** what it does not.
- [ ] No two descriptions could match the same question; overlapping tools were merged or given discriminators.

Tool exposure and side effects:

- [ ] The attached tool set is the narrowest that covers the use case — every attached tool is reachable by any user who can reach the supervisor.
- [ ] Every tool is classified read-only or side-effecting in its `description`.
- [ ] Every side-effecting tool confirms before acting, **in the tool**, restating the resolved parameters — not via an instruction the supervisor is asked to emit.
- [ ] Every side-effecting invocation is audited at the tool: who asked, resolved parameters, what changed.
- [ ] Side-effecting tools are idempotent, or deduplicate on a caller-supplied key.
- [ ] Each tool's own credentials bound what it can reach; scope is on the principal, not the prompt.
- [ ] Where a draft-for-human-approval would serve the use case, it was preferred over acting directly.

Safety:

- [ ] Nothing relies on an instruction as a security control — anything a tool must not do, the tool refuses.
- [ ] Instructions state that retrieved content is data to summarise, never an instruction to follow.
- [ ] Access control lives on each tool's own resource under the supervisor's principal.
- [ ] Tool output is logged at DEBUG, never INFO.

Evaluation — the gate:

- [ ] A change to `instructions.md`, a tool `description`, or the attached tool list triggered a fresh eval run before merge.
- [ ] The pass rate is **at or above** the `CHANGELOG.md` baseline; any drop is recorded as a deliberate trade with its reason in the same commit.
- [ ] Eval asserts **which tool answered**, not only that the reply looked reasonable.
- [ ] Out-of-scope questions are covered and are declined per the instructions.
- [ ] A tool returning nothing produces a stated "I don't know" rather than a fallback to model knowledge.
- [ ] An injection case is covered: content saying "ignore your instructions" is reported, not obeyed.
- [ ] The set was run repeatedly and a pass rate recorded — not graded on a single run.
- [ ] `CHANGELOG.md` has a row for this deploy, and records whether routing, scope or grounding changed.

Observability and cost:

- [ ] One correlation id per turn, propagated into every tool call.
- [ ] Per turn, the tools called and their order, tokens in and out, per-tool latency and total turn latency are recorded.
- [ ] Ceilings on tools per turn, retries per tool and total turn latency come from configuration, not from the instructions.
- [ ] Alerting covers refusal rate, empty-tool-result rate and per-tool error rate.

---
