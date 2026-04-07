import { createBrowserRouter } from 'react-router';
import { Suspense, lazy } from 'react';
import { PublicLayout } from './layouts/PublicLayout';
import { LandingPage } from './pages/LandingPage';
import { AuditReportPage } from './pages/AuditReportPage';
import { HistoryPage } from './pages/HistoryPage';
import { SchedulesPage } from './pages/SchedulesPage';
import { DashboardErrorBoundary } from './components/DashboardErrorBoundary';

const DashboardLayout = lazy(() => import('./layouts/DashboardLayout'));
const DashboardOverviewPage = lazy(
  () => import('./pages/DashboardOverviewPage')
);
const DashboardGraphPage = lazy(
  () => import('./pages/DashboardGraphPage')
);
const DashboardSummaryPage = lazy(
  () => import('./pages/DashboardSummaryPage')
);
const DashboardFixesPage = lazy(
  () => import('./pages/DashboardFixesPage')
);
const DashboardBenchmarkPage = lazy(
  () => import('./pages/DashboardBenchmarkPage')
);
const DashboardClustersPage = lazy(
  () => import('./pages/DashboardClustersPage')
);
const DashboardExportPage = lazy(
  () => import('./pages/DashboardExportPage')
);
const DashboardPillarPage = lazy(
  () => import('./pages/DashboardPillarPage')
);
const DashboardPagesPage = lazy(
  () => import('./pages/DashboardPagesPage')
);
const AdminPanel = lazy(
  () => import('./components/auth/AdminPanel')
);

const dashboardFallback = (
  <div className="min-h-screen bg-surface flex items-center justify-center">
    <div className="text-center">
      <div className="w-8 h-8 mx-auto mb-3 rounded-lg bg-accent/10 flex items-center justify-center animate-pulse">
        <svg
          width="16"
          height="16"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          className="text-accent"
        >
          <polyline points="22 12 18 12 15 21 9 3 6 12 2 12" />
        </svg>
      </div>
      <p className="text-text-muted text-sm">Loading dashboard...</p>
    </div>
  </div>
);

export const router = createBrowserRouter([
  {
    element: <PublicLayout />,
    children: [
      { index: true, element: <LandingPage /> },
      { path: 'audit/:auditId', element: <AuditReportPage /> },
      { path: 'history', element: <HistoryPage /> },
      { path: 'schedules', element: <SchedulesPage /> },
      {
        path: 'admin',
        element: (
          <Suspense fallback={dashboardFallback}>
            <AdminPanel />
          </Suspense>
        ),
      },
    ],
  },
  {
    path: 'dashboard/:auditId',
    element: (
      <DashboardErrorBoundary>
        <Suspense fallback={dashboardFallback}>
          <DashboardLayout />
        </Suspense>
      </DashboardErrorBoundary>
    ),
    children: [
      {
        index: true,
        element: (
          <Suspense fallback={dashboardFallback}>
            <DashboardOverviewPage />
          </Suspense>
        ),
      },
      {
        path: 'graph',
        element: (
          <Suspense fallback={dashboardFallback}>
            <DashboardGraphPage />
          </Suspense>
        ),
      },
      {
        path: 'summary',
        element: (
          <Suspense fallback={dashboardFallback}>
            <DashboardSummaryPage />
          </Suspense>
        ),
      },
      {
        path: 'fixes',
        element: (
          <Suspense fallback={dashboardFallback}>
            <DashboardFixesPage />
          </Suspense>
        ),
      },
      {
        path: 'benchmark',
        element: (
          <Suspense fallback={dashboardFallback}>
            <DashboardBenchmarkPage />
          </Suspense>
        ),
      },
      {
        path: 'clusters',
        element: (
          <Suspense fallback={dashboardFallback}>
            <DashboardClustersPage />
          </Suspense>
        ),
      },
      {
        path: 'export',
        element: (
          <Suspense fallback={dashboardFallback}>
            <DashboardExportPage />
          </Suspense>
        ),
      },
      {
        path: 'pillar/:pillarSlug',
        element: (
          <Suspense fallback={dashboardFallback}>
            <DashboardPillarPage />
          </Suspense>
        ),
      },
      {
        path: 'pages',
        element: (
          <Suspense fallback={dashboardFallback}>
            <DashboardPagesPage />
          </Suspense>
        ),
      },
    ],
  },
]);
