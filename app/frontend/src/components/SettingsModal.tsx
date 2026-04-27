import { useEffect, useState } from 'react'
import { X, Settings as SettingsIcon, RotateCcw } from 'lucide-react'
import { useBranding, BrandingConfig } from '../BrandingContext'

interface Props {
  open: boolean
  onClose: () => void
}

const FIELDS: { key: keyof BrandingConfig; label: string; hint: string }[] = [
  { key: 'companyName', label: 'Company Name',  hint: 'Shown as the primary brand (top-left header + footers)' },
  { key: 'appName',     label: 'App Name',      hint: 'The application name displayed prominently in the header' },
  { key: 'tagline',     label: 'Tagline',       hint: 'Secondary text shown next to the app name' },
  { key: 'userName',    label: 'User Name',     hint: 'Name displayed in the top-right user badge' },
  { key: 'userRole',    label: 'User Role',     hint: 'Role/title displayed under the user name' },
]

export default function SettingsModal({ open, onClose }: Props) {
  const branding = useBranding()

  const [form, setForm] = useState<BrandingConfig>({
    companyName: branding.companyName,
    appName:     branding.appName,
    tagline:     branding.tagline,
    userName:    branding.userName,
    userRole:    branding.userRole,
  })

  useEffect(() => {
    if (open) {
      setForm({
        companyName: branding.companyName,
        appName:     branding.appName,
        tagline:     branding.tagline,
        userName:    branding.userName,
        userRole:    branding.userRole,
      })
    }
  }, [open, branding])

  useEffect(() => {
    if (!open) return
    const onKey = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose() }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [open, onClose])

  if (!open) return null

  const handleSave = () => { branding.update(form); onClose() }
  const handleReset = () => { branding.reset(); onClose() }

  return (
    <>
      <div onClick={onClose} className="fixed inset-0 bg-black/50 z-40" />
      <div className="fixed inset-0 flex items-center justify-center z-50 pointer-events-none">
        <div className="bg-white rounded-xl w-[560px] max-w-[92vw] max-h-[90vh] shadow-2xl pointer-events-auto flex flex-col overflow-hidden">
          {/* Header */}
          <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200 bg-mbi-navy text-white">
            <div className="flex items-center gap-3">
              <div className="w-9 h-9 rounded-md bg-mbi-orange/20 flex items-center justify-center">
                <SettingsIcon size={18} />
              </div>
              <div>
                <div className="font-bold text-sm">Demo Settings</div>
                <div className="text-xs text-blue-200">Customize branding for your demo session</div>
              </div>
            </div>
            <button onClick={onClose} className="w-7 h-7 rounded hover:bg-white/10 flex items-center justify-center">
              <X size={16} />
            </button>
          </div>

          {/* Body */}
          <div className="flex-1 overflow-y-auto px-6 py-5 space-y-4">
            <div className="bg-orange-50 border border-orange-200 rounded-lg px-4 py-3 text-xs text-orange-900 leading-relaxed">
              Changes are saved to your browser (localStorage) — they survive refreshes and affect only your
              local view. This is for demo customization, not a multi-user setting.
            </div>

            {FIELDS.map(f => (
              <div key={f.key}>
                <label className="block text-[10px] font-bold text-gray-500 uppercase tracking-wider mb-1">
                  {f.label}
                </label>
                <input
                  type="text"
                  value={form[f.key]}
                  onChange={e => setForm({ ...form, [f.key]: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-mbi-orange"
                />
                <div className="text-[11px] text-gray-400 mt-0.5">{f.hint}</div>
              </div>
            ))}

            {/* Quick presets */}
            <div className="pt-3 border-t border-gray-100">
              <div className="text-[10px] font-bold text-gray-500 uppercase tracking-wider mb-2">
                Quick presets
              </div>
              <div className="flex flex-wrap gap-2">
                {[
                  { label: 'Michael Baker International', cfg: { companyName: 'Michael Baker International', appName: 'InspectIQ', tagline: 'Infrastructure Intelligence' } },
                  { label: 'AECOM',                       cfg: { companyName: 'AECOM', appName: 'AssetIQ', tagline: 'Infrastructure Intelligence' } },
                  { label: 'Kiewit',                      cfg: { companyName: 'Kiewit Corporation', appName: 'SiteIQ', tagline: 'Project Intelligence' } },
                  { label: 'Jacobs',                      cfg: { companyName: 'Jacobs Engineering', appName: 'InsightIQ', tagline: 'Engineering Intelligence' } },
                  { label: 'HDR',                         cfg: { companyName: 'HDR', appName: 'InspectIQ', tagline: 'Engineering Intelligence' } },
                  { label: 'WSP',                         cfg: { companyName: 'WSP', appName: 'AssetIQ', tagline: 'Infrastructure Intelligence' } },
                ].map(p => (
                  <button
                    key={p.label}
                    onClick={() => setForm(f => ({ ...f, ...p.cfg }))}
                    className="text-xs px-3 py-1.5 bg-gray-50 hover:bg-mbi-light border border-gray-200 rounded-full text-gray-700 hover:border-mbi-navy/30"
                  >
                    {p.label}
                  </button>
                ))}
              </div>
            </div>
          </div>

          {/* Footer */}
          <div className="flex items-center justify-between px-6 py-3 border-t border-gray-200 bg-gray-50 flex-shrink-0">
            <button
              onClick={handleReset}
              className="text-xs text-gray-500 hover:text-gray-700 flex items-center gap-1.5"
            >
              <RotateCcw size={12} />
              Reset to default
            </button>
            <div className="flex gap-2">
              <button onClick={onClose} className="px-4 py-1.5 border border-gray-200 rounded bg-white text-gray-700 text-sm font-medium hover:bg-gray-100">
                Cancel
              </button>
              <button onClick={handleSave} className="px-5 py-1.5 rounded bg-mbi-navy text-white text-sm font-semibold hover:bg-mbi-navy/90">
                Save
              </button>
            </div>
          </div>
        </div>
      </div>
    </>
  )
}
