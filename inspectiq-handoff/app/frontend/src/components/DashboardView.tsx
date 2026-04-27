import { useState, useEffect, useMemo, useCallback } from 'react'
import {
  BarChart2, Wrench, Map, AlertTriangle, CheckCircle, Clock, TrendingDown,
  X, ArrowRight, Sparkles, Filter, ShieldAlert, CalendarClock, RefreshCw,
} from 'lucide-react'

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface Summary {
  total_assets: number
  critical_count: number
  poor_count: number
  fair_count: number
  good_count: number
  overdue_count: number
  total_backlog: number
}

interface RegionData {
  region: string
  condition_category: string
  count: number
  avg_rating: number
  total_cost: number
}

interface DisciplineData {
  inspection_type: string
  condition_category: string
  count: number
  avg_rating: number
  total_cost: number
}

interface Asset {
  asset_id: string
  asset_name: string
  asset_type: string
  region: string
  state: string
  condition_rating: number
  condition_category: string
  inspection_overdue: boolean
  estimated_maintenance_cost: number
  last_inspection_date?: string
  next_scheduled_inspection?: string
}

interface FilterOptions {
  regions: string[]
  disciplines: string[]
  conditions: string[]
  clients: string[]
}

interface FilterState {
  region: string
  discipline: string
  condition: string
  client: string
}

interface Compliance {
  total_assets: number
  overdue_count: number
  safety_flagged_count: number
  nbis_deficient_count: number
  overdue_and_safety: number
  avg_days_overdue: number
  max_days_overdue: number
  overdue_cost_exposure: number
  days_overdue_buckets: { bucket: string; count: number }[]
}

interface TrendPoint {
  month: string
  condition_category: string
  count: number
  avg_rating: number
}

interface NarrativeResponse {
  narrative: string
  fallback?: boolean
}

interface DrawerSpec {
  title: string
  subtitle?: string
  filter: (a: Asset) => boolean
  sort?: (a: Asset, b: Asset) => number
}

// ---------------------------------------------------------------------------
// Constants & helpers
// ---------------------------------------------------------------------------

const CONDITION_COLORS: Record<string, string> = {
  Critical: '#c0392b',
  Poor:     '#e67e22',
  Fair:     '#f1c40f',
  Good:     '#27ae60',
}

const CONDITION_BG: Record<string, string> = {
  Critical: 'bg-red-100 text-red-700 border border-red-200',
  Poor:     'bg-orange-100 text-orange-700 border border-orange-200',
  Fair:     'bg-yellow-100 text-yellow-700 border border-yellow-200',
  Good:     'bg-green-100 text-green-700 border border-green-200',
}

const REGION_MAP: Record<string, string> = {
  PA: 'Mid-Atlantic', NJ: 'Mid-Atlantic', DE: 'Mid-Atlantic', MD: 'Mid-Atlantic',
  NY: 'Northeast',   MA: 'Northeast',     CT: 'Northeast',
  VA: 'Southeast',   NC: 'Southeast',     GA: 'Southeast',  FL: 'Southeast',
  OH: 'Midwest',     IL: 'Midwest',       MI: 'Midwest',
  TX: 'Southwest',   CO: 'Southwest',
  CA: 'Pacific',     WA: 'Pacific',
}
const stateRegion = (s: string) => REGION_MAP[s] || 'Other'

const fmt = (n: number) =>
  n >= 1_000_000 ? `$${(n / 1_000_000).toFixed(1)}M` : `$${(n / 1_000).toFixed(0)}K`

const EMPTY_FILTERS: FilterState = { region: '', discipline: '', condition: '', client: '' }

function buildQuery(f: FilterState): string {
  const params = new URLSearchParams()
  if (f.region)     params.set('region', f.region)
  if (f.discipline) params.set('discipline', f.discipline)
  if (f.condition)  params.set('condition', f.condition)
  if (f.client)     params.set('client', f.client)
  const s = params.toString()
  return s ? `?${s}` : ''
}

// ---------------------------------------------------------------------------
// Small building blocks
// ---------------------------------------------------------------------------

function HBar({
  value, max, color, label, sub, onClick,
}: {
  value: number
  max: number
  color: string
  label: string
  sub?: string
  onClick?: () => void
}) {
  const pct = max > 0 ? Math.max(2, (value / max) * 100) : 0
  const isButton = !!onClick
  return (
    <div
      className={`flex items-center gap-3 text-xs ${isButton ? 'cursor-pointer group' : ''}`}
      onClick={onClick}
      role={isButton ? 'button' : undefined}
    >
      <div className="w-28 text-right">
        <div className={`text-gray-700 font-medium truncate ${isButton ? 'group-hover:text-mbi-navy' : ''}`}>{label}</div>
        {sub && <div className="text-gray-400">{sub}</div>}
      </div>
      <div className="flex-1 bg-gray-100 rounded-full h-5 overflow-hidden">
        <div
          className={`h-5 rounded-full transition-all duration-700 ${isButton ? 'group-hover:brightness-110' : ''}`}
          style={{ width: `${pct}%`, backgroundColor: color }}
        />
      </div>
      <div className="w-10 text-right font-bold text-gray-700">{value.toLocaleString()}</div>
    </div>
  )
}

function Select({
  label, value, options, onChange, placeholder,
}: {
  label: string
  value: string
  options: string[]
  onChange: (v: string) => void
  placeholder: string
}) {
  return (
    <label className="flex flex-col gap-1 min-w-0 flex-1">
      <span className="text-[10px] uppercase tracking-wide font-semibold text-gray-500">{label}</span>
      <select
        value={value}
        onChange={e => onChange(e.target.value)}
        className="border border-gray-200 rounded px-2 py-1.5 text-xs bg-white focus:outline-none focus:ring-2 focus:ring-mbi-navy/40 focus:border-mbi-navy"
      >
        <option value="">{placeholder}</option>
        {options.map(o => <option key={o} value={o}>{o}</option>)}
      </select>
    </label>
  )
}

// Asset drawer — slides in from the right with filtered asset list
function AssetDrawer({
  spec, assets, onClose,
}: {
  spec: DrawerSpec | null
  assets: Asset[]
  onClose: () => void
}) {
  useEffect(() => {
    if (!spec) return
    const onKey = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose() }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [spec, onClose])

  const filtered = useMemo(() => {
    if (!spec) return []
    const list = assets.filter(spec.filter)
    const sortFn = spec.sort || ((a: Asset, b: Asset) => {
      const ac = a.condition_rating
      const bc = b.condition_rating
      if (ac !== bc) return ac - bc
      return b.estimated_maintenance_cost - a.estimated_maintenance_cost
    })
    return [...list].sort(sortFn)
  }, [spec, assets])

  if (!spec) return null

  const totalCost = filtered.reduce((s, a) => s + (a.estimated_maintenance_cost || 0), 0)

  return (
    <>
      <div onClick={onClose} className="fixed inset-0 bg-black/40 z-40 animate-fadeIn" />
      <div className="fixed right-0 top-0 bottom-0 w-[560px] max-w-[95vw] bg-white z-50 shadow-2xl flex flex-col animate-slideInRight">
        <div className="px-6 py-4 border-b border-gray-200 bg-mbi-navy text-white flex items-start justify-between gap-3 flex-shrink-0">
          <div>
            <div className="text-lg font-bold leading-tight">{spec.title}</div>
            {spec.subtitle && (
              <div className="text-xs text-blue-200 mt-0.5">{spec.subtitle}</div>
            )}
            <div className="text-xs text-blue-200 mt-1.5">
              {filtered.length} asset{filtered.length !== 1 ? 's' : ''} · ${(totalCost / 1_000_000).toFixed(1)}M repair cost
            </div>
          </div>
          <button
            onClick={onClose}
            className="w-8 h-8 rounded hover:bg-white/10 flex items-center justify-center flex-shrink-0"
          >
            <X size={16} />
          </button>
        </div>

        <div className="flex-1 overflow-y-auto">
          {filtered.length === 0 ? (
            <div className="text-center text-gray-400 py-10 text-sm">No matching assets</div>
          ) : (
            <div className="divide-y divide-gray-100">
              {filtered.map(a => (
                <div key={a.asset_id} className="px-5 py-3 hover:bg-mbi-light transition-colors">
                  <div className="flex items-start justify-between gap-3 mb-1">
                    <div className="min-w-0 flex-1">
                      <div className="flex items-center gap-2 mb-0.5">
                        <span className="text-[10px] font-mono text-gray-500">{a.asset_id}</span>
                        <span className="text-[10px] font-bold px-1.5 py-0.5 rounded bg-slate-100 text-slate-700 uppercase">
                          {a.asset_type}
                        </span>
                        {a.inspection_overdue && (
                          <span className="text-[10px] font-bold px-1.5 py-0.5 rounded bg-red-100 text-red-700 uppercase">
                            Overdue
                          </span>
                        )}
                      </div>
                      <div className="text-sm font-semibold text-gray-900 truncate">{a.asset_name}</div>
                      <div className="text-xs text-gray-500">
                        {a.state} · {stateRegion(a.state)}
                      </div>
                    </div>
                    <div className="text-right flex-shrink-0">
                      <span className={`inline-block px-2 py-0.5 rounded-full text-xs font-bold ${CONDITION_BG[a.condition_category] || ''}`}>
                        {a.condition_rating} · {a.condition_category}
                      </span>
                      <div className="text-sm font-bold text-mbi-navy mt-1">
                        {fmt(a.estimated_maintenance_cost)}
                      </div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        <div className="px-6 py-3 border-t border-gray-200 bg-gray-50 flex items-center justify-between flex-shrink-0">
          <div className="text-[11px] text-gray-500">
            Click any row to view the asset's inspection report (coming soon)
          </div>
          <button
            onClick={onClose}
            className="px-4 py-1.5 bg-white border border-gray-200 rounded text-gray-700 text-sm font-medium hover:bg-gray-100"
          >
            Close
          </button>
        </div>
      </div>
    </>
  )
}

// ---------------------------------------------------------------------------
// Main component
// ---------------------------------------------------------------------------

export default function DashboardView() {
  const [filters, setFilters] = useState<FilterState>(EMPTY_FILTERS)
  const [options, setOptions] = useState<FilterOptions>({ regions: [], disciplines: [], conditions: [], clients: [] })

  const [summary, setSummary] = useState<Summary | null>(null)
  const [byRegion, setByRegion] = useState<RegionData[]>([])
  const [byDiscipline, setByDiscipline] = useState<DisciplineData[]>([])
  const [allAssets, setAllAssets] = useState<Asset[]>([])
  const [compliance, setCompliance] = useState<Compliance | null>(null)
  const [trend, setTrend] = useState<TrendPoint[]>([])
  const [narrative, setNarrative] = useState<NarrativeResponse | null>(null)
  const [narrativeLoading, setNarrativeLoading] = useState(false)

  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [drawer, setDrawer] = useState<DrawerSpec | null>(null)

  const activeFilterCount = Object.values(filters).filter(Boolean).length

  // Load filter dropdown options once
  useEffect(() => {
    fetch('/api/assets/filters')
      .then(r => r.json())
      .then(setOptions)
      .catch(() => { /* leave options empty */ })
  }, [])

  // Load filtered data whenever filters change
  const loadAll = useCallback(() => {
    const q = buildQuery(filters)
    setLoading(true)
    setError(null)
    Promise.all([
      fetch(`/api/assets/summary${q}`).then(r => r.json()),
      fetch(`/api/assets/by-region${q}`).then(r => r.json()),
      fetch(`/api/assets/by-discipline${q}`).then(r => r.json()),
      fetch(`/api/assets/search${q}`).then(r => r.json()),
      fetch(`/api/assets/compliance${q}`).then(r => r.json()),
      fetch(`/api/assets/trend${q}`).then(r => r.json()),
    ])
      .then(([summ, reg, disc, all, comp, tr]) => {
        setSummary(summ)
        setByRegion(Array.isArray(reg) ? reg : [])
        setByDiscipline(Array.isArray(disc) ? disc : [])
        setAllAssets(Array.isArray(all) ? all : [])
        setCompliance(comp)
        setTrend(Array.isArray(tr) ? tr : [])
        setLoading(false)
      })
      .catch(err => {
        setError(String(err))
        setLoading(false)
      })
  }, [filters])

  useEffect(() => { loadAll() }, [loadAll])

  // Load AI narrative in the background (non-blocking)
  const loadNarrative = useCallback(() => {
    const q = buildQuery(filters)
    setNarrativeLoading(true)
    fetch(`/api/assets/narrative${q}`)
      .then(r => r.json())
      .then((n: NarrativeResponse) => {
        setNarrative(n)
        setNarrativeLoading(false)
      })
      .catch(() => {
        setNarrative({ narrative: 'Narrative unavailable — check serving endpoint.' , fallback: true })
        setNarrativeLoading(false)
      })
  }, [filters])

  useEffect(() => { loadNarrative() }, [loadNarrative])

  // --- Aggregations for charts ---

  const regionCosts = useMemo(() => (
    Object.values(
      byRegion.reduce((acc, r) => {
        if (!acc[r.region]) acc[r.region] = { region: r.region, total_cost: 0, count: 0, critical: 0 }
        acc[r.region].total_cost += r.total_cost
        acc[r.region].count += r.count
        if (r.condition_category === 'Critical') acc[r.region].critical += r.count
        return acc
      }, {} as Record<string, { region: string; total_cost: number; count: number; critical: number }>)
    ).sort((a, b) => b.total_cost - a.total_cost)
  ), [byRegion])

  const conditionTotals = useMemo(() => (
    ['Critical', 'Poor', 'Fair', 'Good'].map(cat => ({
      cat,
      count: byRegion.filter(r => r.condition_category === cat).reduce((s, r) => s + r.count, 0),
    }))
  ), [byRegion])
  const maxCount = Math.max(1, ...conditionTotals.map(c => c.count))

  const disciplineTotals = useMemo(() => (
    Object.entries(
      byDiscipline.reduce((acc, d) => {
        if (!acc[d.inspection_type]) acc[d.inspection_type] = { count: 0, critical: 0, total_cost: 0, weighted_rating: 0 }
        acc[d.inspection_type].count += d.count
        acc[d.inspection_type].total_cost += d.total_cost
        acc[d.inspection_type].weighted_rating += d.avg_rating * d.count
        if (d.condition_category === 'Critical') acc[d.inspection_type].critical += d.count
        return acc
      }, {} as Record<string, { count: number; critical: number; total_cost: number; weighted_rating: number }>)
    ).sort((a, b) => b[1].count - a[1].count)
  ), [byDiscipline])
  const maxDisciplineCount = Math.max(1, ...disciplineTotals.map(([, s]) => s.count))

  // Trend: pivot (month -> condition_category -> count)
  const trendMonths = useMemo(() => {
    const months = Array.from(new Set(trend.map(t => t.month))).sort()
    return months.map(m => {
      const byCat: Record<string, number> = {}
      let total = 0, weighted = 0
      for (const t of trend.filter(x => x.month === m)) {
        byCat[t.condition_category] = t.count
        total += t.count
        weighted += t.avg_rating * t.count
      }
      return {
        month: m,
        counts: byCat,
        total,
        avg_rating: total > 0 ? (weighted / total) : 0,
      }
    })
  }, [trend])
  const maxTrendTotal = Math.max(1, ...trendMonths.map(m => m.total))

  // --- Drawer filter helpers ---

  const openByCondition = (cat: string) => setDrawer({
    title: `${cat} Condition Assets`,
    subtitle: `${cat === 'Critical' ? 'Rating 1–3 · Immediate engineering intervention' :
      cat === 'Poor' ? 'Rating 4–5 · Priority repair required' :
      cat === 'Fair' ? 'Rating 6–7 · Routine maintenance' :
      'Rating 8–9 · No deficiencies'}`,
    filter: a => a.condition_category === cat,
  })

  const openOverdue = () => setDrawer({
    title: 'Overdue Inspections',
    subtitle: 'Assets past their scheduled re-inspection date',
    filter: a => a.inspection_overdue === true,
  })

  const openAllAssets = () => setDrawer({
    title: 'Complete Asset Portfolio',
    subtitle: 'All inspected infrastructure assets in the current view',
    filter: () => true,
  })

  const openBacklog = () => setDrawer({
    title: 'Maintenance Backlog',
    subtitle: 'Assets ranked by estimated repair cost (highest first)',
    filter: () => true,
    sort: (a, b) => b.estimated_maintenance_cost - a.estimated_maintenance_cost,
  })

  const openByRegion = (region: string) => setDrawer({
    title: `${region} Region`,
    subtitle: 'Assets in this geographic region',
    filter: a => stateRegion(a.state) === region,
  })

  const openByDiscipline = (discipline: string) => setDrawer({
    title: `${discipline} Assets`,
    subtitle: `All ${discipline.toLowerCase()} inspection projects`,
    filter: a => a.asset_type === discipline,
  })

  const openCritPoor = () => setDrawer({
    title: 'Assets Requiring Immediate Action',
    subtitle: 'Critical + Poor condition — the action queue for engineering leadership',
    filter: a => a.condition_category === 'Critical' || a.condition_category === 'Poor',
  })

  const openRegionCondition = (region: string, cat: string) => setDrawer({
    title: `${cat} · ${region}`,
    subtitle: `${cat} condition assets located in ${region}`,
    filter: a => stateRegion(a.state) === region && a.condition_category === cat,
  })

  // --- Render states ---

  if (loading && !summary) {
    return (
      <div className="flex flex-col items-center justify-center h-64 gap-3">
        <div className="w-8 h-8 border-4 border-mbi-navy border-t-transparent rounded-full animate-spin" />
        <p className="text-sm text-gray-400">Loading dashboard data...</p>
      </div>
    )
  }

  if (error) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-center text-red-500">
          <AlertTriangle size={32} className="mx-auto mb-2" />
          <p className="font-medium">Failed to load dashboard</p>
          <p className="text-xs text-gray-500 mt-1">{error}</p>
        </div>
      </div>
    )
  }

  const kpis = summary ? [
    { label: 'Total Assets',        value: summary.total_assets.toLocaleString(),
      icon: <CheckCircle size={20} className="text-mbi-navy" />,
      sub: 'Active portfolio · Click to explore',
      border: 'border-mbi-navy', onClick: openAllAssets },
    { label: 'Critical / Poor',     value: `${summary.critical_count} / ${summary.poor_count}`,
      icon: <AlertTriangle size={20} className="text-red-500" />,
      sub: `${summary.critical_count + summary.poor_count} need immediate action`,
      border: 'border-red-400', onClick: openCritPoor },
    { label: 'Overdue Inspections', value: summary.overdue_count.toLocaleString(),
      icon: <Clock size={20} className="text-orange-500" />,
      sub: 'Past scheduled date',
      border: 'border-orange-400', onClick: openOverdue },
    { label: 'Maintenance Backlog', value: fmt(summary.total_backlog),
      icon: <TrendingDown size={20} className="text-mbi-orange" />,
      sub: 'Estimated total cost',
      border: 'border-mbi-orange', onClick: openBacklog },
  ] : []

  return (
    <div className="space-y-4">
      <style>{`
        @keyframes slideInRight {
          from { transform: translateX(100%); }
          to   { transform: translateX(0); }
        }
        @keyframes fadeIn {
          from { opacity: 0; }
          to   { opacity: 1; }
        }
        .animate-slideInRight { animation: slideInRight 0.25s ease-out; }
        .animate-fadeIn       { animation: fadeIn 0.2s ease-out; }
      `}</style>

      {/* Filter bar */}
      <div className="card flex flex-col sm:flex-row items-start sm:items-end gap-3">
        <div className="flex items-center gap-2 text-xs font-semibold text-mbi-navy shrink-0 pb-1.5">
          <Filter size={14} />
          <span>Executive View Filters</span>
          {activeFilterCount > 0 && (
            <span className="inline-flex items-center justify-center w-5 h-5 rounded-full bg-mbi-orange text-white text-[10px] font-bold">
              {activeFilterCount}
            </span>
          )}
        </div>
        <div className="flex-1 grid grid-cols-2 md:grid-cols-4 gap-3 w-full">
          <Select label="Region"     value={filters.region}     options={options.regions}     onChange={v => setFilters(f => ({ ...f, region: v }))}     placeholder="All regions" />
          <Select label="Discipline" value={filters.discipline} options={options.disciplines} onChange={v => setFilters(f => ({ ...f, discipline: v }))} placeholder="All disciplines" />
          <Select label="Condition"  value={filters.condition}  options={options.conditions}  onChange={v => setFilters(f => ({ ...f, condition: v }))}  placeholder="All conditions" />
          <Select label="Client"     value={filters.client}     options={options.clients}     onChange={v => setFilters(f => ({ ...f, client: v }))}     placeholder="All clients" />
        </div>
        <button
          onClick={() => setFilters(EMPTY_FILTERS)}
          disabled={activeFilterCount === 0}
          className="shrink-0 px-3 py-1.5 text-xs font-medium rounded border border-gray-200 bg-white hover:bg-gray-50 text-gray-600 disabled:opacity-40 disabled:cursor-not-allowed inline-flex items-center gap-1"
        >
          <RefreshCw size={12} />
          Reset
        </button>
      </div>

      {/* AI narrative */}
      <div className="card border-l-4 border-mbi-orange bg-gradient-to-r from-orange-50/60 to-white">
        <div className="flex items-start gap-3">
          <div className="mt-0.5 shrink-0 w-8 h-8 rounded-full bg-mbi-orange/15 flex items-center justify-center">
            <Sparkles size={16} className="text-mbi-orange" />
          </div>
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 mb-1">
              <h3 className="text-sm font-semibold text-mbi-navy">Executive Briefing</h3>
              {narrative?.fallback && (
                <span className="text-[10px] uppercase tracking-wide font-bold px-1.5 py-0.5 rounded bg-gray-100 text-gray-500">Deterministic fallback</span>
              )}
              <span className="text-[10px] text-gray-400">Generated by databricks-claude-sonnet-4-6</span>
            </div>
            {narrativeLoading && !narrative ? (
              <div className="space-y-2">
                <div className="h-3 bg-gray-100 rounded animate-pulse w-11/12" />
                <div className="h-3 bg-gray-100 rounded animate-pulse w-10/12" />
                <div className="h-3 bg-gray-100 rounded animate-pulse w-9/12" />
              </div>
            ) : (
              <p className="text-sm text-gray-700 leading-relaxed">{narrative?.narrative}</p>
            )}
          </div>
        </div>
      </div>

      {/* Tip */}
      <div className="text-xs text-gray-500 px-1">
        Tip: KPIs, bars, trend months, and heatmap cells are clickable — drill into the underlying assets.
      </div>

      {/* KPI strip */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        {kpis.map((kpi, i) => (
          <button
            key={i}
            onClick={kpi.onClick}
            className={`card flex items-start gap-3 border-l-4 ${kpi.border} text-left hover:shadow-md hover:border-mbi-orange transition-all group`}
          >
            <div className="mt-0.5 shrink-0">{kpi.icon}</div>
            <div className="flex-1">
              <div className="text-2xl font-bold text-mbi-navy leading-tight">{kpi.value}</div>
              <div className="text-xs font-semibold text-gray-700 mt-0.5">{kpi.label}</div>
              <div className="text-xs text-gray-400">{kpi.sub}</div>
            </div>
            <ArrowRight size={14} className="text-gray-300 group-hover:text-mbi-orange group-hover:translate-x-0.5 transition-all shrink-0" />
          </button>
        ))}
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">

        {/* Condition breakdown */}
        <div className="card">
          <div className="flex items-center gap-2 mb-4">
            <BarChart2 size={16} className="text-mbi-navy" />
            <h2 className="font-semibold text-mbi-navy text-sm">Portfolio Condition Breakdown</h2>
          </div>
          {conditionTotals.every(c => c.count === 0) ? (
            <p className="text-xs text-gray-400 py-6 text-center">No data available</p>
          ) : (
            <div className="space-y-3">
              {conditionTotals.map(({ cat, count }) => (
                <HBar
                  key={cat}
                  label={cat}
                  value={count}
                  max={maxCount}
                  color={CONDITION_COLORS[cat]}
                  onClick={count > 0 ? () => openByCondition(cat) : undefined}
                />
              ))}
            </div>
          )}
        </div>

        {/* Backlog by region */}
        <div className="card">
          <div className="flex items-center gap-2 mb-4">
            <Map size={16} className="text-mbi-navy" />
            <h2 className="font-semibold text-mbi-navy text-sm">Maintenance Backlog by Region</h2>
          </div>
          {regionCosts.length === 0 ? (
            <p className="text-xs text-gray-400 py-6 text-center">No data available</p>
          ) : (
            <div className="space-y-3">
              {regionCosts.map(r => (
                <HBar
                  key={r.region}
                  label={r.region}
                  value={r.count}
                  max={Math.max(1, ...regionCosts.map(x => x.count))}
                  color={r.critical > 0 ? '#1a3a5c' : '#2d6a9f'}
                  sub={fmt(r.total_cost)}
                  onClick={() => openByRegion(r.region)}
                />
              ))}
            </div>
          )}
        </div>

        {/* Discipline bars */}
        <div className="card">
          <div className="flex items-center gap-2 mb-4">
            <Wrench size={16} className="text-mbi-navy" />
            <h2 className="font-semibold text-mbi-navy text-sm">Asset Count by Inspection Discipline</h2>
          </div>
          {disciplineTotals.length === 0 ? (
            <p className="text-xs text-gray-400 py-6 text-center">No data available</p>
          ) : (
            <div className="space-y-3">
              {disciplineTotals.map(([discipline, stats]) => {
                const pct = Math.max(4, (stats.count / maxDisciplineCount) * 100)
                const avgRating = stats.count > 0 ? (stats.weighted_rating / stats.count).toFixed(1) : '-'
                const color = stats.critical > 0 ? '#c0392b' : '#1a3a5c'
                return (
                  <div
                    key={discipline}
                    onClick={() => openByDiscipline(discipline)}
                    role="button"
                    className="flex items-center gap-3 text-xs cursor-pointer group"
                  >
                    <div className="w-32 text-right">
                      <div className="text-gray-700 font-medium truncate group-hover:text-mbi-navy">{discipline}</div>
                      <div className="text-gray-400">avg {avgRating} · {fmt(stats.total_cost)}</div>
                    </div>
                    <div className="flex-1 bg-gray-100 rounded-full h-5 overflow-hidden">
                      <div className="h-5 rounded-full transition-all duration-700 group-hover:brightness-110" style={{ width: `${pct}%`, backgroundColor: color }} />
                    </div>
                    <div className="w-8 text-right font-bold text-gray-700">{stats.count}</div>
                  </div>
                )
              })}
            </div>
          )}
        </div>

        {/* Top risk */}
        <div className="card p-0 overflow-hidden">
          <div className="px-4 py-3 flex items-center gap-2 border-b border-gray-100 bg-red-50">
            <AlertTriangle size={15} className="text-red-500" />
            <h2 className="font-semibold text-mbi-navy text-sm">Highest-Risk Assets Requiring Action</h2>
          </div>
          {allAssets.length === 0 ? (
            <p className="text-xs text-gray-400 py-8 text-center">No data available</p>
          ) : (
            <div className="divide-y divide-gray-50">
              {[...allAssets]
                .sort((a, b) => {
                  if (a.condition_rating !== b.condition_rating) return a.condition_rating - b.condition_rating
                  return b.estimated_maintenance_cost - a.estimated_maintenance_cost
                })
                .slice(0, 8)
                .map(a => (
                  <div
                    key={a.asset_id}
                    onClick={() => setDrawer({
                      title: a.asset_name,
                      subtitle: `${a.asset_id} · ${a.asset_type} · ${a.state}`,
                      filter: x => x.asset_id === a.asset_id,
                    })}
                    className="px-4 py-2.5 flex items-center gap-3 hover:bg-gray-50 transition-colors cursor-pointer"
                  >
                    <div className="shrink-0">
                      <span className={`px-2 py-0.5 rounded-full text-xs font-bold ${CONDITION_BG[a.condition_category] ?? ''}`}>
                        {a.condition_rating}
                      </span>
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="text-xs font-semibold text-gray-800 truncate">{a.asset_name}</div>
                      <div className="text-xs text-gray-400">{a.asset_type} · {a.region}</div>
                    </div>
                    <div className="shrink-0 text-right">
                      <div className="text-xs font-bold text-mbi-navy">{fmt(a.estimated_maintenance_cost)}</div>
                      {a.inspection_overdue && (
                        <div className="text-xs text-red-500 font-medium">Overdue</div>
                      )}
                    </div>
                  </div>
                ))}
            </div>
          )}
        </div>

      </div>

      {/* Compliance & Backlog Risk panel */}
      {compliance && (
        <div className="card">
          <div className="flex items-center gap-2 mb-4">
            <ShieldAlert size={16} className="text-red-600" />
            <h2 className="font-semibold text-mbi-navy text-sm">Inspection Backlog &amp; Compliance Risk</h2>
          </div>

          <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-4">
            {[
              { label: 'Overdue',             value: compliance.overdue_count,          sub: `${compliance.total_assets ? Math.round((compliance.overdue_count / compliance.total_assets) * 100) : 0}% of portfolio`, color: 'text-orange-600', bg: 'bg-orange-50', onClick: openOverdue },
              { label: 'Safety-Flagged',      value: compliance.safety_flagged_count,   sub: 'Active hazard documented',              color: 'text-red-600',    bg: 'bg-red-50' },
              { label: 'NBIS Deficient',      value: compliance.nbis_deficient_count,   sub: 'Fails FHWA compliance',                 color: 'text-purple-600', bg: 'bg-purple-50' },
              { label: 'Overdue + Safety',    value: compliance.overdue_and_safety,     sub: 'Highest-urgency combo',                 color: 'text-red-700',    bg: 'bg-red-100' },
            ].map((m, i) => (
              <button
                key={i}
                onClick={m.onClick}
                disabled={!m.onClick}
                className={`text-left rounded border border-gray-100 ${m.bg} px-3 py-2 ${m.onClick ? 'hover:shadow-md hover:border-mbi-orange transition-all' : 'cursor-default'}`}
              >
                <div className={`text-2xl font-bold ${m.color} leading-tight`}>{m.value.toLocaleString()}</div>
                <div className="text-xs font-semibold text-gray-700 mt-0.5">{m.label}</div>
                <div className="text-xs text-gray-500">{m.sub}</div>
              </button>
            ))}
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-3 text-xs">
            <div className="rounded bg-gray-50 px-3 py-2 flex items-center justify-between">
              <span className="text-gray-500 inline-flex items-center gap-1.5"><CalendarClock size={12} /> Avg days overdue</span>
              <span className="font-bold text-mbi-navy">{compliance.avg_days_overdue}</span>
            </div>
            <div className="rounded bg-gray-50 px-3 py-2 flex items-center justify-between">
              <span className="text-gray-500 inline-flex items-center gap-1.5"><CalendarClock size={12} /> Longest overdue</span>
              <span className="font-bold text-mbi-navy">{compliance.max_days_overdue} d</span>
            </div>
            <div className="rounded bg-gray-50 px-3 py-2 flex items-center justify-between">
              <span className="text-gray-500 inline-flex items-center gap-1.5"><TrendingDown size={12} /> $ at risk (overdue)</span>
              <span className="font-bold text-mbi-navy">{fmt(compliance.overdue_cost_exposure || 0)}</span>
            </div>
          </div>

          <div className="mt-4">
            <div className="text-xs font-semibold text-gray-600 mb-2">Days-overdue distribution</div>
            <div className="space-y-2">
              {compliance.days_overdue_buckets.map(b => {
                const max = Math.max(1, ...compliance.days_overdue_buckets.map(x => x.count))
                const pct = max > 0 ? Math.max(2, (b.count / max) * 100) : 0
                const isOverdueBucket = b.bucket !== 'On schedule'
                const color = b.bucket === 'On schedule' ? '#27ae60' :
                              b.bucket === '1–30 days'   ? '#f1c40f' :
                              b.bucket === '31–90 days'  ? '#e67e22' :
                              b.bucket === '91–180 days' ? '#d35400' : '#c0392b'
                return (
                  <div
                    key={b.bucket}
                    role={isOverdueBucket && b.count > 0 ? 'button' : undefined}
                    onClick={isOverdueBucket && b.count > 0 ? openOverdue : undefined}
                    className={`flex items-center gap-3 text-xs ${isOverdueBucket && b.count > 0 ? 'cursor-pointer group' : ''}`}
                  >
                    <div className="w-28 text-right text-gray-700 font-medium">{b.bucket}</div>
                    <div className="flex-1 bg-gray-100 rounded-full h-4 overflow-hidden">
                      <div className="h-4 rounded-full transition-all duration-700 group-hover:brightness-110" style={{ width: `${pct}%`, backgroundColor: color }} />
                    </div>
                    <div className="w-10 text-right font-bold text-gray-700">{b.count.toLocaleString()}</div>
                  </div>
                )
              })}
            </div>
          </div>
        </div>
      )}

      {/* Condition Rating Trend */}
      <div className="card">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2">
            <BarChart2 size={16} className="text-mbi-navy" />
            <h2 className="font-semibold text-mbi-navy text-sm">Condition Rating Trend</h2>
          </div>
          <div className="flex items-center gap-3 text-[11px] text-gray-500">
            {['Critical','Poor','Fair','Good'].map(c => (
              <span key={c} className="inline-flex items-center gap-1">
                <span className="w-2 h-2 rounded-sm" style={{ backgroundColor: CONDITION_COLORS[c] }} />
                {c}
              </span>
            ))}
          </div>
        </div>
        {trendMonths.length === 0 ? (
          <p className="text-xs text-gray-400 py-6 text-center">No data available</p>
        ) : (
          <div>
            <div className="flex items-stretch gap-2 px-1" style={{ height: '180px' }}>
              {trendMonths.map(m => (
                <div key={m.month} className="flex-1 min-w-0 flex flex-col items-center gap-1 group h-full">
                  <div className="text-[10px] text-gray-400 opacity-0 group-hover:opacity-100 transition-opacity h-3">
                    avg {m.avg_rating.toFixed(1)}
                  </div>
                  <div className="w-full flex-1 flex flex-col justify-end bg-gray-50 rounded overflow-hidden">
                    <div className="w-full flex flex-col-reverse" style={{ height: `${Math.max(4, (m.total / maxTrendTotal) * 100)}%` }}>
                      {(['Good','Fair','Poor','Critical'] as const).map(cat => {
                        const c = Number(m.counts[cat] || 0)
                        if (!c) return null
                        const pctH = (c / m.total) * 100
                        return (
                          <div
                            key={cat}
                            title={`${m.month} · ${cat}: ${c}`}
                            onClick={() => openByCondition(cat)}
                            className="w-full cursor-pointer hover:brightness-110 transition-all"
                            style={{ height: `${pctH}%`, backgroundColor: CONDITION_COLORS[cat], minHeight: '2px' }}
                          />
                        )
                      })}
                    </div>
                  </div>
                  <div className="text-[10px] text-gray-500 font-medium truncate w-full text-center" title={m.month}>
                    {m.month.slice(2)}
                  </div>
                </div>
              ))}
            </div>
            <div className="text-[10px] text-gray-400 mt-2">
              Bucketed by <span className="font-mono">inspection_date</span> month · bar height = inspections recorded · hover for avg rating · click a segment to filter
            </div>
          </div>
        )}
      </div>

      {/* Region × Condition heatmap */}
      <div className="card p-0 overflow-hidden">
        <div className="px-4 py-3 flex items-center gap-2 border-b border-gray-100">
          <BarChart2 size={15} className="text-mbi-navy" />
          <h2 className="font-semibold text-mbi-navy text-sm">Asset Health Heatmap — Region × Condition</h2>
        </div>
        {regionCosts.length === 0 ? (
          <p className="text-xs text-gray-400 py-8 text-center">No data available</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-xs">
              <thead>
                <tr className="bg-mbi-navy text-white">
                  <th className="px-3 py-2 text-left">Region</th>
                  {['Critical','Poor','Fair','Good'].map(c => (
                    <th key={c} className="px-3 py-2 text-center">{c}</th>
                  ))}
                  <th className="px-3 py-2 text-center">Total</th>
                  <th className="px-3 py-2 text-right">Est. Backlog</th>
                </tr>
              </thead>
              <tbody>
                {regionCosts.map((rc, i) => {
                  const row = ['Critical','Poor','Fair','Good'].map(cat => {
                    const found = byRegion.find(r => r.region === rc.region && r.condition_category === cat)
                    return found?.count ?? 0
                  })
                  return (
                    <tr key={rc.region} className={i % 2 === 0 ? 'bg-white' : 'bg-mbi-light'}>
                      <td
                        className="px-3 py-2 font-semibold text-gray-700 cursor-pointer hover:text-mbi-navy hover:underline"
                        onClick={() => openByRegion(rc.region)}
                      >
                        {rc.region}
                      </td>
                      {row.map((cnt, j) => {
                        const cat = ['Critical','Poor','Fair','Good'][j]
                        const maxInCat = Math.max(1, ...byRegion.filter(r => r.condition_category === cat).map(r => r.count))
                        const opacity = cnt === 0 ? 0 : 0.15 + (cnt / maxInCat) * 0.75
                        return (
                          <td
                            key={j}
                            className={`px-3 py-2 text-center font-bold ${cnt > 0 ? 'cursor-pointer hover:ring-2 hover:ring-mbi-orange hover:ring-inset' : ''}`}
                            style={{
                              backgroundColor: cnt > 0
                                ? `${CONDITION_COLORS[cat]}${Math.round(opacity * 255).toString(16).padStart(2, '0')}`
                                : 'transparent',
                            }}
                            onClick={cnt > 0 ? () => openRegionCondition(rc.region, cat) : undefined}
                          >
                            {cnt || '—'}
                          </td>
                        )
                      })}
                      <td className="px-3 py-2 text-center font-bold text-mbi-navy">{rc.count}</td>
                      <td className="px-3 py-2 text-right font-medium text-gray-700">{fmt(rc.total_cost)}</td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>

      <p className="text-xs text-center text-gray-400">
        Data source: mbi_demo.inspectiq.project_assets · Powered by Databricks Unity Catalog · Narrative via Foundation Model API
      </p>

      <AssetDrawer spec={drawer} assets={allAssets} onClose={() => setDrawer(null)} />
    </div>
  )
}
