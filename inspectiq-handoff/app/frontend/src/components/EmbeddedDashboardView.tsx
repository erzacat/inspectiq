import { useEffect, useState } from 'react'
import { ExternalLink, AlertTriangle } from 'lucide-react'

const DASHBOARD_ID = '01f13232608316f4b4411a791afe86c4'
const WORKSPACE_HOST = 'https://e2-demo-field-eng.cloud.databricks.com'
const WORKSPACE_ORG  = '1444828305810485'

const EMBED_URL = `${WORKSPACE_HOST}/embed/dashboardsv3/${DASHBOARD_ID}?o=${WORKSPACE_ORG}`
const OPEN_URL  = `${WORKSPACE_HOST}/dashboardsv3/${DASHBOARD_ID}/published?o=${WORKSPACE_ORG}`

export default function EmbeddedDashboardView() {
  const [loaded, setLoaded] = useState(false)
  const [failed, setFailed] = useState(false)

  useEffect(() => {
    const timer = setTimeout(() => {
      if (!loaded) setFailed(true)
    }, 20000)
    return () => clearTimeout(timer)
  }, [loaded])

  return (
    <div className="space-y-3">
      <div className="flex items-start justify-between gap-3">
        <div className="text-xs text-gray-500">
          Shareable Databricks AI/BI dashboard · filters, region heatmap, compliance, trend, and AI narrative.
          Use the <span className="font-mono">Filters</span> page inside the dashboard to scope all widgets.
        </div>
        <a
          href={OPEN_URL}
          target="_blank"
          rel="noreferrer"
          className="shrink-0 inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded border border-gray-200 bg-white hover:bg-gray-50 text-mbi-navy"
        >
          Open in Databricks <ExternalLink size={12} />
        </a>
      </div>

      <div className="relative w-full border border-gray-200 rounded-lg overflow-hidden bg-white" style={{ height: 'calc(100vh - 200px)', minHeight: '700px' }}>
        {!loaded && !failed && (
          <div className="absolute inset-0 flex items-center justify-center bg-white z-10">
            <div className="flex flex-col items-center gap-3">
              <div className="w-8 h-8 border-4 border-mbi-navy border-t-transparent rounded-full animate-spin" />
              <p className="text-sm text-gray-400">Loading Databricks dashboard...</p>
            </div>
          </div>
        )}
        {failed && (
          <div className="absolute inset-0 flex items-center justify-center bg-white z-10 p-8">
            <div className="max-w-md text-center">
              <AlertTriangle size={32} className="mx-auto mb-3 text-orange-500" />
              <p className="font-semibold text-gray-800 mb-1">Dashboard took too long to load</p>
              <p className="text-sm text-gray-500 mb-4">
                The embed may require you to be signed in to the Databricks workspace, or your network is blocking the iframe.
              </p>
              <a
                href={OPEN_URL}
                target="_blank"
                rel="noreferrer"
                className="inline-flex items-center gap-1.5 px-4 py-2 text-sm font-medium rounded bg-mbi-navy text-white hover:bg-mbi-navy/90"
              >
                Open in a new tab <ExternalLink size={14} />
              </a>
            </div>
          </div>
        )}
        <iframe
          src={EMBED_URL}
          title="InspectIQ Executive Dashboard"
          className="w-full h-full border-0"
          onLoad={() => setLoaded(true)}
        />
      </div>
    </div>
  )
}
