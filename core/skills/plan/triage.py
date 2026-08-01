#!/usr/bin/env python3
"""Shortlist what can be deferred and what should be pulled earlier, so the critical work
sits at the START of the plan and anything that merely improves the outcome sits at the end.

This proposes; a human decides. It reports the mechanical facts a triage decision needs and
refuses to guess the judgement. "Nothing depends on it" is a WEAK signal on its own —
tests, runbooks and sign-off are leaves by nature and are all mandatory — so candidates are
tiered rather than lumped together:

  CANNOT DEFER        something depends on it, or another task's acceptance criterion names
                      it. Deferring drags the subtree along, or strands a task that can
                      never be signed off.
  DEFERRING ORPHANS   named elsewhere as a risk mitigation or as checklist evidence.
                      Allowed, but that risk or line becomes silently false and must be
                      rewritten in the same change.
  ENHANCEMENT         P2/P3, nothing depends on it, nothing cites it. The real shortlist.
  ASSURANCE LEAF      P0/P1 with no dependents. Mechanically removable, but priority says
                      required — deferring means explicitly accepting a risk, not tidying.
  PULL EARLIER        cheap task gating an expensive chain. Belongs in week 1 whatever its
                      priority says.
  MISPLACED           P2/P3 in the first phase, or P0/P1 late with no dependencies either
                      way (go-live work in the final phase is normal, not misplaced).
  PAIRS               one task's rationale names another — defer both or neither. One-way
                      is the common case: a control is pointless without what it controls.

    triage.py --backlog PLAN.xlsx
    triage.py --backlog PLAN.xlsx --spike-max 2 --chain-min 10
"""

import argparse
import sys
from collections import defaultdict
from functools import lru_cache
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from schedule import ID_RE, load, phase_order, wire  # noqa: E402

DEFERRABLE = {"P2", "P3"}
CRITICAL = {"P0", "P1"}
# Sheets whose prose, if it names a task, means deferring that task falsifies something.
ORPHAN_HINTS = ("risk", "checklist", "go-live", "golive", "gate")


def rule(title, n=78):
    print("\n" + "=" * n)
    print(title)
    print("=" * n)


def main():
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("--backlog", required=True)
    ap.add_argument("--sheet", default="02 Task Backlog")
    ap.add_argument(
        "--spike-max",
        type=float,
        default=2.0,
        help="a task this small or smaller counts as cheap (default 2 days)",
    )
    ap.add_argument(
        "--chain-min",
        type=float,
        default=10.0,
        help="downstream work this large counts as expensive (default 10 days)",
    )
    a = ap.parse_args()

    wb, sheet, _, _, _, tasks = load(a.backlog, a.sheet)
    kids, problems = wire(tasks)
    if problems:
        print("fix the dependency graph first:")
        for p in problems:
            print("  x " + p)
        sys.exit(1)
    _, named = phase_order(tasks)
    first_phase, last_phase = (named[0], named[-1]) if named else (None, None)

    @lru_cache(maxsize=None)
    def chain(tid):
        return tasks[tid]["days"] + max((chain(k) for k in kids[tid]), default=0)

    @lru_cache(maxsize=None)
    def subtree(tid):
        out = set()
        for k in kids[tid]:
            out.add(k)
            out |= subtree(k)
        return frozenset(out)

    # An acceptance criterion naming a task is a hard block: defer the named task and the
    # naming task can never be signed off. A rationale naming one is a softer pair signal.
    in_accept, in_why = defaultdict(set), defaultdict(set)
    for tid, t in tasks.items():
        for field, sink in (("accept", in_accept), ("why", in_why)):
            for ref in ID_RE.findall(t.get(field) or ""):
                if ref in tasks and ref != tid:
                    sink[ref].add(tid)

    # Risk mitigations and checklist evidence elsewhere in the workbook. This is the check
    # that catches the real hazard: deferring a task that WAS a control leaves the risk
    # reading as mitigated and the checklist line unverifiable.
    orphans = defaultdict(set)
    prefixes = {t.split("-")[0] for t in tasks}
    for name in wb.sheetnames:
        if name == sheet or not any(h in name.lower() for h in ORPHAN_HINTS):
            continue
        sh = wb[name]
        for r in range(1, sh.max_row + 1):
            for c in range(1, sh.max_column + 1):
                v = sh.cell(row=r, column=c).value
                if not isinstance(v, str):
                    continue
                for ref in ID_RE.findall(v):
                    if ref in tasks and ref.split("-")[0] in prefixes:
                        orphans[ref].add(
                            f"{name}!{sh.cell(row=r, column=c).coordinate}"
                        )

    total = sum(t["days"] for t in tasks.values())
    print(f"{len(tasks)} tasks · {total:g} days · {sheet!r}")
    scanned = [n for n in wb.sheetnames if any(h in n.lower() for h in ORPHAN_HINTS)]
    print(
        f"scanned for orphaned controls: {', '.join(scanned) if scanned else '(no risk/checklist sheet found)'}"
    )

    # ------------------------- classify -------------------------
    cannot, orphan_risk, enhancement, assurance = [], [], [], []
    for tid, t in sorted(tasks.items(), key=lambda x: -x[1]["days"]):
        sub = subtree(tid)
        if sub or in_accept[tid]:
            why = []
            if in_accept[tid]:
                why.append(
                    "acceptance criteria of " + ", ".join(sorted(in_accept[tid]))
                )
            if sub:
                why.append(
                    f"{len(sub)} dependent(s), {sum(tasks[x]['days'] for x in sub):g}d"
                )
            cannot.append((tid, t, sum(tasks[x]["days"] for x in sub), "; ".join(why)))
        elif orphans[tid]:
            orphan_risk.append((tid, t, sorted(orphans[tid])))
        elif t["prio"] in DEFERRABLE:
            enhancement.append((tid, t))
        else:
            assurance.append((tid, t))

    def row(tid, t, tail=""):
        print(
            f"  {tid:7}{t['days']:>5g}d {t['prio']:4} {t['phase']:9} {t['task'][:44]:46}{tail}"
        )

    rule(f"CANNOT DEFER ALONE — {len(cannot)} task(s)")
    print(
        "Deferring one drags its dependents with it, or strands a task that can never be"
    )
    print(
        "accepted. The days column below is its own size; the tail is what moves WITH it.\n"
    )
    for tid, t, _, why in sorted(cannot, key=lambda x: -x[2])[:12]:
        row(tid, t, why)
    if len(cannot) > 12:
        print(f"  … and {len(cannot) - 12} more")

    rule(f"DEFERRING THESE ORPHANS A CONTROL — {len(orphan_risk)} task(s)")
    print(
        "Each is named elsewhere as a risk mitigation or as checklist evidence. You may still"
    )
    print(
        "defer it, but the risk then reads as mitigated when it is not, and the checklist line"
    )
    print("asks for evidence nothing will produce. Rewrite both in the same change.\n")
    for tid, t, where in orphan_risk:
        row(
            tid,
            t,
            "cited by " + ", ".join(where[:3]) + (" …" if len(where) > 3 else ""),
        )
    if not orphan_risk:
        print("  (none)")

    etot = sum(t["days"] for _, t in enhancement)
    rule(f"ENHANCEMENT CANDIDATES — {len(enhancement)} task(s), {etot:g} days")
    print(
        "P2/P3, nothing depends on them, nothing cites them. This is the real shortlist —"
    )
    print("run each through reference/triage.md before cutting.\n")
    for tid, t in enhancement:
        pair = in_why[tid] | in_accept[tid]
        row(tid, t, ("PAIR? named by " + ", ".join(sorted(pair))) if pair else "")
    if not enhancement:
        print(
            "  (none — every leaf task is P0 or P1, so there is no easy scope to cut)"
        )

    atot = sum(t["days"] for _, t in assurance)
    rule(
        f"ASSURANCE LEAVES — NOT ENHANCEMENTS — {len(assurance)} task(s), {atot:g} days"
    )
    print(
        "P0/P1 with nothing depending on them. Removing one breaks no dependency, which is"
    )
    print(
        "exactly why this category is dangerous: tests, runbooks, penetration testing and"
    )
    print(
        "sign-off are leaves BY NATURE and all of them are required. Deferring one is"
    )
    print(
        "accepting a risk explicitly, not tidying the plan. Do not treat this list as scope.\n"
    )
    for tid, t in assurance[:14]:
        row(tid, t)
    if len(assurance) > 14:
        print(f"  … and {len(assurance) - 14} more")

    spikes = sorted(
        (
            (tid, t, chain(tid))
            for tid, t in tasks.items()
            if t["days"] <= a.spike_max and chain(tid) - t["days"] >= a.chain_min
        ),
        key=lambda x: -(x[2] - x[1]["days"]),
    )
    rule(f"PULL EARLIER — {len(spikes)} cheap task(s) gating expensive work")
    print(
        f"<={a.spike_max:g}d of effort in front of >={a.chain_min:g}d of dependent work. These are the"
    )
    print(
        "de-risking gates: prove them first whatever their priority says, because a problem"
    )
    print("found here late strands everything queued behind it.\n")
    for tid, t, ch in spikes:
        row(tid, t, f"gates {ch - t['days']:g}d")
    if not spikes:
        print("  (none)")

    mis = []
    for tid, t in tasks.items():
        # A P0 in the final phase is NORMAL when that phase is go-live hardening — runbooks
        # and penetration testing belong there. It is only suspicious when nothing forces it
        # late: no dependencies AND no dependents means it could have run any time.
        if (
            t["prio"] in CRITICAL
            and t["phase"] == last_phase
            and not subtree(tid)
            and not t["deps"]
        ):
            mis.append((tid, t, f"{t['prio']}, last phase, no deps either way — why so late?"))
        if t["prio"] in DEFERRABLE and t["phase"] == first_phase:
            mis.append((tid, t, f"{t['prio']} in the first phase — why not later?"))
    rule(f"MISPLACED — {len(mis)} task(s) where phase and priority disagree")
    print()
    for tid, t, why in mis:
        row(tid, t, why)
    if not mis:
        print("  (none — phase and priority agree throughout)")

    mutual, oneway = set(), set()
    for tid in tasks:
        for other in in_why[tid]:
            if tid in in_why[other] or tid in in_accept[other]:
                mutual.add(tuple(sorted((tid, other))))
            else:
                oneway.add((other, tid))
    oneway = sorted(x for x in oneway if tuple(sorted(x)) not in mutual)
    rule(f"PAIRS — {len(mutual)} mutual, {len(oneway)} one-way reference(s)")
    print("Defer both or neither, and write the RULE beside both rows — deferring half a pair")
    print("is how a plan acquires a hazard. One-way is the COMMON case and matters just as much:")
    print("a task whose only justification is containing another task's risk is pointless")
    print("without it, and dangerous to omit if that other task ever returns.\n")
    for x, y in sorted(mutual):
        print(f"  mutual    {x} <-> {y}   ({tasks[x]['days']:g}d + {tasks[y]['days']:g}d)")
    for x, y in oneway:
        print(f"  one-way   {x} ({tasks[x]['days']:g}d) justifies itself by naming {y}")
    if not mutual and not oneway:
        print("  (none inside the backlog — pairs already deferred live on the deferred sheet,")
        print("   where the RULE should already be written beside both rows)")
    print("\n" + "-" * 78)
    print(
        "Deferral is scope discipline, not a schedule lever. On the reference plan, cutting"
    )
    print(
        "24.5 days bought 0.7 weeks while re-levelling bought 2.7 with no cut at all. Defer to"
    )
    print(
        "deliver value earlier and keep the plan honest; use schedule.py --scenarios for duration."
    )


if __name__ == "__main__":
    main()
