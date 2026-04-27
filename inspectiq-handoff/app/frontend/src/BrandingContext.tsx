import { createContext, useContext, useState, useEffect, ReactNode } from 'react'

// ---------------------------------------------------------------------------
// Branding / user config — persisted to localStorage so demo customizations
// survive a page refresh.
// ---------------------------------------------------------------------------

export interface BrandingConfig {
  companyName: string    // e.g. "Michael Baker International"
  appName: string        // e.g. "InspectIQ"
  tagline: string        // e.g. "Infrastructure Intelligence"
  userName: string       // e.g. "Sarah Chen"
  userRole: string       // e.g. "Senior Project Engineer"
}

const DEFAULTS: BrandingConfig = {
  companyName: 'Michael Baker International',
  appName:     'InspectIQ',
  tagline:     'Infrastructure Intelligence',
  userName:    'Michael Baker',
  userRole:    'Senior Project Engineer',
}

// v2 bump resets any stale cached user name from the previous default ("Sarah Chen")
const STORAGE_KEY = 'inspectiq.branding.v2'

function load(): BrandingConfig {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (!raw) return DEFAULTS
    return { ...DEFAULTS, ...JSON.parse(raw) }
  } catch {
    return DEFAULTS
  }
}

function save(cfg: BrandingConfig) {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(cfg))
  } catch {
    /* ignore quota / SSR errors */
  }
}

// ---------------------------------------------------------------------------

interface BrandingContextValue extends BrandingConfig {
  update: (patch: Partial<BrandingConfig>) => void
  reset: () => void
  initials: string
}

const Ctx = createContext<BrandingContextValue | null>(null)

export function BrandingProvider({ children }: { children: ReactNode }) {
  const [cfg, setCfg] = useState<BrandingConfig>(load)

  useEffect(() => { save(cfg) }, [cfg])

  const value: BrandingContextValue = {
    ...cfg,
    update: patch => setCfg(c => ({ ...c, ...patch })),
    reset:  ()    => setCfg(DEFAULTS),
    initials: cfg.userName
      .split(/\s+/)
      .filter(Boolean)
      .slice(0, 2)
      .map(w => w[0])
      .join('')
      .toUpperCase() || 'U',
  }

  return <Ctx.Provider value={value}>{children}</Ctx.Provider>
}

export function useBranding(): BrandingContextValue {
  const v = useContext(Ctx)
  if (!v) throw new Error('useBranding must be used inside <BrandingProvider>')
  return v
}
