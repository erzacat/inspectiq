import { useState, useRef, useEffect } from 'react'
import { Send, Bot, User, RefreshCw, Lightbulb } from 'lucide-react'
import Markdown from './Markdown'
import { useBranding } from '../BrandingContext'

interface Message {
  role: 'user' | 'assistant'
  content: string
  streaming?: boolean
}

const SAMPLE_QUESTIONS = [
  "What structural issues were identified in the parking garage inspection?",
  "Were any immediate safety risks identified across our inspections?",
  "What corrective actions were recommended for concrete deterioration?",
  "Which assets are showing signs of freeze-thaw damage?",
  "Summarize the key findings from the asphalt pavement assessments.",
  "What repair methods were recommended for exposed rebar?",
]

export default function ChatView() {
  const { appName, companyName } = useBranding()
  const [messages, setMessages] = useState<Message[]>([
    {
      role: 'assistant',
      content:
        `Hello! I'm the **${appName} AI Assistant**. I route your questions across ${companyName}'s inspection reports (RAG) and asset database (SQL) — covering structural steel, concrete, and asphalt/pavement disciplines.\n\nAsk me about specific findings, deficiencies, repair recommendations, safety risks, or portfolio metrics.`,
    },
  ])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const bottomRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLTextAreaElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const sendMessage = async (text?: string) => {
    const query = (text ?? input).trim()
    if (!query || loading) return

    setInput('')
    const userMsg: Message = { role: 'user', content: query }
    const history = [...messages, userMsg]
    setMessages(history)
    setLoading(true)

    const assistantIdx = history.length
    setMessages(prev => [...prev, { role: 'assistant', content: '', streaming: true }])

    try {
      const payload = {
        messages: history.map(m => ({ role: m.role, content: m.content })),
        stream: true,
      }
      const res = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      })

      if (!res.ok) throw new Error(`HTTP ${res.status}`)

      const reader = res.body!.getReader()
      const decoder = new TextDecoder()
      let accumulated = ''

      while (true) {
        const { done, value } = await reader.read()
        if (done) break
        const chunk = decoder.decode(value, { stream: true })
        const lines = chunk.split('\n').filter(l => l.startsWith('data: '))
        for (const line of lines) {
          const data = line.slice(6)
          if (data === '[DONE]') break
          try {
            const parsed = JSON.parse(data)
            if (parsed.error) {
              accumulated = `Error: ${parsed.error}`
            } else if (parsed.content) {
              accumulated += parsed.content
            }
            setMessages(prev => {
              const updated = [...prev]
              updated[assistantIdx] = { role: 'assistant', content: accumulated, streaming: true }
              return updated
            })
          } catch {}
        }
      }

      setMessages(prev => {
        const updated = [...prev]
        updated[assistantIdx] = { role: 'assistant', content: accumulated, streaming: false }
        return updated
      })
    } catch (e) {
      setMessages(prev => {
        const updated = [...prev]
        updated[assistantIdx] = {
          role: 'assistant',
          content: `Sorry, I encountered an error. Please try again. (${e})`,
          streaming: false,
        }
        return updated
      })
    } finally {
      setLoading(false)
      inputRef.current?.focus()
    }
  }

  return (
    <div className="flex flex-col h-[calc(100vh-140px)]">
      {/* Sample questions */}
      {messages.length <= 1 && (
        <div className="mb-4">
          <div className="flex items-center gap-2 text-xs text-mbi-steel mb-2">
            <Lightbulb size={13} /> Sample questions
          </div>
          <div className="flex flex-wrap gap-2">
            {SAMPLE_QUESTIONS.map((q, i) => (
              <button
                key={i}
                onClick={() => sendMessage(q)}
                className="text-xs bg-white border border-gray-200 text-mbi-navy px-3 py-1.5 rounded-full hover:border-mbi-navy hover:bg-mbi-light transition-colors text-left"
              >
                {q}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Message list */}
      <div className="flex-1 overflow-y-auto space-y-4 pb-2">
        {messages.map((msg, i) => (
          <div
            key={i}
            className={`flex gap-3 ${msg.role === 'user' ? 'flex-row-reverse' : 'flex-row'}`}
          >
            <div
              className={`flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center ${
                msg.role === 'user'
                  ? 'bg-mbi-navy text-white'
                  : 'bg-mbi-orange text-white'
              }`}
            >
              {msg.role === 'user' ? <User size={15} /> : <Bot size={15} />}
            </div>
            <div
              className={`max-w-[80%] rounded-2xl px-4 py-3 text-sm leading-relaxed ${
                msg.role === 'user'
                  ? 'bg-mbi-navy text-white rounded-tr-sm'
                  : 'bg-white border border-gray-200 text-gray-800 rounded-tl-sm shadow-sm markdown-body'
              } ${msg.streaming ? 'cursor-blink' : ''}`}
            >
              {msg.role === 'user' ? (
                <div className="whitespace-pre-wrap">{msg.content || '\u00A0'}</div>
              ) : (
                <Markdown>{msg.content || '\u00A0'}</Markdown>
              )}
            </div>
          </div>
        ))}
        <div ref={bottomRef} />
      </div>

      {/* Input */}
      <div className="mt-3 flex gap-2 items-end">
        <textarea
          ref={inputRef}
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyDown={e => {
            if (e.key === 'Enter' && !e.shiftKey) {
              e.preventDefault()
              sendMessage()
            }
          }}
          placeholder="Ask about inspection findings, maintenance procedures, load ratings..."
          rows={2}
          className="flex-1 resize-none border border-gray-300 rounded-xl px-4 py-2.5 text-sm focus:outline-none focus:border-mbi-navy focus:ring-1 focus:ring-mbi-navy"
          disabled={loading}
        />
        <button
          onClick={() => sendMessage()}
          disabled={loading || !input.trim()}
          className="btn-orange h-10 w-10 flex items-center justify-center rounded-xl disabled:opacity-40"
        >
          {loading ? <RefreshCw size={16} className="animate-spin" /> : <Send size={16} />}
        </button>
      </div>
      <p className="text-xs text-gray-400 mt-1 text-center">
        Searches across structural steel, concrete &amp; asphalt inspection reports · Answers cite source documents
      </p>
    </div>
  )
}
