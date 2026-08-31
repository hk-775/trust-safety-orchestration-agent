import { Link } from 'react-router-dom'
import { IS_PUBLIC_SITE, publicAsset } from '@/lib/publicSite'

export function ArchitecturePage() {
  return (
    <div className="min-h-screen bg-[#f7f4f8]" data-testid="architecture-page">
      <header className="border-b border-white/10 bg-[#17131c] text-white">
        <div className="mx-auto flex max-w-[1500px] flex-col gap-4 px-5 py-4 sm:flex-row sm:items-center sm:justify-between sm:px-8">
          <div className="flex items-center gap-4">
            <Link
              to="/"
              className="rounded-lg border border-white/15 bg-white/5 px-3 py-2 text-sm font-medium text-white/80 transition hover:bg-white/10 hover:text-white"
            >
              ← One pager
            </Link>
            <div>
              <h1 className="text-lg font-semibold">Interactive AWS architecture</h1>
              <p className="text-xs text-white/50">Select services or play the narrated orchestration path.</p>
            </div>
          </div>
          <div className="flex flex-wrap gap-2">
            <Link
              to="/demo"
              data-testid="architecture-guided-link"
              className="rounded-lg border border-white/15 px-3 py-2 text-sm font-medium text-white/80 transition hover:bg-white/10"
            >
              Guided case
            </Link>
            <Link
              to={IS_PUBLIC_SITE ? '/app' : '/login'}
              className="rounded-lg bg-white px-3 py-2 text-sm font-semibold text-[#24142f]"
            >
              Open dashboard
            </Link>
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-[1500px] px-3 py-4 sm:px-6">
        <div className="mb-3 rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-xs leading-5 text-amber-900">
          This walkthrough describes a reference topology. Integration availability, policy
          thresholds, latency, and downstream enforcement remain adopter-specific.
        </div>
        <iframe
          className="h-[820px] w-full rounded-2xl border border-gray-200 bg-white shadow-sm"
          data-testid="architecture-frame"
          src={publicAsset('architecture-demo.html')}
          title="SafetyAgent interactive architecture walkthrough"
        />
      </main>
    </div>
  )
}
