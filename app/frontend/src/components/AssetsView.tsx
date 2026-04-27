import { useState, useEffect } from 'react'
import { Search, AlertTriangle, CheckCircle, Clock, TrendingDown } from 'lucide-react'

interface Summary {
  total_assets: number
  critical_count: number
  poor_count: number
  fair_count: number
  good_count: number
  overdue_count: number
  total_backlog: number
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
  last_inspection_date: string
}

const CONDITION_COLORS: Record<string, string> = {
  Critical: 'bg-red-100 text-red-700 border-red-200',
  Poor:     'bg-orange-100 text-orange-700 border-orange-200',
  Fair:     'bg-yellow-100 text-yellow-700 border-yellow-200',
  Good:     'bg-green-100 text-green-700 border-green-200',
}

const fmt = (n: number) =>
  n >= 1_000_000
    ? `$${(n / 1_000_000).toFixed(1)}M`
    : n >= 1_000
    ? `$${(n / 1_000).toFixed(0)}K`
    : `$${n}`

export default function AssetsView() {
  const [summary, setSummary] = useState<Summary | null>(null)
  const [assets, setAssets] = useState<Asset[]>([])
  const [search, setSearch] = useState('')
  const [region, setRegion] = useState('')
  const [condition, setCondition] = useState('')
  const [loading, setLoading] = useState(false)
  const [view, setView] = useState<'search' | 'risk'>('risk')

  useEffect(() => {
    fetch('/api/assets/summary').then(r => r.json()).then(setSummary)
    loadTopRisk()
  }, [])

  const loadTopRisk = async () => {
    setLoading(true)
    const data = await fetch('/api/assets/top-risk?limit=20').then(r => r.json())
    setAssets(Array.isArray(data) ? data : [])
    setLoading(false)
  }

  const doSearch = async () => {
    setLoading(true)
    setView('search')
    const params = new URLSearchParams()
    if (search) params.set('q', search)
    if (region) params.set('region', region)
    if (condition) params.set('condition', condition)
    const data = await fetch(`/api/assets/search?${params}`).then(r => r.json())
    setAssets(Array.isArray(data) ? data : [])
    setLoading(false)
  }

  return (
    <div className="space-y-4">
      {/* KPI row */}
      {summary && (
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          {[
            { label: 'Total Assets', value: summary.total_assets, icon: <CheckCircle size={18} className="text-mbi-navy" />, sub: '' },
            { label: 'Critical / Poor', value: `${summary.critical_count} / ${summary.poor_count}`, icon: <AlertTriangle size={18} className="text-red-500" />, sub: 'Need attention' },
            { label: 'Overdue Inspections', value: summary.overdue_count, icon: <Clock size={18} className="text-orange-500" />, sub: 'Past due' },
            { label: 'Maintenance Backlog', value: fmt(summary.total_backlog), icon: <TrendingDown size={18} className="text-mbi-orange" />, sub: 'Estimated total' },
          ].map((kpi, i) => (
            <div key={i} className="card flex items-start gap-3">
              <div className="mt-0.5">{kpi.icon}</div>
              <div>
                <div className="text-xl font-bold text-mbi-navy">{kpi.value}</div>
                <div className="text-xs font-medium text-gray-600">{kpi.label}</div>
                {kpi.sub && <div className="text-xs text-gray-400">{kpi.sub}</div>}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Search bar */}
      <div className="card flex gap-2 flex-wrap">
        <div className="flex-1 min-w-48 relative">
          <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
          <input
            value={search}
            onChange={e => setSearch(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && doSearch()}
            placeholder="Search asset name or ID..."
            className="w-full pl-8 pr-3 py-2 text-sm border border-gray-300 rounded-lg focus:outline-none focus:border-mbi-navy"
          />
        </div>
        <select
          value={region}
          onChange={e => setRegion(e.target.value)}
          className="text-sm border border-gray-300 rounded-lg px-3 py-2 focus:outline-none focus:border-mbi-navy"
        >
          <option value="">All Regions</option>
          {['Northeast','Southeast','Midwest','Southwest','Northwest','Mid-Atlantic'].map(r => (
            <option key={r}>{r}</option>
          ))}
        </select>
        <select
          value={condition}
          onChange={e => setCondition(e.target.value)}
          className="text-sm border border-gray-300 rounded-lg px-3 py-2 focus:outline-none focus:border-mbi-navy"
        >
          <option value="">All Conditions</option>
          {['Critical','Poor','Fair','Good'].map(c => <option key={c}>{c}</option>)}
        </select>
        <button onClick={doSearch} className="btn-primary text-sm">Search</button>
        <button
          onClick={() => { setSearch(''); setRegion(''); setCondition(''); setView('risk'); loadTopRisk() }}
          className="text-sm text-mbi-steel hover:text-mbi-navy underline"
        >
          Top Risk
        </button>
      </div>

      {/* Asset table */}
      <div className="card p-0 overflow-hidden">
        <div className="px-4 py-3 border-b border-gray-100 flex items-center justify-between">
          <h2 className="font-semibold text-mbi-navy text-sm">
            {view === 'risk' ? '20 Highest-Risk Assets' : `${assets.length} Results`}
          </h2>
          {loading && <span className="text-xs text-gray-400 animate-pulse">Loading...</span>}
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-xs">
            <thead>
              <tr className="bg-mbi-navy text-white">
                {['Asset ID','Name','Type','Region','Rating','Condition','Overdue','Est. Cost','Last Inspected'].map(h => (
                  <th key={h} className="px-3 py-2.5 text-left font-medium whitespace-nowrap">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {assets.map((a, i) => (
                <tr key={a.asset_id} className={i % 2 === 0 ? 'bg-white' : 'bg-mbi-light'}>
                  <td className="px-3 py-2 font-mono text-mbi-navy whitespace-nowrap">{a.asset_id}</td>
                  <td className="px-3 py-2 font-medium max-w-[160px] truncate">{a.asset_name}</td>
                  <td className="px-3 py-2 whitespace-nowrap text-gray-600">{a.asset_type}</td>
                  <td className="px-3 py-2 whitespace-nowrap">{a.region}</td>
                  <td className="px-3 py-2 text-center font-bold text-mbi-navy">{a.condition_rating}</td>
                  <td className="px-3 py-2">
                    <span className={`px-2 py-0.5 rounded-full border text-xs font-medium ${CONDITION_COLORS[a.condition_category] ?? ''}`}>
                      {a.condition_category}
                    </span>
                  </td>
                  <td className="px-3 py-2 text-center">
                    {a.inspection_overdue
                      ? <span className="text-red-500 font-bold">YES</span>
                      : <span className="text-green-600">—</span>}
                  </td>
                  <td className="px-3 py-2 text-right whitespace-nowrap">{fmt(a.estimated_maintenance_cost)}</td>
                  <td className="px-3 py-2 whitespace-nowrap text-gray-500">{a.last_inspection_date}</td>
                </tr>
              ))}
              {assets.length === 0 && !loading && (
                <tr><td colSpan={9} className="px-4 py-8 text-center text-gray-400">No assets found</td></tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}
