import { lazy, Suspense, useEffect } from 'react'
import {
  BrowserRouter,
  HashRouter,
  Navigate,
  Route,
  Routes,
} from 'react-router-dom'
import { useAuthStore } from '@/store/authStore'
import { useWebSocket } from '@/hooks/useWebSocket'
import { Layout } from '@/components/Layout'
import { LoginPage } from '@/components/LoginPage'
import { LoadingSpinner } from '@/components/LoadingSpinner'
import { LandingPage } from '@/pages/LandingPage'
import { ArchitecturePage } from '@/pages/ArchitecturePage'
import { IS_PUBLIC_SITE } from '@/lib/publicSite'
import type { ReactNode } from 'react'

const DemoPage = lazy(() =>
  import('@/modules/demo/DemoPage').then(({ DemoPage }) => ({ default: DemoPage })),
)
const DashboardPage = lazy(() =>
  import('@/modules/dashboard/DashboardPage').then(({ DashboardPage }) => ({
    default: DashboardPage,
  })),
)
const ReviewQueuePage = lazy(() =>
  import('@/modules/review/ReviewQueuePage').then(({ ReviewQueuePage }) => ({
    default: ReviewQueuePage,
  })),
)
const CasesListPage = lazy(() =>
  import('@/modules/case/CasesListPage').then(({ CasesListPage }) => ({
    default: CasesListPage,
  })),
)
const CaseDetailPage = lazy(() =>
  import('@/modules/case/CaseDetailPage').then(({ CaseDetailPage }) => ({
    default: CaseDetailPage,
  })),
)
const AdminConfigPage = lazy(() =>
  import('@/modules/admin/AdminConfigPage').then(({ AdminConfigPage }) => ({
    default: AdminConfigPage,
  })),
)
const WellbeingPage = lazy(() =>
  import('@/modules/wellbeing/WellbeingPage').then(({ WellbeingPage }) => ({
    default: WellbeingPage,
  })),
)
const GettingStartedPage = lazy(() =>
  import('@/modules/getting-started/GettingStartedPage').then(({ GettingStartedPage }) => ({
    default: GettingStartedPage,
  })),
)

function DeferredPage({ children }: { children: ReactNode }) {
  return <Suspense fallback={<LoadingSpinner />}>{children}</Suspense>
}

function ProtectedRoute({ children }: { children: ReactNode }) {
  const token = useAuthStore((s) => s.token)
  if (IS_PUBLIC_SITE) return <>{children}</>
  if (!token) return <Navigate to="/login" replace />
  return <>{children}</>
}

function AuthenticatedApp() {
  useWebSocket()

  useEffect(() => {
    document.documentElement.classList.remove('dark')
  }, [])

  return (
    <Routes>
      <Route element={<Layout />}>
        <Route
          index
          element={
            <DeferredPage>
              <DashboardPage />
            </DeferredPage>
          }
        />
        <Route
          path="review"
          element={
            <DeferredPage>
              <ReviewQueuePage />
            </DeferredPage>
          }
        />
        <Route
          path="cases"
          element={
            <DeferredPage>
              <CasesListPage />
            </DeferredPage>
          }
        />
        <Route
          path="cases/:caseId"
          element={
            <DeferredPage>
              <CaseDetailPage />
            </DeferredPage>
          }
        />
        <Route
          path="admin"
          element={
            <DeferredPage>
              <AdminConfigPage />
            </DeferredPage>
          }
        />
        <Route
          path="wellbeing"
          element={
            <DeferredPage>
              <WellbeingPage />
            </DeferredPage>
          }
        />
        <Route
          path="getting-started"
          element={
            <DeferredPage>
              <GettingStartedPage />
            </DeferredPage>
          }
        />
      </Route>
    </Routes>
  )
}

export default function App() {
  const Router = IS_PUBLIC_SITE ? HashRouter : BrowserRouter

  return (
    <Router>
      <Routes>
        <Route path="/" element={<LandingPage />} />
        <Route path="/architecture" element={<ArchitecturePage />} />
        <Route
          path="/demo"
          element={
            <DeferredPage>
              <DemoPage />
            </DeferredPage>
          }
        />
        <Route path="/login" element={<LoginPage />} />
        <Route
          path="/app/*"
          element={
            <ProtectedRoute>
              <AuthenticatedApp />
            </ProtectedRoute>
          }
        />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </Router>
  )
}
