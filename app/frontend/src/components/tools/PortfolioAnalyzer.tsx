import { useState } from 'react'
import { X, Database, Play, Sparkles } from 'lucide-react'
import Markdown from '../Markdown'

interface Preset {
  label: string
  question: string
  tag: string
}

const PRESETS: Preset[] = [
  {
    label: 'Condition breakdown by discipline',
    question: 'How many projects are in each condition category broken down by inspection type?',
    tag: 'Health',
  },
  {
    label: 'Total repair cost by type',
    question: 'What is the total estimated repair cost by inspection type in millions of dollars?',
    tag: 'Cost',
  },
  {
    label: 'Safety-flagged projects',
    question: 'List all safety-flagged projects with their report ID, state, priority, and estimated repair cost, sorted by priority score descending.',
    tag: 'Safety',
  },
  {
    label: 'Overdue inspections by state',
    question: 'How many inspections are overdue in each state, and what is the average days overdue?',
    tag: 'Backlog',
  },
  {
    label: 'Most expensive projects',
    question: 'Show the top 10 most expensive projects by estimated repair cost with their project name, inspection type, condition category, and cost.',
    tag: 'Cost',
  },
  {
    label: 'Critical condition assets',
    question: 'Which assets have a condition rating of 4 or below? Include project name, state, inspector, and key findings.',
    tag: 'Health',
  },
]

export default function PortfolioAnalyzer({ onClose }: { onClose: () => void }) {
  const [answer, setAnswer] = useState('')
  const [loading, setLoading] = useState(false)
  const [activeQuestion, setActiveQuestion] = useState('')
  const [sqlQuery, setSqlQuery] = useState('')

  const runQuery = async (question: string) => {
    if (loading) return
    setActiveQuestion(question)
    setLoading(true)
    setAnswer('')
    setSqlQuery('')

    try {
      const res = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          messages: [{ role: 'user', content: question }],
          stream: true,
        }),
      })
      if (!res.ok) throw new Error(`HTTP ${res.status}`)

      const reader = res.body!.getReader()
      const decoder = new TextDecoder()
      let acc = ''

      while (true) {
        const { done, value } = await reader.read()
        if (done) break
        const chunk = decoder.decode(value, { stream: true })
        for (const line of chunk.split('\n')) {
          if (!line.startsWith('data: ')) continue
          const data = line.slice(6)
          if (data === '[DONE]') break
          try {
            const parsed = JSON.parse(data)
            if (parsed.content) {
              acc += parsed.content
              setAnswer(acc)
              // Extract SQL when we see it
              const sqlMatch = acc.match(/```sql\n([\s\S]+?)\n```/)
              if (sqlMatch) setSqlQuery(sqlMatch[1])
            }
          } catch { /* ignore */ }
        }
      }
    } catch (e) {
      setAnswer(`Error: ${(e as Error).message}`)
    } finally {
      setLoading(false)
    }
  }

  // Answer text with SQL block hidden (we render it separately)
  const answerBody = answer.replace(/```sql[\s\S]+?```/g, '').trim()

  return (
    <>
      <div onClick={onClose} className="fixed inset-0 bg-black/50 z-40" />
      <div className="fixed inset-0 flex items-center justify-center z-50 pointer-events-none">
        <div className="bg-white rounded-xl w-[920px] max-w-[95vw] max-h-[88vh] shadow-2xl pointer-events-auto flex flex-col overflow-hidden">
          {/* Header */}
          <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200 bg-mbi-navy text-white flex-shrink-0">
            <div className="flex items-center gap-3">
              <div className="w-9 h-9 rounded-md bg-mbi-orange/20 flex items-center justify-center">
                <Database size={18} />
              </div>
              <div>
                <div className="font-bold text-sm">Portfolio Analyzer</div>
                <div className="text-xs text-blue-200 flex items-center gap-1.5">
                  <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" />
                  Connected to SQL tool · Queries project_assets
                </div>
              </div>
            </div>
            <button onClick={onClose} className="w-7 h-7 rounded hover:bg-white/10 flex items-center justify-center">
              <X size={16} />
            </button>
          </div>

          {/* Body */}
          <div className="flex-1 overflow-y-auto px-6 py-5">
            {/* Presets */}
            <div className="mb-5">
              <div className="text-[10px] font-bold text-gray-400 uppercase tracking-wider mb-2">
                Select an analysis
              </div>
              <div className="grid grid-cols-2 gap-2">
                {PRESETS.map(p => (
                  <button
                    key={p.label}
                    onClick={() => runQuery(p.question)}
                    disabled={loading}
                    className={`text-left px-4 py-3 rounded-lg border transition-all ${
                      activeQuestion === p.question
                        ? 'border-mbi-orange bg-orange-50'
                        : 'border-gray-200 bg-white hover:border-mbi-navy/30 hover:shadow-sm'
                    } disabled:opacity-50 disabled:cursor-not-allowed`}
                  >
                    <div className="flex items-start justify-between gap-2 mb-1">
                      <div className="text-sm font-semibold text-gray-900">{p.label}</div>
                      <span className="text-[9px] font-bold px-1.5 py-0.5 rounded bg-gray-100 text-gray-600 uppercase flex-shrink-0">
                        {p.tag}
                      </span>
                    </div>
                    <div className="text-xs text-gray-500 line-clamp-2">{p.question}</div>
                  </button>
                ))}
              </div>
            </div>

            {/* Loading */}
            {loading && !answer && (
              <div className="flex items-center gap-2 text-gray-500 text-sm py-6 border-t border-gray-100">
                <div className="w-4 h-4 border-2 border-mbi-orange border-t-transparent rounded-full animate-spin" />
                <span>Generating SQL and querying asset database...</span>
              </div>
            )}

            {/* SQL query display */}
            {sqlQuery && (
              <div className="mb-4 border-t border-gray-100 pt-4">
                <div className="flex items-center gap-2 mb-2">
                  <Play size={12} className="text-mbi-navy" />
                  <div className="text-[10px] font-bold text-gray-400 uppercase tracking-wider">
                    Generated SQL
                  </div>
                </div>
                <pre className="bg-slate-900 text-slate-100 text-xs rounded-lg px-4 py-3 overflow-x-auto font-mono">
                  {sqlQuery}
                </pre>
              </div>
            )}

            {/* Answer */}
            {answerBody && (
              <div className="border-t border-gray-100 pt-4">
                <div className="flex items-center gap-2 mb-3">
                  <Sparkles size={14} className="text-mbi-orange" />
                  <div className="text-[10px] font-bold text-gray-400 uppercase tracking-wider">
                    Result {loading && '(streaming...)'}
                  </div>
                </div>
                <div className="text-sm text-gray-800 leading-relaxed markdown-body">
                  <Markdown>{answerBody}</Markdown>
                </div>
              </div>
            )}
          </div>

          {/* Footer */}
          <div className="flex items-center justify-between px-6 py-3 border-t border-gray-200 bg-gray-50 flex-shrink-0">
            <div className="text-[11px] text-gray-500">
              Powered by Databricks SQL Warehouse + Claude Sonnet 4.6
            </div>
            <button
              onClick={onClose}
              className="px-4 py-1.5 border border-gray-200 rounded bg-white text-gray-700 text-sm font-medium hover:bg-gray-100"
            >
              Close
            </button>
          </div>
        </div>
      </div>
    </>
  )
}
