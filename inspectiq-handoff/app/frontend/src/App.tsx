import { useState, useEffect, useRef } from 'react'
import ChatView from './components/ChatView'
import AssetsView from './components/AssetsView'
import DashboardView from './components/DashboardView'
import EmbeddedDashboardView from './components/EmbeddedDashboardView'
import AgentToolsView from './components/AgentToolsView'
import SettingsModal from './components/SettingsModal'
import { useBranding } from './BrandingContext'
import {
  MessageSquare, LayoutDashboard, Database, Wrench,
  ChevronDown, Settings, LogOut, User, BarChart3,
} from 'lucide-react'

type Tab = 'chat' | 'assets' | 'overview' | 'exec-dashboard' | 'agents'

// ---------------------------------------------------------------------------
// User badge + dropdown — top-right of header
// ---------------------------------------------------------------------------

function UserBadge({ onOpenSettings }: { onOpenSettings: () => void }) {
  const { userName, userRole, initials } = useBranding()
  const [open, setOpen] = useState(false)
  const ref = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!open) return
    const handler = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false)
    }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [open])

  return (
    <div ref={ref} className="relative">
      <button
        onClick={() => setOpen(v => !v)}
        className="flex items-center gap-2 px-2 py-1.5 rounded-lg hover:bg-white/10 transition-colors"
      >
        <div className="w-8 h-8 rounded-full bg-mbi-orange flex items-center justify-center text-white font-bold text-xs ring-2 ring-white/20">
          {initials}
        </div>
        <div className="text-left hidden md:block">
          <div className="text-xs font-semibold leading-tight text-white">{userName}</div>
          <div className="text-[10px] text-blue-200 leading-tight">{userRole}</div>
        </div>
        <ChevronDown size={14} className="text-blue-200" />
      </button>

      {open && (
        <div className="absolute right-0 top-full mt-2 w-64 bg-white rounded-lg shadow-xl border border-gray-200 overflow-hidden z-[60]">
          {/* User info */}
          <div className="px-4 py-3 bg-gray-50 border-b border-gray-100">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-full bg-mbi-orange flex items-center justify-center text-white font-bold">
                {initials}
              </div>
              <div className="min-w-0 flex-1">
                <div className="text-sm font-semibold text-gray-900 truncate">{userName}</div>
                <div className="text-xs text-gray-500 truncate">{userRole}</div>
              </div>
            </div>
            <div className="mt-2 flex items-center gap-1.5 text-[11px] text-emerald-700">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
              <span>Active session · Authenticated</span>
            </div>
          </div>

          {/* Menu */}
          <div className="py-1.5">
            <button
              onClick={() => { setOpen(false); onOpenSettings() }}
              className="w-full flex items-center gap-2.5 px-4 py-2 text-sm text-gray-700 hover:bg-gray-50"
            >
              <Settings size={14} className="text-gray-400" />
              Demo Settings
            </button>
            <button
              disabled
              className="w-full flex items-center gap-2.5 px-4 py-2 text-sm text-gray-400 cursor-not-allowed"
            >
              <User size={14} className="text-gray-300" />
              Profile
            </button>
            <div className="border-t border-gray-100 my-1" />
            <button
              disabled
              className="w-full flex items-center gap-2.5 px-4 py-2 text-sm text-gray-400 cursor-not-allowed"
            >
              <LogOut size={14} className="text-gray-300" />
              Sign out
            </button>
          </div>
        </div>
      )}
    </div>
  )
}

// ---------------------------------------------------------------------------
// Main App
// ---------------------------------------------------------------------------

export default function App() {
  const [tab, setTab] = useState<Tab>('overview')
  const [settingsOpen, setSettingsOpen] = useState(false)
  const { companyName, appName, tagline } = useBranding()

  // Keep the document title in sync with app name
  useEffect(() => {
    document.title = `${appName} · ${companyName}`
  }, [appName, companyName])

  return (
    <div className="min-h-screen flex flex-col">
      {/* Header */}
      <header className="bg-mbi-navy text-white shadow-md">
        <div className="max-w-7xl mx-auto px-4 py-3 flex items-center justify-between gap-4">
          <div className="flex items-center gap-3 min-w-0">
            <div className="bg-mbi-orange rounded-lg p-1.5 flex-shrink-0">
              <span className="text-xl">🏗</span>
            </div>
            <div className="min-w-0">
              <h1 className="text-lg font-bold leading-tight truncate">{appName}</h1>
              <p className="text-xs text-blue-200 truncate">{companyName} · {tagline}</p>
            </div>
          </div>

          <div className="flex items-center gap-3 flex-shrink-0">
            <div className="text-xs text-blue-200 hidden lg:block">
              Powered by Databricks
            </div>
            <UserBadge onOpenSettings={() => setSettingsOpen(true)} />
          </div>
        </div>

        {/* Tab bar */}
        <nav className="max-w-7xl mx-auto px-4">
          <div className="flex gap-1">
            {([
              { key: 'overview',       label: 'Overview',            icon: LayoutDashboard },
              { key: 'exec-dashboard', label: 'Executive Dashboard', icon: BarChart3 },
              { key: 'assets',         label: 'Asset Intelligence',  icon: Database },
              { key: 'chat',           label: 'AI Assistant',        icon: MessageSquare },
              { key: 'agents',         label: 'Agent Tools',         icon: Wrench },
            ] as { key: Tab; label: string; icon: React.ElementType }[]).map(({ key, label, icon: Icon }) => (
              <button
                key={key}
                onClick={() => setTab(key)}
                className={`flex items-center gap-2 px-4 py-2.5 text-sm font-medium border-b-2 transition-colors ${
                  tab === key
                    ? 'border-mbi-orange text-white'
                    : 'border-transparent text-blue-200 hover:text-white hover:border-blue-300'
                }`}
              >
                <Icon size={15} />
                {label}
              </button>
            ))}
          </div>
        </nav>
      </header>

      {/* Main */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 py-4">
        {tab === 'chat'           && <ChatView />}
        {tab === 'assets'         && <AssetsView />}
        {tab === 'overview'       && <DashboardView />}
        {tab === 'exec-dashboard' && <EmbeddedDashboardView />}
        {tab === 'agents'         && <AgentToolsView />}
      </main>

      {/* Settings modal */}
      <SettingsModal open={settingsOpen} onClose={() => setSettingsOpen(false)} />
    </div>
  )
}
