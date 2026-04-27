import { useState, useRef, useEffect } from 'react'
import { X, Search, Send, Sparkles } from 'lucide-react'
import Markdown from '../Markdown'

const PRESET_QUESTIONS = [
  'Were any immediate safety risks identified in the parking garage inspections?',
  'What causes concrete deterioration and what repairs were recommended?',
  'Which asphalt projects have alligator cracking?',
  'What structural issues were identified in the highway overpass?',
]

export default function InspectionReportFinder({ onClose }: { onClose: () => void }) {
  const [query, setQuery] = useState('')
  const [answer, setAnswer] = useState('')
  const [loading, setLoading] = useState(false)
  const [sources, setSources] = useState<string[]>([])
  const inputRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    inputRef.current?.focus()
  }, [])

  const runQuery = async (text: string) => {
    if (!text.trim() || loading) return
    setLoading(true)
    setAnswer('')
    setSources([])

    try {
      const res = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          messages: [{ role: 'user', content: text }],
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
            }
          } catch { /* ignore */ }
        }
      }

      // Extract cited report IDs (INS-XX-###)
      const matches = acc.match(/INS-[A-Z]{2}-\d{3}/g) || []
      setSources([...new Set(matches)])
    } catch (e) {
      setAnswer(`Error: ${(e as Error).message}`)
    } finally {
      setLoading(false)
    }
  }

  return (
    <>
      <div onClick={onClose} className="fixed inset-0 bg-black/50 z-40" />
      <div className="fixed inset-0 flex items-center justify-center z-50 pointer-events-none">
        <div className="bg-white rounded-xl w-[780px] max-w-[92vw] max-h-[88vh] shadow-2xl pointer-events-auto flex flex-col overflow-hidden">
          {/* Header */}
          <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200 bg-mbi-navy text-white flex-shrink-0">
            <div className="flex items-center gap-3">
              <div className="w-9 h-9 rounded-md bg-mbi-orange/20 flex items-center justify-center">
                <Search size={18} />
              </div>
              <div>
                <div className="font-bold text-sm">Inspection Report Finder</div>
                <div className="text-xs text-blue-200 flex items-center gap-1.5">
                  <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" />
                  Connected to RAG endpoint · Vector Search on 10 PDFs
                </div>
              </div>
            </div>
            <button onClick={onClose} className="w-7 h-7 rounded hover:bg-white/10 flex items-center justify-center">
              <X size={16} />
            </button>
          </div>

          {/* Body */}
          <div className="flex-1 overflow-y-auto px-6 py-5">
            {/* Query input */}
            <div className="mb-4">
              <div className="text-[10px] font-bold text-gray-400 uppercase tracking-wider mb-2">
                Ask a question
              </div>
              <div className="flex gap-2">
                <input
                  ref={inputRef}
                  value={query}
                  onChange={e => setQuery(e.target.value)}
                  onKeyDown={e => { if (e.key === 'Enter') runQuery(query) }}
                  placeholder="e.g., Were any immediate safety risks identified?"
                  className="flex-1 px-3 py-2.5 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-mbi-orange"
                  disabled={loading}
                />
                <button
                  onClick={() => runQuery(query)}
                  disabled={!query.trim() || loading}
                  className="px-4 py-2.5 bg-mbi-navy text-white rounded-lg font-semibold text-sm disabled:bg-gray-300 disabled:cursor-not-allowed hover:bg-mbi-navy/90 flex items-center gap-1.5"
                >
                  <Send size={14} />
                  {loading ? 'Searching...' : 'Search'}
                </button>
              </div>
            </div>

            {/* Preset questions */}
            {!answer && !loading && (
              <div className="mb-4">
                <div className="text-[10px] font-bold text-gray-400 uppercase tracking-wider mb-2">
                  Try one of these
                </div>
                <div className="flex flex-wrap gap-2">
                  {PRESET_QUESTIONS.map(q => (
                    <button
                      key={q}
                      onClick={() => { setQuery(q); runQuery(q) }}
                      className="text-xs px-3 py-1.5 bg-gray-50 hover:bg-gray-100 border border-gray-200 rounded-full text-gray-700"
                    >
                      {q}
                    </button>
                  ))}
                </div>
              </div>
            )}

            {/* Loading indicator */}
            {loading && !answer && (
              <div className="flex items-center gap-2 text-gray-500 text-sm py-6 border-t border-gray-100">
                <div className="w-4 h-4 border-2 border-mbi-orange border-t-transparent rounded-full animate-spin" />
                <span>Retrieving relevant inspection reports...</span>
              </div>
            )}

            {/* Answer */}
            {answer && (
              <div className="border-t border-gray-100 pt-4">
                <div className="flex items-center gap-2 mb-3">
                  <Sparkles size={14} className="text-mbi-orange" />
                  <div className="text-[10px] font-bold text-gray-400 uppercase tracking-wider">
                    Answer {loading && '(streaming...)'}
                  </div>
                </div>
                <div className="text-sm text-gray-800 leading-relaxed markdown-body">
                  <Markdown>{answer}</Markdown>
                </div>

                {sources.length > 0 && !loading && (
                  <div className="mt-5 pt-4 border-t border-gray-100">
                    <div className="text-[10px] font-bold text-gray-400 uppercase tracking-wider mb-2">
                      Cited reports ({sources.length})
                    </div>
                    <div className="flex flex-wrap gap-2">
                      {sources.map(src => (
                        <span key={src} className="text-xs font-mono px-2.5 py-1 bg-mbi-navy/5 text-mbi-navy rounded border border-mbi-navy/10">
                          {src}
                        </span>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>

          {/* Footer */}
          <div className="flex items-center justify-between px-6 py-3 border-t border-gray-200 bg-gray-50 flex-shrink-0">
            <div className="text-[11px] text-gray-500">
              Powered by Databricks Vector Search + Claude Sonnet 4.6
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
