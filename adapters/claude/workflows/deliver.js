export const meta = {
  name: 'deliver',
  description: 'Run several requirements through the deliver gates in parallel, each in its own worktree',
  whenToUse:
    'You have 2+ independent requirements and want them all built, reviewed and tested ' +
    'without supervision. One requirement does not need this — run /deliver:feature instead.',
  phases: [
    { title: 'Frame', detail: 'requirement -> numbered binary acceptance criteria' },
    { title: 'Build', detail: 'design + implement in an isolated worktree' },
    { title: 'Review', detail: 'independent reviewer, bounded fix loop' },
    { title: 'Test', detail: 'qa subagent writes tests, the runner executes them' },
    { title: 'Report', detail: 'one report per requirement, plus a roll-up' },
  ],
}

// args: ["requirement one", "requirement two", ...]  — or a single string.
const REQUIREMENTS = (Array.isArray(args) ? args : [args]).filter(Boolean)

if (!REQUIREMENTS.length) {
  log('No requirements passed. Call with args: ["build X", "build Y"].')
  return { delivered: [] }
}

log(`${REQUIREMENTS.length} requirement(s) — each gets its own worktree and its own review.`)

const CRITERIA = {
  type: 'object',
  required: ['slug', 'criteria', 'assumptions'],
  properties: {
    slug: { type: 'string', description: 'kebab-case, <= 4 words, derived from the requirement' },
    criteria: {
      type: 'array',
      items: {
        type: 'object',
        required: ['id', 'statement'],
        properties: {
          id: { type: 'string' },
          statement: { type: 'string', description: 'binary — true or false on inspection' },
        },
      },
    },
    assumptions: { type: 'array', items: { type: 'string' } },
    ambiguous: {
      type: 'boolean',
      description: 'true only if two readings would produce materially different systems',
    },
  },
}

const OUTCOME = {
  type: 'object',
  required: ['verdict', 'summary'],
  properties: {
    verdict: { type: 'string', enum: ['PASS', 'PASS_WITH_CONDITIONS', 'BLOCKED'] },
    summary: { type: 'string' },
    branch: { type: 'string' },
    reportPath: { type: 'string' },
    criteriaMet: { type: 'number' },
    criteriaTotal: { type: 'number' },
    testsPassed: { type: 'number' },
    testsFailed: { type: 'number' },
    outstanding: { type: 'array', items: { type: 'string' } },
  },
}

// Pipeline, not parallel-with-barriers: requirement B should not wait for A's review
// just because A's build was slower. Each requirement runs its own chain end to end.
const results = await pipeline(
  REQUIREMENTS,

  // ── Gate 0 · Frame ────────────────────────────────────────────────────────
  (req) =>
    agent(
      `Gate 0 of the deliver skill. Requirement:\n\n${req}\n\n` +
        `Read the deliver skill's reference/gates.md, then produce ONLY gate 0: a kebab-case ` +
        `slug, numbered binary acceptance criteria (AC1, AC2, ...), and any assumptions not ` +
        `settled by the requirement. Include the negative cases the requirement implies — ` +
        `empty input, upstream failure, unauthorised caller. Then dispatch the critic ` +
        `subagent — give it the requirement, the criteria and the exclusions, NOT your ` +
        `reasoning — and resolve every finding into a criterion or a stated exclusion. Set ` +
        `ambiguous if it returns a BLOCKING gap you cannot settle by assumption. Write ` +
        `docs/specs/<slug>/requirements.md from the skill's template. Do not design and do ` +
        `not write code. Set ambiguous only if two readings would produce materially ` +
        `different systems.`,
      { label: 'frame', phase: 'Frame', schema: CRITERIA },
    ),

  // ── Gates 1-7 · Ground, Design, Tasks, Build, Review, Fix, Test ───────────
  // isolation: worktree so concurrent requirements cannot collide on the same files.
  (framed, req, i) => {
    if (!framed) return null
    if (framed.ambiguous) {
      log(`[${i + 1}] "${framed.slug}" is ambiguous — skipped, needs a human answer first.`)
      return { verdict: 'BLOCKED', summary: 'Requirement ambiguous at gate 0; not started.' }
    }
    const acs = framed.criteria.map((c) => `${c.id}: ${c.statement}`).join('\n')
    return agent(
      `Run gates 1 through 7 of the deliver skill for this requirement.\n\n` +
        `REQUIREMENT:\n${req}\n\n` +
        `ACCEPTANCE CRITERIA (fixed — do not renegotiate, do not narrow):\n${acs}\n\n` +
        `ASSUMPTIONS ALREADY MADE:\n${(framed.assumptions || []).join('\n') || '(none)'}\n\n` +
        `Gate 0 already ran and wrote docs/specs/${framed.slug}/requirements.md. Load it ` +
        `rather than re-deriving it.\n\n` +
        `Read the deliver skill's reference/gates.md and follow it exactly. Specifically:\n` +
        `- Gate 1: load the guidelines for this repo type, plus service-structure if there is ` +
        `service code. Name them in the report. This gate produces context, not a document — ` +
        `run it even though gate 0 already ran.\n` +
        `- Gates 2 and 3: write docs/specs/${framed.slug}/design.md and tasks.md from the ` +
        `skill's templates, each stamped with its upstream's git hash-object hash.\n` +
        `- Gate 4: work on branch deliver/${framed.slug}. Zero TODOs in delivered code.\n` +
        `- Gate 5: dispatch the reviewer subagent. Record its verdict VERBATIM.\n` +
        `- Gate 6: at most 3 fix rounds. On a fourth FAIL, stop and return BLOCKED.\n` +
        `- Gate 7: dispatch the qa subagent, then RUN the tests and keep the real output.\n` +
        `Never weaken a test or a criterion to reach green. Do not push, open a PR, deploy ` +
        `or touch CI.\n\n` +
        `Return the outcome. Write the full report at gate 8 to ` +
        `docs/specs/${framed.slug}/report.md.`,
      {
        label: `deliver:${framed.slug}`,
        phase: 'Build',
        isolation: 'worktree',
        schema: OUTCOME,
      },
    ).then((out) => (out ? { ...out, slug: framed.slug, requirement: req } : null))
  },
)

const delivered = results.filter(Boolean)
const blocked = delivered.filter((d) => d.verdict === 'BLOCKED')

log(
  `Done — ${delivered.length - blocked.length} of ${REQUIREMENTS.length} passed review, ` +
    `${blocked.length} blocked.`,
)

// The roll-up exists because the user was not watching. Blocked runs go first:
// they are the ones needing a decision.
return {
  passed: delivered.filter((d) => d.verdict !== 'BLOCKED'),
  blocked,
  needsAttention: blocked.map((d) => ({
    slug: d.slug,
    why: d.summary,
    outstanding: d.outstanding || [],
  })),
}
