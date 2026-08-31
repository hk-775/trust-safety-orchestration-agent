import { useMetricsStore } from '@/store/metricsStore'
import { useAuthStore } from '@/store/authStore'
import { StatusBadge } from './StatusBadge'
import { Link } from 'react-router-dom'
import { IS_PUBLIC_SITE } from '@/lib/publicSite'

export function Header() {
  const metrics = useMetricsStore((s) => s.metrics)
  const logout = useAuthStore((s) => s.logout)

  return (
    <header className="flex h-16 items-center justify-between border-b border-gray-200 bg-white px-6">
      <div className="flex items-center gap-4">
        {IS_PUBLIC_SITE && (
          <span className="inline-flex items-center gap-2 rounded-full bg-kelp/10 px-3 py-1 text-xs font-semibold text-kelp">
            <span className="h-2 w-2 rounded-full bg-kelp" />
            Synthetic public demo
          </span>
        )}
        {metrics?.elevated_threat_level && (
          <StatusBadge status="critical" label="ELEVATED THREAT" />
        )}
        {metrics && (
          <span className="text-sm text-gray-500">
            Queue: <span className="font-medium text-gray-900">{metrics.review_queue_depth}</span>
          </span>
        )}
      </div>

      {IS_PUBLIC_SITE ? (
        <Link
          to="/demo"
          className="rounded-lg border border-gray-200 px-3 py-1.5 text-sm font-medium text-gray-600 transition hover:bg-gray-50 hover:text-gray-900"
        >
          Guided scenario
        </Link>
      ) : (
        <button
          onClick={logout}
          className="text-sm text-gray-500 hover:text-gray-700 transition-colors"
        >
          Sign out
        </button>
      )}
    </header>
  )
}
