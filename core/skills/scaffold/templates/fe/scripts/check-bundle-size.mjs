// Bundle-size budget — a FAILING check, not a warning.
//
// Front-end bundles only ever grow, and they grow one reasonable-looking
// dependency at a time. A limit the build does not fail on is a preference; the
// point of this script is that adding 400kB of charting library has to be a
// decision someone makes on purpose, by raising the number below in a diff.
//
// Measured GZIPPED, because that is what the browser downloads. Raw size is
// shown alongside it only to make a bad compression ratio visible.
//
// Node built-ins only — it runs in CI before anything else is installed.

import { gzipSync } from 'node:zlib'
import { readFileSync, readdirSync, statSync } from 'node:fs'
import { join, extname } from 'node:path'

// The budget, in kilobytes of gzipped JS + CSS. Raise it deliberately, in a
// commit that says why.
const BUDGET_KB = Number(process.env.BUNDLE_BUDGET_KB || 300)

const DIST = 'dist'

function walk(dir) {
  const out = []
  for (const entry of readdirSync(dir)) {
    const path = join(dir, entry)
    if (statSync(path).isDirectory()) out.push(...walk(path))
    else out.push(path)
  }
  return out
}

let files
try {
  files = walk(DIST).filter((f) => ['.js', '.css'].includes(extname(f)))
} catch {
  console.error(`ERROR: no ${DIST}/ to measure — run \`npm run build\` first.`)
  process.exit(1)
}

if (files.length === 0) {
  console.error(`ERROR: ${DIST}/ contains no .js or .css — the build produced nothing.`)
  process.exit(1)
}

const measured = files
  .map((file) => {
    const raw = readFileSync(file)
    return { file, raw: raw.length, gz: gzipSync(raw).length }
  })
  .sort((a, b) => b.gz - a.gz)

const total = measured.reduce((sum, m) => sum + m.gz, 0)
const kb = (bytes) => (bytes / 1024).toFixed(1).padStart(8)

console.log('  gzipped       raw  file')
for (const m of measured) {
  console.log(`${kb(m.gz)}  ${kb(m.raw)}  ${m.file}`)
}
console.log(`${kb(total)}            TOTAL (budget ${BUDGET_KB.toFixed(1)} kB)`)

if (total > BUDGET_KB * 1024) {
  console.error(
    `\nERROR: bundle is ${(total / 1024).toFixed(1)} kB gzipped, over the ${BUDGET_KB} kB budget.` +
      `\n       Lazy-load the feature that grew, drop the dependency, or raise BUDGET_KB at the` +
      `\n       top of this file — but raise it in a commit that explains the trade.`,
  )
  process.exit(1)
}

console.log(`\n✓ within budget (${((total / 1024 / BUDGET_KB) * 100).toFixed(0)}% used)`)
