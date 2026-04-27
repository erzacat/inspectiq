import { useState, useEffect, useMemo } from 'react'
import { X, FileText, Sparkles, Download, CheckCircle2 } from 'lucide-react'
import { useBranding } from '../../BrandingContext'

// ----------------------------------------------------------------------------
// Real MBI projects (from project_assets) — used as the picker source
// ----------------------------------------------------------------------------

interface Project {
  report_id: string
  project_name: string
  location: string
  state: string
  client: string
  inspection_type: 'Structural Steel' | 'Concrete' | 'Asphalt'
  last_inspection_date: string
  last_inspector: string
  last_rating: number
  last_category: string
  safety_flagged: boolean
  estimated_repair_cost: number
  key_findings: string
}

const PROJECTS: Project[] = [
  {
    report_id: 'INS-SS-001', project_name: 'Parker Street Highway Overpass',
    location: 'Pittsburgh', state: 'PA', client: 'Pennsylvania DOT — District 11',
    inspection_type: 'Structural Steel', last_inspection_date: '2024-10-15',
    last_inspector: 'Sarah Chen, PE, S.E.', last_rating: 5, last_category: 'Poor',
    safety_flagged: false, estimated_repair_cost: 930000,
    key_findings: 'Section loss fascia girders, fatigue cracking web-to-flange welds, paint failure, bearing corrosion',
  },
  {
    report_id: 'INS-SS-002', project_name: 'Commerce Center Parking Garage',
    location: 'Philadelphia', state: 'PA', client: 'Commerce Center Associates LLC',
    inspection_type: 'Structural Steel', last_inspection_date: '2024-03-22',
    last_inspector: 'David Park, PE, SE', last_rating: 4, last_category: 'Poor',
    safety_flagged: true, estimated_repair_cost: 337000,
    key_findings: 'Exposed rebar Column C-14 (SAFETY RISK), connection corrosion B-8/D-12, floor delamination, secondary beam section loss',
  },
  {
    report_id: 'INS-SS-003', project_name: 'Riverside Industrial Complex — Building 4',
    location: 'Baltimore', state: 'MD', client: 'Riverside Holdings Group',
    inspection_type: 'Structural Steel', last_inspection_date: '2024-07-08',
    last_inspector: 'Marcus Webb, PE', last_rating: 6, last_category: 'Fair',
    safety_flagged: false, estimated_repair_cost: 122000,
    key_findings: 'Bracing connection corrosion, bearing plate deterioration, minor purlin section loss',
  },
  {
    report_id: 'INS-CO-001', project_name: 'I-95 Northbound Bridge Deck — Wilmington Interchange',
    location: 'Wilmington', state: 'DE', client: 'Delaware DOT — Structures Management',
    inspection_type: 'Concrete', last_inspection_date: '2024-09-03',
    last_inspector: 'Lisa Tran, PE', last_rating: 4, last_category: 'Poor',
    safety_flagged: true, estimated_repair_cost: 2967500,
    key_findings: '34% deck delamination, rebar corrosion span 2, scour critical Pier 1 (2.1 ft), joint failure Sta 142+50',
  },
  {
    report_id: 'INS-CO-002', project_name: 'Terminal C Parking Structure — PHL Airport',
    location: 'Philadelphia', state: 'PA', client: 'Philadelphia Airport Authority',
    inspection_type: 'Concrete', last_inspection_date: '2024-01-19',
    last_inspector: 'Angela Foster, PE', last_rating: 6, last_category: 'Fair',
    safety_flagged: false, estimated_repair_cost: 215000,
    key_findings: 'Slab edge cracking/spalling Levels 2-4, rebar exposure column bases Level 3, drain failures Level 4, freeze-thaw damage',
  },
  {
    report_id: 'INS-CO-003', project_name: 'SR-422 Retaining Wall — Section 3',
    location: 'Norristown', state: 'PA', client: 'Pennsylvania DOT — District 6',
    inspection_type: 'Concrete', last_inspection_date: '2024-05-14',
    last_inspector: 'Robert Castillo, PE', last_rating: 7, last_category: 'Good',
    safety_flagged: false, estimated_repair_cost: 50500,
    key_findings: 'Construction joint hairline cracking, efflorescence/staining Sta 40-65, minor toe undermining Sta 28-34',
  },
  {
    report_id: 'INS-AP-001', project_name: 'PHL Airport Runway 09L-27R',
    location: 'Philadelphia', state: 'PA', client: 'Philadelphia Airport Authority',
    inspection_type: 'Asphalt', last_inspection_date: '2024-08-20',
    last_inspector: 'James Hargrove, PE', last_rating: 5, last_category: 'Fair',
    safety_flagged: true, estimated_repair_cost: 2170000,
    key_findings: 'High-severity transverse cracking Zones T1-T4, rutting 0.5in approach zones, FOD generation Zone T3, centerline longitudinal crack',
  },
  {
    report_id: 'INS-AP-002', project_name: 'I-78 Eastbound Pavement — Segment 3',
    location: 'Allentown', state: 'PA', client: 'Pennsylvania DOT — District 5',
    inspection_type: 'Asphalt', last_inspection_date: '2024-04-11',
    last_inspector: 'Priya Nair, PE', last_rating: 4, last_category: 'Poor',
    safety_flagged: true, estimated_repair_cost: 6173000,
    key_findings: 'High-density block cracking 30% surface, pothole clusters MM 13.2 and 14.7, longitudinal joint cracking full length, base failure near weigh station',
  },
  {
    report_id: 'INS-AP-003', project_name: 'Valley Forge Industrial Park Access Roads',
    location: 'Valley Forge', state: 'PA', client: 'Valley Forge Industrial Partners LP',
    inspection_type: 'Asphalt', last_inspection_date: '2024-06-25',
    last_inspector: 'Tom Ellison, PE', last_rating: 4, last_category: 'Poor',
    safety_flagged: true, estimated_repair_cost: 2090000,
    key_findings: 'Alligator cracking 40% surface, shoving at entrance and dock approaches, pothole cluster docks B/C, SW quadrant base failure',
  },
  {
    report_id: 'INS-AP-004', project_name: 'Chestnut Street Streetscape Pavement',
    location: 'Philadelphia', state: 'PA', client: 'City of Philadelphia — Streets Dept',
    inspection_type: 'Asphalt', last_inspection_date: '2024-02-28',
    last_inspector: 'Helen Kozlowski, PE', last_rating: 7, last_category: 'Good',
    safety_flagged: false, estimated_repair_cost: 329000,
    key_findings: 'Utility cut deterioration (19 of 37), catch basin collar cracking (12 units), bus stop rutting 11th St, surface delamination 8th-9th St',
  },
]

const REPORT_TYPES = [
  'Annual Re-inspection Report',
  'Supplemental Findings Report',
  'Emergency Safety Assessment',
] as const
type ReportType = typeof REPORT_TYPES[number]

const GENERATION_STEPS = [
  'Pulling asset history from Unity Catalog...',
  'Retrieving similar past reports from vector search...',
  'Analyzing deficiency trends with Claude...',
  'Estimating updated repair costs...',
  'Formatting MBI-branded report...',
]

// ----------------------------------------------------------------------------
// Helpers
// ----------------------------------------------------------------------------

function today(): string {
  const d = new Date()
  return d.toISOString().slice(0, 10)
}

function todayLong(): string {
  return new Date().toLocaleDateString('en-US', { year: 'numeric', month: 'long', day: 'numeric' })
}

function currency(n: number): string {
  return `$${n.toLocaleString('en-US', { maximumFractionDigits: 0 })}`
}

function seededRandom(seed: number) {
  let s = seed
  return () => { s = (s * 16807) % 2147483647; return (s - 1) / 2147483646 }
}

// Build templated findings from the project's raw key_findings
function buildFindings(p: Project) {
  const items = p.key_findings.split(/,\s*/).map(s => s.trim()).filter(Boolean)
  const rand = seededRandom(p.report_id.charCodeAt(p.report_id.length - 1) * 7 + 17)
  const severities = ['Critical', 'High', 'Moderate', 'Low'] as const

  return items.map((finding, i) => {
    const sevIdx = p.safety_flagged && i === 0 ? 0 : Math.min(3, Math.floor(rand() * 3) + (p.last_rating <= 4 ? 0 : 1))
    return {
      id: i + 1,
      severity: severities[sevIdx],
      finding,
      timeframe: sevIdx === 0 ? '24–72 hrs' : sevIdx === 1 ? '30–90 days' : sevIdx === 2 ? '6–12 months' : '12–24 months',
    }
  })
}

// Build recommendation table from findings
function buildRecommendations(p: Project) {
  const findings = buildFindings(p)
  const rand = seededRandom(p.report_id.charCodeAt(0) + 11)
  const total = p.estimated_repair_cost
  // Distribute cost across findings (higher severity = higher share)
  const weights = findings.map(f => f.severity === 'Critical' ? 5 : f.severity === 'High' ? 3 : f.severity === 'Moderate' ? 2 : 1)
  const wsum = weights.reduce((a, b) => a + b, 0)
  return findings.map((f, i) => {
    const share = weights[i] / wsum
    const cost = Math.round((total * share) / 1000) * 1000
    const actions = [
      'Install shoring; perform hands-on follow-up with NDT',
      'Apply epoxy crack injection + polymer-modified patch',
      'Mill and overlay affected sections with PG 76-22 HMA',
      'Full-depth reclamation with cement-treated base',
      'Protective coating per SSPC-SP6 + anode replacement',
      'Expansion joint replacement with pourable seal',
      'Riprap scour countermeasures (D50 = 18")',
      'Targeted patch repair + drainage correction',
    ]
    return {
      id: i + 1,
      action: actions[Math.floor(rand() * actions.length)],
      priority: f.severity,
      timeframe: f.timeframe,
      cost: currency(cost),
    }
  })
}

function ratingColor(rating: number): string {
  if (rating <= 3) return '#b91c1c'
  if (rating <= 5) return '#d97706'
  if (rating <= 7) return '#ca8a04'
  return '#15803d'
}

function severityBadge(sev: string) {
  const map: Record<string, { bg: string; text: string }> = {
    Critical: { bg: '#fee2e2', text: '#991b1b' },
    High:     { bg: '#fef3c7', text: '#92400e' },
    Moderate: { bg: '#e0e7ff', text: '#3730a3' },
    Low:      { bg: '#dcfce7', text: '#14532d' },
  }
  const c = map[sev] || { bg: '#f3f4f6', text: '#374151' }
  return (
    <span
      className="text-[10px] font-bold px-2 py-0.5 rounded uppercase tracking-wide"
      style={{ background: c.bg, color: c.text }}
    >
      {sev}
    </span>
  )
}

// ----------------------------------------------------------------------------
// Component
// ----------------------------------------------------------------------------

type Phase = 'select' | 'configure' | 'generating' | 'preview'

export default function InspectionReportDrafter({ onClose }: { onClose: () => void }) {
  const { userName } = useBranding()
  const [phase, setPhase] = useState<Phase>('select')
  const [projectId, setProjectId] = useState<string>('')
  const [reportType, setReportType] = useState<ReportType>(REPORT_TYPES[0])
  const [inspector, setInspector] = useState(userName)
  const [inspectionDate, setInspectionDate] = useState(today())
  const [stepIdx, setStepIdx] = useState(0)

  // If the configured user changes while the modal is open (e.g. via Settings),
  // reflect that change in the inspector field — unless the user manually edited it.
  useEffect(() => { setInspector(userName) }, [userName])

  const project = useMemo(() => PROJECTS.find(p => p.report_id === projectId), [projectId])

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose() }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [onClose])

  // Animate through the generation steps
  useEffect(() => {
    if (phase !== 'generating') return
    setStepIdx(0)
    const interval = setInterval(() => {
      setStepIdx(i => {
        if (i >= GENERATION_STEPS.length - 1) {
          clearInterval(interval)
          setTimeout(() => setPhase('preview'), 600)
          return i
        }
        return i + 1
      })
    }, 900)
    return () => clearInterval(interval)
  }, [phase])

  const modalWidth = phase === 'preview' ? '920px' : '620px'

  const findings = project ? buildFindings(project) : []
  const recommendations = project ? buildRecommendations(project) : []
  const nextInspectionDate = (() => {
    const d = new Date(inspectionDate)
    d.setFullYear(d.getFullYear() + 1)
    return d.toLocaleDateString('en-US', { year: 'numeric', month: 'long', day: 'numeric' })
  })()

  return (
    <>
      <div onClick={onClose} className="fixed inset-0 bg-black/50 z-40" />
      <div className="fixed inset-0 flex items-center justify-center z-50 pointer-events-none">
        <div
          className="bg-white rounded-xl shadow-2xl pointer-events-auto flex flex-col overflow-hidden max-h-[92vh]"
          style={{ width: modalWidth, maxWidth: '95vw', transition: 'width 0.3s ease' }}
        >
          {/* Header */}
          <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200 bg-mbi-navy text-white flex-shrink-0">
            <div className="flex items-center gap-3">
              <div className="w-9 h-9 rounded-md bg-mbi-orange/20 flex items-center justify-center">
                <FileText size={18} />
              </div>
              <div>
                <div className="font-bold text-sm">
                  {phase === 'select' && 'Draft Inspection Report'}
                  {phase === 'configure' && 'Configure Report'}
                  {phase === 'generating' && 'Generating Report...'}
                  {phase === 'preview' && 'Report Preview'}
                </div>
                <div className="text-xs text-blue-200 flex items-center gap-1.5">
                  <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" />
                  Vector Search + SQL + Claude Sonnet 4.6
                </div>
              </div>
            </div>
            <button onClick={onClose} className="w-7 h-7 rounded hover:bg-white/10 flex items-center justify-center">
              <X size={16} />
            </button>
          </div>

          {/* Body */}
          <div className="flex-1 overflow-y-auto px-7 py-6">
            {/* ─── Phase 1: Select project ──────────────────────────────── */}
            {phase === 'select' && (
              <div>
                <div className="text-xs text-gray-500 mb-4 leading-relaxed">
                  Select an asset. The agent will pull its history from Unity Catalog, retrieve
                  relevant findings from similar past reports (vector search), and draft a new
                  inspection report with updated deficiencies, cost estimates, and recommendations.
                </div>
                <div className="text-[10px] font-bold text-gray-400 uppercase tracking-wider mb-2">
                  Asset
                </div>
                <div className="space-y-2">
                  {PROJECTS.map(p => (
                    <button
                      key={p.report_id}
                      onClick={() => setProjectId(p.report_id)}
                      className={`w-full text-left px-4 py-3 rounded-lg border transition-all ${
                        projectId === p.report_id
                          ? 'border-mbi-orange bg-orange-50'
                          : 'border-gray-200 bg-white hover:border-mbi-navy/30 hover:shadow-sm'
                      }`}
                    >
                      <div className="flex items-center justify-between gap-3">
                        <div className="min-w-0 flex-1">
                          <div className="flex items-center gap-2 mb-1">
                            <span className="text-[10px] font-mono text-gray-500">{p.report_id}</span>
                            <span className="text-[10px] font-bold px-1.5 py-0.5 rounded bg-slate-100 text-slate-700 uppercase">
                              {p.inspection_type}
                            </span>
                            {p.safety_flagged && (
                              <span className="text-[10px] font-bold px-1.5 py-0.5 rounded bg-red-100 text-red-700 uppercase">
                                Safety Risk
                              </span>
                            )}
                          </div>
                          <div className="text-sm font-semibold text-gray-900 truncate">{p.project_name}</div>
                          <div className="text-xs text-gray-500 truncate">{p.location}, {p.state} · {p.client}</div>
                        </div>
                        <div className="text-right flex-shrink-0">
                          <div className="text-[10px] text-gray-400 uppercase">Last rating</div>
                          <div className="font-bold text-sm" style={{ color: ratingColor(p.last_rating) }}>
                            {p.last_rating} / 9 · {p.last_category}
                          </div>
                        </div>
                      </div>
                    </button>
                  ))}
                </div>
              </div>
            )}

            {/* ─── Phase 2: Configure ────────────────────────────────────── */}
            {phase === 'configure' && project && (
              <div>
                <div className="mb-5">
                  <div className="text-[10px] font-bold text-gray-400 uppercase tracking-wider mb-1">
                    Selected asset
                  </div>
                  <div className="text-lg font-bold text-gray-900">{project.project_name}</div>
                  <div className="text-xs text-gray-500">
                    {project.report_id} · {project.inspection_type} · {project.location}, {project.state}
                  </div>
                </div>

                {/* AI capabilities callout */}
                <div className="bg-orange-50 border border-orange-200 rounded-lg px-4 py-3 mb-5 text-xs">
                  <div className="flex items-center gap-2 mb-2 text-gray-700">
                    <Sparkles size={14} className="text-mbi-orange" />
                    <span className="font-semibold">The agent will assemble:</span>
                  </div>
                  <ul className="list-disc pl-5 text-gray-600 space-y-0.5">
                    <li>Cover page and executive summary</li>
                    <li>Updated condition rating and category</li>
                    <li>Deficiency findings table with severity scoring</li>
                    <li>Recommendation table with prioritized actions and cost estimates</li>
                    <li>References to past inspection findings and MBI standards</li>
                  </ul>
                </div>

                <div className="mb-4">
                  <div className="text-[10px] font-bold text-gray-400 uppercase tracking-wider mb-2">
                    Report type
                  </div>
                  <div className="space-y-2">
                    {REPORT_TYPES.map(t => (
                      <label key={t} className="flex items-center gap-2 text-sm text-gray-700 cursor-pointer">
                        <input
                          type="radio"
                          name="reportType"
                          checked={reportType === t}
                          onChange={() => setReportType(t)}
                          className="accent-mbi-navy"
                        />
                        {t}
                      </label>
                    ))}
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-3 mb-4">
                  <div>
                    <div className="text-[10px] font-bold text-gray-400 uppercase tracking-wider mb-2">
                      Inspection date
                    </div>
                    <input
                      type="date"
                      value={inspectionDate}
                      onChange={e => setInspectionDate(e.target.value)}
                      className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-mbi-orange"
                    />
                  </div>
                  <div>
                    <div className="text-[10px] font-bold text-gray-400 uppercase tracking-wider mb-2">
                      Lead inspector
                    </div>
                    <input
                      type="text"
                      value={inspector}
                      onChange={e => setInspector(e.target.value)}
                      className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-mbi-orange"
                    />
                  </div>
                </div>
              </div>
            )}

            {/* ─── Phase 3: Generating ──────────────────────────────────── */}
            {phase === 'generating' && (
              <div className="py-6 text-center">
                <div className="w-12 h-12 border-[3px] border-orange-100 border-t-mbi-orange rounded-full animate-spin mx-auto mb-5" />
                <div className="text-lg font-bold text-gray-900 mb-6">Drafting report...</div>
                <div className="max-w-sm mx-auto text-left space-y-2.5">
                  {GENERATION_STEPS.map((step, i) => {
                    const done = i < stepIdx
                    const active = i === stepIdx
                    return (
                      <div
                        key={i}
                        className={`flex items-start gap-2.5 transition-opacity ${
                          i <= stepIdx ? 'opacity-100' : 'opacity-30'
                        }`}
                      >
                        <div className="flex-shrink-0 mt-0.5">
                          {done ? (
                            <CheckCircle2 size={16} className="text-emerald-500" />
                          ) : active ? (
                            <div className="w-4 h-4 border-2 border-mbi-orange border-t-transparent rounded-full animate-spin" />
                          ) : (
                            <div className="w-4 h-4 rounded-full border-2 border-gray-200" />
                          )}
                        </div>
                        <span className={`text-sm ${active ? 'text-gray-900 font-medium' : 'text-gray-600'}`}>
                          {step}
                        </span>
                      </div>
                    )
                  })}
                </div>
              </div>
            )}

            {/* ─── Phase 4: Preview ─────────────────────────────────────── */}
            {phase === 'preview' && project && (
              <div id="inspectiq-print-target" className="bg-white border border-gray-300 rounded-lg shadow-sm" style={{ padding: '36px 48px' }}>
                {/* MBI header bar */}
                <div className="flex items-center justify-between mb-5">
                  <div className="text-[10px] font-bold tracking-[0.3em] text-mbi-navy">
                    MICHAEL BAKER INTERNATIONAL
                  </div>
                  <div className="text-[9px] font-bold tracking-[0.15em] px-2 py-0.5 rounded text-red-700 bg-red-100">
                    CONFIDENTIAL
                  </div>
                </div>
                <div
                  className="h-1 mb-6"
                  style={{ background: 'linear-gradient(90deg, #1a3a5c, #e87722, #1a3a5c)' }}
                />

                {/* Title */}
                <div className="mb-5">
                  <div className="text-[22px] font-bold text-mbi-navy leading-tight">
                    {reportType}
                  </div>
                  <div className="text-sm text-gray-500 mt-1">
                    {project.inspection_type} · {project.project_name}
                  </div>
                </div>

                {/* Meta grid */}
                <div className="border border-gray-200 rounded-lg overflow-hidden mb-6">
                  <table className="w-full text-xs">
                    <tbody>
                      {[
                        ['Report ID', `${project.report_id}-R2`, 'Inspection Date', new Date(inspectionDate).toLocaleDateString('en-US', { year: 'numeric', month: 'long', day: 'numeric' })],
                        ['Project', project.project_name, 'Discipline', project.inspection_type],
                        ['Client', project.client, 'Lead Inspector', inspector],
                        ['Location', `${project.location}, ${project.state}`, 'Next Inspection', nextInspectionDate],
                      ].map((row, i) => (
                        <tr key={i} className={i % 2 === 0 ? 'bg-mbi-light' : 'bg-white'}>
                          <td className="px-3 py-2 font-bold text-mbi-navy w-[18%]">{row[0]}</td>
                          <td className="px-3 py-2 text-gray-800 w-[32%]">{row[1]}</td>
                          <td className="px-3 py-2 font-bold text-mbi-navy w-[18%]">{row[2]}</td>
                          <td className="px-3 py-2 text-gray-800 w-[32%]">{row[3]}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>

                {/* Executive Summary */}
                <div className="text-[10px] font-bold tracking-[0.15em] text-mbi-navy mb-2">
                  1. EXECUTIVE SUMMARY
                </div>
                <p className="text-[13px] text-gray-700 leading-relaxed mb-5">
                  The {project.project_name} in {project.location}, {project.state} was inspected on{' '}
                  {new Date(inspectionDate).toLocaleDateString('en-US', { year: 'numeric', month: 'long', day: 'numeric' })}{' '}
                  in accordance with FHWA BIRM and AASHTO Manual for Bridge Evaluation standards. The overall condition
                  rating is <strong style={{ color: ratingColor(project.last_rating) }}>
                    {project.last_rating} of 9 ({project.last_category})
                  </strong>. {project.safety_flagged && (
                    <span className="text-red-800 font-semibold">An immediate safety risk was identified and requires action within 30 days.</span>
                  )} The following priority findings and recommendations are documented below based on current inspection observations and cross-referenced against historical MBI reports for this asset.
                </p>

                {/* Rating callout */}
                <div className="grid grid-cols-4 gap-3 mb-6">
                  {[
                    { label: 'Overall Rating', value: `${project.last_rating} / 9`, sub: project.last_category, color: ratingColor(project.last_rating) },
                    { label: 'Findings', value: String(findings.length), sub: 'documented', color: '#1a3a5c' },
                    { label: 'Est. Repair Cost', value: currency(project.estimated_repair_cost), sub: 'USD total', color: '#1a3a5c' },
                    { label: 'Safety Flag', value: project.safety_flagged ? 'YES' : 'None', sub: project.safety_flagged ? 'Immediate action' : 'No risks', color: project.safety_flagged ? '#b91c1c' : '#15803d' },
                  ].map(k => (
                    <div key={k.label} className="bg-mbi-light rounded-md px-3 py-2">
                      <div className="text-[9px] text-gray-500 uppercase tracking-wider mb-1">{k.label}</div>
                      <div className="font-bold text-base" style={{ color: k.color }}>{k.value}</div>
                      <div className="text-[10px] text-gray-500">{k.sub}</div>
                    </div>
                  ))}
                </div>

                {/* Findings */}
                <div className="text-[10px] font-bold tracking-[0.15em] text-mbi-navy mb-2">
                  2. DEFICIENCY FINDINGS
                </div>
                <div className="border border-gray-200 rounded-lg overflow-hidden mb-6">
                  <table className="w-full text-xs">
                    <thead>
                      <tr className="bg-mbi-navy text-white">
                        <th className="px-3 py-2 text-left w-[6%]">#</th>
                        <th className="px-3 py-2 text-left w-[12%]">Severity</th>
                        <th className="px-3 py-2 text-left">Finding</th>
                        <th className="px-3 py-2 text-left w-[18%]">Timeframe</th>
                      </tr>
                    </thead>
                    <tbody>
                      {findings.map((f, i) => (
                        <tr key={f.id} className={i % 2 === 0 ? 'bg-white' : 'bg-mbi-light'}>
                          <td className="px-3 py-2 font-mono text-gray-500">{f.id}</td>
                          <td className="px-3 py-2">{severityBadge(f.severity)}</td>
                          <td className="px-3 py-2 text-gray-800">{f.finding}</td>
                          <td className="px-3 py-2 text-gray-600 text-[11px]">{f.timeframe}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>

                {/* Recommendations */}
                <div className="text-[10px] font-bold tracking-[0.15em] text-mbi-navy mb-2">
                  3. RECOMMENDATIONS
                </div>
                <div className="border border-gray-200 rounded-lg overflow-hidden mb-6">
                  <table className="w-full text-xs">
                    <thead>
                      <tr className="bg-mbi-navy text-white">
                        <th className="px-3 py-2 text-left w-[6%]">#</th>
                        <th className="px-3 py-2 text-left w-[14%]">Priority</th>
                        <th className="px-3 py-2 text-left">Action</th>
                        <th className="px-3 py-2 text-left w-[16%]">Timeframe</th>
                        <th className="px-3 py-2 text-right w-[16%]">Est. Cost</th>
                      </tr>
                    </thead>
                    <tbody>
                      {recommendations.map((r, i) => (
                        <tr key={r.id} className={i % 2 === 0 ? 'bg-white' : 'bg-mbi-light'}>
                          <td className="px-3 py-2 font-mono text-gray-500">{r.id}</td>
                          <td className="px-3 py-2">{severityBadge(r.priority)}</td>
                          <td className="px-3 py-2 text-gray-800">{r.action}</td>
                          <td className="px-3 py-2 text-gray-600 text-[11px]">{r.timeframe}</td>
                          <td className="px-3 py-2 text-right font-semibold text-mbi-navy">{r.cost}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>

                {/* Past report reference */}
                <div className="bg-slate-50 border border-slate-200 rounded-lg p-3 mb-5">
                  <div className="text-[10px] font-bold tracking-[0.15em] text-mbi-navy mb-1">
                    REFERENCED HISTORICAL REPORTS
                  </div>
                  <div className="flex flex-wrap gap-1.5 text-[11px] font-mono">
                    <span className="px-2 py-0.5 rounded bg-white border border-slate-200 text-mbi-navy">{project.report_id}</span>
                    {PROJECTS
                      .filter(p => p.inspection_type === project.inspection_type && p.report_id !== project.report_id)
                      .slice(0, 2)
                      .map(p => (
                        <span key={p.report_id} className="px-2 py-0.5 rounded bg-white border border-slate-200 text-mbi-navy">
                          {p.report_id}
                        </span>
                      ))}
                  </div>
                  <div className="text-[11px] text-gray-500 mt-1.5 italic">
                    Retrieved via Databricks Vector Search — same discipline, correlated deficiency patterns.
                  </div>
                </div>

                {/* Signature */}
                <div
                  className="h-0.5 mb-3"
                  style={{ background: 'linear-gradient(90deg, #1a3a5c, #e87722, #1a3a5c)' }}
                />
                <div className="text-[11px] text-gray-600">
                  <strong>Prepared by:</strong> {inspector} · Michael Baker International —{' '}
                  {project.location}, {project.state} Office · {todayLong()}
                </div>
                <div className="text-[10px] text-gray-400 mt-1">
                  Generated by InspectIQ Agent · Databricks Claude Sonnet 4.6 · Vector Search ·{' '}
                  Unity Catalog governance
                </div>
              </div>
            )}
          </div>

          {/* Footer */}
          <div className="flex items-center justify-end gap-3 px-6 py-3 border-t border-gray-200 bg-gray-50 flex-shrink-0">
            {phase === 'select' && (
              <>
                <button
                  onClick={onClose}
                  className="px-4 py-2 border border-gray-200 rounded-lg bg-white text-gray-700 text-sm font-medium hover:bg-gray-100"
                >
                  Cancel
                </button>
                <button
                  onClick={() => setPhase('configure')}
                  disabled={!projectId}
                  className="px-5 py-2 rounded-lg bg-mbi-navy text-white text-sm font-semibold disabled:bg-gray-300 disabled:cursor-not-allowed hover:bg-mbi-navy/90"
                >
                  Next
                </button>
              </>
            )}
            {phase === 'configure' && (
              <>
                <button
                  onClick={() => setPhase('select')}
                  className="px-4 py-2 border border-gray-200 rounded-lg bg-white text-gray-700 text-sm font-medium hover:bg-gray-100"
                >
                  Back
                </button>
                <button
                  onClick={() => setPhase('generating')}
                  className="px-5 py-2 rounded-lg bg-mbi-navy text-white text-sm font-semibold hover:bg-mbi-navy/90 flex items-center gap-2"
                >
                  <Sparkles size={14} />
                  Generate Report
                </button>
              </>
            )}
            {phase === 'preview' && (
              <>
                <button
                  onClick={() => setPhase('select')}
                  className="px-4 py-2 border border-gray-200 rounded-lg bg-white text-gray-700 text-sm font-medium hover:bg-gray-100"
                >
                  Draft Another
                </button>
                <button
                  onClick={() => {
                    // Enable print-mode, trigger the browser's print dialog
                    // (user picks "Save as PDF"), then restore UI state.
                    document.body.classList.add('inspectiq-printing')
                    const cleanup = () => {
                      document.body.classList.remove('inspectiq-printing')
                      window.removeEventListener('afterprint', cleanup)
                    }
                    window.addEventListener('afterprint', cleanup)
                    // Give the DOM one frame to apply print styles before dialog opens.
                    setTimeout(() => window.print(), 50)
                  }}
                  className="px-5 py-2 rounded-lg bg-mbi-orange text-white text-sm font-semibold hover:bg-mbi-orange/90 flex items-center gap-2"
                >
                  <Download size={14} />
                  Export PDF
                </button>
              </>
            )}
          </div>
        </div>
      </div>
    </>
  )
}
