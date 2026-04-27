import { useState, useEffect, useMemo } from 'react'
import { Search, X, Wrench, FileText, Shield, Users, Wand2, TrendingUp, Database, Sparkles, FilePlus } from 'lucide-react'
import InspectionReportFinder from './tools/InspectionReportFinder'
import PortfolioAnalyzer from './tools/PortfolioAnalyzer'
import InspectionReportDrafter from './tools/InspectionReportDrafter'

type ToolTag = 'Analysis' | 'Documents' | 'Intelligence' | 'Productivity' | 'Research'

interface AgentTool {
  name: string
  tag: ToolTag
  description: string
  functional: boolean
  icon: React.ElementType
}

const AGENT_TOOLS: AgentTool[] = [
  // ── Functional (wired to live endpoints) ───────────────────────────────────
  {
    name: 'Inspection Report Drafter',
    tag: 'Documents',
    description:
      'Draft a full re-inspection report for any asset. Combines past findings (vector search), current portfolio data (SQL), and Claude to produce a polished, MBI-branded document in 30 seconds — replacing hours of manual work.',
    functional: true,
    icon: FilePlus,
  },
  {
    name: 'Inspection Report Finder',
    tag: 'Research',
    description:
      'Search across all MBI inspection reports using natural language. Finds specific findings, deficiencies, and safety risks — with document citations.',
    functional: true,
    icon: Search,
  },
  {
    name: 'Portfolio Analyzer',
    tag: 'Analysis',
    description:
      'Run aggregate queries against the full asset portfolio — counts by discipline, total repair cost, overdue inspections, safety-flagged projects.',
    functional: true,
    icon: Database,
  },
  // ── UI-only placeholders ───────────────────────────────────────────────────
  {
    name: 'Safety Risk Assessor',
    tag: 'Analysis',
    description:
      'Continuously monitors inspection findings for safety risks, scores by severity, and auto-generates immediate-action recommendations with 24-hour response requirements.',
    functional: false,
    icon: Shield,
  },
  {
    name: 'Compliance Report Generator',
    tag: 'Documents',
    description:
      'Generate NBIS- and FHWA-compliant inspection summary reports with executive cover sheets, photo logs, condition rating justifications, and recommended repair timelines.',
    functional: false,
    icon: FileText,
  },
  {
    name: 'Inspector Assignment Optimizer',
    tag: 'Productivity',
    description:
      'Auto-assign upcoming inspections to PEs based on discipline expertise, certification currency, geographic proximity, and workload balancing across the team.',
    functional: false,
    icon: Users,
  },
  {
    name: 'Work Order Drafter',
    tag: 'Documents',
    description:
      'Convert inspection recommendations into structured work orders with scope, quantities, estimated cost, required crews, and priority routing into the CMMS.',
    functional: false,
    icon: Wand2,
  },
  {
    name: 'Bridge Condition Forecaster',
    tag: 'Intelligence',
    description:
      'Project future condition ratings and maintenance cost curves using historical inspection data, deterioration models, and environmental exposure factors.',
    functional: false,
    icon: TrendingUp,
  },
]

const TAG_COLORS: Record<ToolTag, { bg: string; text: string }> = {
  Analysis:     { bg: 'bg-slate-100',  text: 'text-slate-700' },
  Documents:    { bg: 'bg-fuchsia-50', text: 'text-fuchsia-700' },
  Intelligence: { bg: 'bg-orange-50',  text: 'text-orange-700' },
  Productivity: { bg: 'bg-sky-50',     text: 'text-sky-700' },
  Research:     { bg: 'bg-yellow-50',  text: 'text-yellow-700' },
}

export default function AgentToolsView() {
  const [search, setSearch] = useState('')
  const [activeTags, setActiveTags] = useState<Set<ToolTag>>(new Set())
  const [selected, setSelected] = useState<AgentTool | null>(null)

  const filtered = useMemo(() => {
    let result = [...AGENT_TOOLS]
    if (activeTags.size > 0) {
      result = result.filter(t => activeTags.has(t.tag))
    }
    if (search) {
      const q = search.toLowerCase()
      result = result.filter(
        t => t.name.toLowerCase().includes(q) || t.description.toLowerCase().includes(q)
      )
    }
    return result
  }, [search, activeTags])

  const toggleTag = (tag: ToolTag) => {
    setActiveTags(prev => {
      const next = new Set(prev)
      if (next.has(tag)) next.delete(tag)
      else next.add(tag)
      return next
    })
  }

  const tags: ToolTag[] = ['Analysis', 'Documents', 'Intelligence', 'Productivity', 'Research']

  return (
    <div className="py-4">
      {/* Header */}
      <div className="mb-6">
        <h2 className="text-2xl font-bold text-mbi-navy mb-1">Agent Tools</h2>
        <p className="text-sm text-gray-600">
          Specialized AI agents for inspection workflows. Click any tool to launch it.
        </p>
      </div>

      {/* Search + tag pills */}
      <div className="flex items-center gap-3 flex-wrap mb-4">
        <input
          value={search}
          onChange={e => setSearch(e.target.value)}
          placeholder="Search agents..."
          className="w-56 px-3 py-2 border border-gray-200 rounded text-sm focus:outline-none focus:ring-2 focus:ring-mbi-orange"
        />
        <button
          onClick={() => setActiveTags(new Set())}
          className={`px-3 py-1.5 rounded-full text-xs font-semibold border transition-colors ${
            activeTags.size === 0
              ? 'border-mbi-navy bg-mbi-navy text-white'
              : 'border-gray-200 bg-white text-gray-600 hover:border-gray-300'
          }`}
        >
          All
        </button>
        {tags.map(tag => {
          const tc = TAG_COLORS[tag]
          const active = activeTags.has(tag)
          return (
            <button
              key={tag}
              onClick={() => toggleTag(tag)}
              className={`px-3 py-1.5 rounded-full text-xs font-semibold border transition-colors ${
                active
                  ? `${tc.bg} ${tc.text} border-current`
                  : 'border-gray-200 bg-white text-gray-600 hover:border-gray-300'
              }`}
            >
              {tag}
            </button>
          )
        })}
      </div>

      <div className="text-xs text-gray-400 mb-3">
        {filtered.length} agent{filtered.length !== 1 ? 's' : ''}
      </div>

      {/* Card grid */}
      <div className="grid grid-cols-3 gap-4">
        {filtered.map(tool => {
          const tc = TAG_COLORS[tool.tag]
          const Icon = tool.icon
          return (
            <div
              key={tool.name}
              onClick={() => setSelected(tool)}
              className="bg-white rounded-lg border border-gray-200 p-5 cursor-pointer hover:border-mbi-orange hover:shadow-md transition-all"
            >
              <div className="flex items-start justify-between mb-3">
                <div className="flex items-center gap-2">
                  <div className="w-9 h-9 rounded-md bg-mbi-light flex items-center justify-center text-mbi-navy flex-shrink-0">
                    <Icon size={18} />
                  </div>
                  <div className="font-semibold text-gray-900 text-sm leading-tight">
                    {tool.name}
                  </div>
                </div>
                <span className={`${tc.bg} ${tc.text} text-[10px] font-bold px-2 py-0.5 rounded uppercase tracking-wide flex-shrink-0`}>
                  {tool.tag}
                </span>
              </div>
              <p className="text-xs text-gray-600 leading-relaxed">
                {tool.description}
              </p>
              {tool.functional && (
                <div className="mt-3 flex items-center gap-1.5 text-[10px] font-bold text-emerald-700 uppercase tracking-wide">
                  <span className="w-1.5 h-1.5 rounded-full bg-emerald-500" />
                  Live · Connected to endpoint
                </div>
              )}
            </div>
          )
        })}
      </div>

      {/* Modal */}
      {selected && <ToolModal tool={selected} onClose={() => setSelected(null)} />}
    </div>
  )
}

// ---------------------------------------------------------------------------
// Modal — routes to functional flow or static card
// ---------------------------------------------------------------------------

function ToolModal({ tool, onClose }: { tool: AgentTool; onClose: () => void }) {
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose() }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [onClose])

  if (tool.functional && tool.name === 'Inspection Report Drafter') {
    return <InspectionReportDrafter onClose={onClose} />
  }
  if (tool.functional && tool.name === 'Inspection Report Finder') {
    return <InspectionReportFinder onClose={onClose} />
  }
  if (tool.functional && tool.name === 'Portfolio Analyzer') {
    return <PortfolioAnalyzer onClose={onClose} />
  }

  // UI-only static modal
  const tc = TAG_COLORS[tool.tag]
  const Icon = tool.icon
  return (
    <>
      <div onClick={onClose} className="fixed inset-0 bg-black/50 z-40" />
      <div className="fixed inset-0 flex items-center justify-center z-50 pointer-events-none">
        <div className="bg-white rounded-xl w-[540px] max-w-[92vw] shadow-2xl pointer-events-auto overflow-hidden">
          {/* Header */}
          <div className="flex items-center justify-between px-7 py-4 border-b border-gray-200">
            <div className="text-sm font-bold text-mbi-navy">Agent Tool</div>
            <button
              onClick={onClose}
              className="w-7 h-7 rounded border border-gray-200 flex items-center justify-center text-gray-500 hover:bg-gray-50"
            >
              <X size={14} />
            </button>
          </div>

          {/* Body */}
          <div className="px-7 py-6">
            <div className="flex items-center gap-3 mb-4">
              <div className="w-11 h-11 rounded-lg bg-mbi-light flex items-center justify-center text-mbi-navy">
                <Icon size={22} />
              </div>
              <div className="font-bold text-xl text-gray-900">{tool.name}</div>
              <span className={`${tc.bg} ${tc.text} text-[10px] font-bold px-2 py-1 rounded uppercase tracking-wide`}>
                {tool.tag}
              </span>
            </div>

            <div className="bg-gray-50 rounded-lg px-4 py-3 mb-5 text-[13px] text-gray-700 leading-relaxed">
              {tool.description}
            </div>

            <div className="text-[10px] font-bold text-gray-400 uppercase tracking-wider mb-2">
              Capabilities
            </div>
            <div className="flex flex-wrap gap-2 mb-5">
              {['Natural Language Input', 'AI-Powered', 'InspectIQ Optimized', 'Instant Results'].map(cap => (
                <span key={cap} className="text-xs text-mbi-navy bg-orange-50 border border-orange-100 px-2.5 py-1 rounded">
                  {cap}
                </span>
              ))}
            </div>

            <div className="bg-amber-50 border border-amber-200 rounded-lg px-3 py-2 text-xs text-amber-900 flex items-start gap-2">
              <Sparkles size={14} className="flex-shrink-0 mt-0.5" />
              <span>
                This tool is a design prototype. In production, it would wire to the MBI inspection
                management system, CMMS, and relevant Databricks endpoints.
              </span>
            </div>
          </div>

          {/* Footer */}
          <div className="flex justify-end gap-3 px-7 py-4 border-t border-gray-200 bg-gray-50">
            <button
              onClick={onClose}
              className="px-4 py-2 border border-gray-200 rounded-lg bg-white text-gray-700 text-sm font-medium hover:bg-gray-100"
            >
              Close
            </button>
            <button
              disabled
              className="px-5 py-2 rounded-lg bg-mbi-navy/40 text-white text-sm font-semibold flex items-center gap-2 cursor-not-allowed"
            >
              <Wrench size={14} />
              Launch Agent
            </button>
          </div>
        </div>
      </div>
    </>
  )
}
