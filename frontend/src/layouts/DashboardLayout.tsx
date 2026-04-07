import { useState, useEffect } from 'react';
import { Outlet, Link, useParams, useLocation } from 'react-router';
import { motion, AnimatePresence } from 'framer-motion';
import * as Collapsible from '@radix-ui/react-collapsible';
import { useAuditStore } from '../stores/auditStore';
import { useEnrichmentPolling } from '../hooks/useEnrichmentPolling';
import {
  LayoutDashboard,
  ArrowLeft,
  ChevronDown,
  PanelLeftClose,
  PanelLeft,
  FileCode,
  Paintbrush,
  Zap,
  ShieldCheck,
  BookOpen,
  FileJson,
  Layers,
  Link2,
  Network,
  FolderTree,
  Accessibility,
  Radio,
  FileText,
  Wrench,
  BarChart3,
  Download,
  Menu,
  X,
  Loader2,
  CheckCircle2,
  AlertTriangle,
} from 'lucide-react';
import { PILLAR_LABELS } from '../constants/pillarLabels';

interface NavItem {
  icon: React.ElementType;
  label: string;
  href: string;
}

interface NavGroup {
  label: string;
  items: NavItem[];
}

const navGroups: NavGroup[] = [
  {
    label: 'Technical Health',
    items: [
      { icon: FileCode, label: PILLAR_LABELS.semantic_html, href: '#semantic_html' },
      { icon: Paintbrush, label: PILLAR_LABELS.css_quality, href: '#css_quality' },
      { icon: Zap, label: PILLAR_LABELS.js_bloat, href: '#js_bloat' },
      { icon: ShieldCheck, label: PILLAR_LABELS.data_integrity, href: '#data_integrity' },
    ],
  },
  {
    label: 'Content & SEO',
    items: [
      { icon: BookOpen, label: PILLAR_LABELS.aeo_content, href: '#aeo_content' },
      { icon: FileJson, label: PILLAR_LABELS.structured_data, href: '#structured_data' },
      { icon: Layers, label: PILLAR_LABELS.rag_readiness, href: '#rag_readiness' },
    ],
  },
  {
    label: 'Links & Architecture',
    items: [
      { icon: Link2, label: PILLAR_LABELS.internal_linking, href: '#internal_linking' },
      { icon: Network, label: 'Link Graph', href: 'graph' },
      { icon: FolderTree, label: 'Topic Clusters', href: 'clusters' },
    ],
  },
  {
    label: 'Accessibility & Protocols',
    items: [
      { icon: Accessibility, label: PILLAR_LABELS.accessibility, href: '#accessibility' },
      { icon: Radio, label: PILLAR_LABELS.agentic_protocols, href: '#agentic_protocols' },
    ],
  },
  {
    label: 'Reports & Export',
    items: [
      { icon: FileText, label: 'Executive Summary', href: 'summary' },
      { icon: Wrench, label: 'Fix Guide', href: 'fixes' },
      { icon: BarChart3, label: 'Competitor Benchmark', href: 'benchmark' },
      { icon: Download, label: 'Export', href: 'export' },
    ],
  },
];

export default function DashboardLayout() {
  const { auditId } = useParams();
  const location = useLocation();
  const { report, isLoading, fetchReport } = useAuditStore();
  const [collapsed, setCollapsed] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);
  const [bannerDismissed, setBannerDismissed] = useState(false);

  // Fetch audit data from API if not in memory
  useEffect(() => {
    if (!report && !isLoading && auditId) {
      fetchReport(auditId);
    }
  }, [auditId, report, isLoading, fetchReport]);

  // Enrichment polling
  const enrichment = useEnrichmentPolling(auditId);

  // Auto-dismiss success banner after 4 seconds
  useEffect(() => {
    if (enrichment.status === 'complete') {
      const timer = setTimeout(() => setBannerDismissed(true), 4000);
      return () => clearTimeout(timer);
    }
    setBannerDismissed(false);
  }, [enrichment.status]);
  const [openGroups, setOpenGroups] = useState<Record<string, boolean>>(() =>
    Object.fromEntries(navGroups.map((g) => [g.label, true]))
  );

  // Cmd/Ctrl+B toggle
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'b') {
        e.preventDefault();
        setCollapsed((c) => !c);
      }
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, []);

  // Close mobile drawer on navigation
  useEffect(() => {
    setMobileOpen(false);
  }, [location.pathname]);

  const toggleGroup = (label: string) =>
    setOpenGroups((prev) => ({ ...prev, [label]: !prev[label] }));

  const isActive = (href: string) => {
    if (href.startsWith('#')) return false; // Anchor links — no active state
    const full = `/dashboard/${auditId}/${href}`;
    return location.pathname === full;
  };

  const isOverviewActive = location.pathname === `/dashboard/${auditId}`;

  const sidebarContent = (
    <>
      {/* Logo */}
      <div className="p-4 border-b border-border flex items-center justify-between">
        <Link to="/" className="flex items-center gap-2.5">
          <div className="w-8 h-8 bg-accent rounded-lg flex items-center justify-center flex-shrink-0">
            <svg
              width="18"
              height="18"
              viewBox="0 0 24 24"
              fill="none"
              stroke="white"
              strokeWidth="2.5"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <polyline points="22 12 18 12 15 21 9 3 6 12 2 12" />
            </svg>
          </div>
          {!collapsed && (
            <span className="text-lg font-bold tracking-tight text-text font-heading">
              WAIO
            </span>
          )}
        </Link>
        {!collapsed && (
          <button
            onClick={() => setCollapsed(true)}
            className="p-1.5 text-text-muted hover:text-text hover:bg-surface-overlay rounded-lg transition-all hidden lg:block"
            title="Collapse sidebar (Cmd+B)"
          >
            <PanelLeftClose size={16} />
          </button>
        )}
      </div>

      {/* Overview link */}
      <div className="px-3 pt-4 pb-2">
        <Link
          to={`/dashboard/${auditId}`}
          className={`flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all ${
            isOverviewActive
              ? 'bg-accent-muted text-accent border-l-2 border-accent'
              : 'text-text-secondary hover:text-text hover:bg-surface-overlay'
          }`}
        >
          <LayoutDashboard size={16} className="flex-shrink-0" />
          {!collapsed && 'Overview'}
        </Link>
      </div>

      {/* Nav Groups */}
      <nav className="flex-1 px-3 py-2 space-y-1 overflow-y-auto">
        {navGroups.map((group) => (
          <Collapsible.Root
            key={group.label}
            open={collapsed ? false : openGroups[group.label]}
            onOpenChange={() => !collapsed && toggleGroup(group.label)}
          >
            <Collapsible.Trigger asChild>
              <button
                className={`w-full flex items-center justify-between px-3 py-2 text-[11px] font-bold text-text-muted uppercase tracking-widest hover:text-text-secondary transition-colors ${
                  collapsed ? 'justify-center' : ''
                }`}
              >
                {collapsed ? (
                  <span className="w-4 h-px bg-border block" />
                ) : (
                  <>
                    {group.label}
                    <ChevronDown
                      size={12}
                      className={`transition-transform duration-200 ${
                        openGroups[group.label] ? 'rotate-180' : ''
                      }`}
                    />
                  </>
                )}
              </button>
            </Collapsible.Trigger>

            <Collapsible.Content className="overflow-hidden data-[state=open]:animate-slideDown data-[state=closed]:animate-slideUp">
              <div className="space-y-0.5 pb-2">
                {group.items.map((item) => {
                  const active = isActive(item.href);
                  const resolvedHref = item.href.startsWith('#')
                    ? `/dashboard/${auditId}${item.href}`
                    : `/dashboard/${auditId}/${item.href}`;

                  return (
                    <Link
                      key={item.label}
                      to={resolvedHref}
                      className={`flex items-center gap-3 px-3 py-2 rounded-lg text-sm transition-all ${
                        active
                          ? 'bg-accent-muted text-accent font-medium'
                          : 'text-text-muted hover:text-text hover:bg-surface-overlay'
                      }`}
                      title={collapsed ? item.label : undefined}
                    >
                      <item.icon size={15} className="flex-shrink-0" />
                      {!collapsed && item.label}
                    </Link>
                  );
                })}
              </div>
            </Collapsible.Content>
          </Collapsible.Root>
        ))}
      </nav>

      {/* Footer */}
      <div className="p-4 border-t border-border">
        {collapsed ? (
          <button
            onClick={() => setCollapsed(false)}
            className="w-full flex items-center justify-center p-1.5 text-text-muted hover:text-text hover:bg-surface-overlay rounded-lg transition-all"
            title="Expand sidebar (Cmd+B)"
          >
            <PanelLeft size={16} />
          </button>
        ) : (
          <Link
            to="/"
            className="flex items-center gap-2 text-xs text-text-muted hover:text-text transition-colors"
          >
            <ArrowLeft size={14} />
            Back to Auditor
          </Link>
        )}
      </div>
    </>
  );

  return (
    <div className="min-h-screen bg-surface flex">
      {/* Desktop Sidebar */}
      <aside
        className={`hidden lg:flex flex-col bg-surface-raised border-r border-border transition-all duration-200 ${
          collapsed ? 'w-14' : 'w-64'
        }`}
      >
        {sidebarContent}
      </aside>

      {/* Mobile hamburger */}
      <button
        onClick={() => setMobileOpen(true)}
        className="lg:hidden fixed top-4 left-4 z-50 p-2 bg-surface-raised border border-border rounded-lg text-text-muted hover:text-text transition-colors"
      >
        <Menu size={18} />
      </button>

      {/* Mobile drawer overlay */}
      <AnimatePresence>
        {mobileOpen && (
          <>
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="lg:hidden fixed inset-0 bg-black/60 z-40"
              onClick={() => setMobileOpen(false)}
            />
            <motion.aside
              initial={{ x: -280 }}
              animate={{ x: 0 }}
              exit={{ x: -280 }}
              transition={{ type: 'spring', damping: 25, stiffness: 300 }}
              className="lg:hidden fixed left-0 top-0 bottom-0 w-[280px] z-50 bg-surface-raised border-r border-border flex flex-col"
            >
              <button
                onClick={() => setMobileOpen(false)}
                className="absolute top-4 right-4 p-1.5 text-text-muted hover:text-text transition-colors"
              >
                <X size={16} />
              </button>
              {sidebarContent}
            </motion.aside>
          </>
        )}
      </AnimatePresence>

      {/* Main Content */}
      <div className="flex-1 overflow-auto">
        {/* Enrichment Banner */}
        <AnimatePresence>
          {enrichment.status === 'polling' && (
            <motion.div
              initial={{ opacity: 0, y: -20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -20 }}
              className="mx-4 mt-4 lg:mx-6 lg:mt-5"
            >
              <div className="bg-indigo-50 border border-indigo-200 rounded-xl px-5 py-3.5 flex items-start gap-3">
                <Loader2 size={18} className="text-indigo-600 animate-spin mt-0.5 flex-shrink-0" />
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-semibold text-indigo-900">Report enrichment in progress</p>
                  <p className="text-xs text-indigo-700 mt-0.5">{enrichment.progress}</p>
                  <p className="text-xs text-indigo-500 mt-1">
                    Link graph, topic clusters, and crawl statistics are being generated...
                  </p>
                  {/* Indeterminate progress bar */}
                  <div className="mt-2.5 h-1.5 bg-indigo-100 rounded-full overflow-hidden">
                    <div className="h-full w-1/3 bg-indigo-500 rounded-full animate-[shimmer_1.5s_ease-in-out_infinite]"
                      style={{ animation: 'shimmer 1.5s ease-in-out infinite' }} />
                  </div>
                </div>
              </div>
            </motion.div>
          )}
          {enrichment.status === 'complete' && !bannerDismissed && (
            <motion.div
              initial={{ opacity: 0, y: -20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -20 }}
              className="mx-4 mt-4 lg:mx-6 lg:mt-5"
            >
              <div className="bg-green-50 border border-green-200 rounded-xl px-5 py-3.5 flex items-center gap-3">
                <CheckCircle2 size={18} className="text-green-600 flex-shrink-0" />
                <p className="text-sm font-semibold text-green-900">
                  Report enrichment complete! Refreshing data...
                </p>
              </div>
            </motion.div>
          )}
          {enrichment.status === 'failed' && (
            <motion.div
              initial={{ opacity: 0, y: -20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -20 }}
              className="mx-4 mt-4 lg:mx-6 lg:mt-5"
            >
              <div className="bg-amber-50 border border-amber-200 rounded-xl px-5 py-3.5 flex items-center gap-3">
                <AlertTriangle size={18} className="text-amber-600 flex-shrink-0" />
                <div>
                  <p className="text-sm font-semibold text-amber-900">
                    Some premium data couldn't be generated
                  </p>
                  <p className="text-xs text-amber-700 mt-0.5">
                    The rest of your report is ready. {enrichment.progress}
                  </p>
                </div>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
        <Outlet />
      </div>
    </div>
  );
}
