import { APP_DESCRIPTION, APP_NAME } from '@/app/app-info'

/** The one feature this repo ships with — a worked example of the pattern, and
 * the page a fresh scaffold renders.
 *
 * It is deliberately static. Delete it once you have a real first feature;
 * copying it as a starting point is fine, keeping it forever is not. */
export function OverviewPage() {
  return (
    <div className="mx-auto max-w-3xl p-8">
      <h1 className="text-2xl font-semibold">{APP_NAME}</h1>
      <p className="text-muted-foreground mt-2">{APP_DESCRIPTION}</p>

      <div className="border-border mt-8 rounded-lg border p-6">
        <h2 className="font-medium">Building the first feature</h2>
        <ol className="text-muted-foreground mt-3 list-decimal space-y-2 pl-5 text-sm">
          <li>
            <code>npm run setup</code> once, to vendor the shadcn/ui components into{' '}
            <code>src/shared/ui/</code>.
          </li>
          <li>
            Create <code>src/features/&lt;name&gt;/</code> with{' '}
            <code>components/ hooks/ api/ types/</code> and an <code>index.ts</code> that
            default exports the page.
          </li>
          <li>
            Add one entry to <code>src/app/registry.ts</code>. Navigation and routing both
            follow from it — no shell file is edited.
          </li>
          <li>
            Fetch through <code>src/shared/api/client.ts</code>, which parses every response
            with Zod and calls the same-origin <code>/api</code> path.
          </li>
          <li>
            Read <code>docs/REACT_STANDARDS.md</code>, and check your work against{' '}
            <code>docs/REACT_STANDARDS_CONFORMANCE.md</code> before you open the merge request.
          </li>
        </ol>
      </div>
    </div>
  )
}
