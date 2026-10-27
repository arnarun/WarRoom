import { formatDistanceToNow } from 'date-fns'

function ago(iso) {
  if (!iso) return '—'
  try { return formatDistanceToNow(new Date(iso), { addSuffix: true }) } catch { return '—' }
}

function every(s) {
  return s >= 3600 ? `${s / 3600}h` : s >= 60 ? `${s / 60}m` : `${s}s`
}

const DOT = {
  ok:       'bg-brand',
  degraded: 'bg-yellow-400',
  down:     'bg-red-500',
  unknown:  'bg-gray-600',
}

export function HealthDot({ health }) {
  return <span className={`inline-block w-2 h-2 rounded-full ${DOT[health] || DOT.unknown}`} />
}

function jobState(j) {
  if (j.running) return { label: 'running', cls: 'text-cyan-400' }
  if (!j.runs) return { label: 'pending', cls: 'text-gray-500' }
  if (j.last_error) return { label: `failed (${j.last_error})`, cls: 'text-red-400' }
  return { label: 'ok', cls: 'text-brand' }
}

export default function StatusView({ status, error, health }) {
  if (error) {
    return <p className="p-6 text-sm text-red-400">Backend unreachable: {error}</p>
  }
  if (!status) {
    return <p className="p-6 text-sm text-gray-600">Loading status…</p>
  }

  const rss = status.rss || {}

  return (
    <div className="h-full overflow-y-auto p-4 space-y-6 max-w-5xl">
      <div className="flex items-center gap-2 text-xs text-gray-400">
        <HealthDot health={health} />
        <span className="uppercase tracking-wider">System {health}</span>
        <span className="text-gray-600 ml-2">API v{status.version}</span>
      </div>

      <section>
        <h2 className="text-xs font-bold uppercase text-brand mb-2 tracking-wider">Data</h2>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
          {Object.entries(status.tables || {}).map(([name, t]) => (
            <div key={name} className="border border-gray-800 rounded bg-gray-900 p-3">
              <p className="text-[10px] uppercase text-gray-500">{name.replace('_', ' ')}</p>
              <p className="text-lg text-gray-100 tabular-nums">{t.rows.toLocaleString()}</p>
              <p className="text-[10px] text-gray-600">latest {ago(t.latest)}</p>
            </div>
          ))}
        </div>
      </section>

      <section>
        <h2 className="text-xs font-bold uppercase text-brand mb-2 tracking-wider">Fetchers</h2>
        <div className="border border-gray-800 rounded overflow-x-auto">
          <table className="w-full text-xs">
            <thead className="bg-gray-900 text-gray-500 text-[10px] uppercase">
              <tr>
                <th className="text-left px-3 py-2">Job</th>
                <th className="text-left px-3 py-2">State</th>
                <th className="text-right px-3 py-2">Every</th>
                <th className="text-right px-3 py-2">Last success</th>
                <th className="text-right px-3 py-2">Took</th>
                <th className="text-right px-3 py-2">New rows</th>
                <th className="text-right px-3 py-2">Runs / fails</th>
              </tr>
            </thead>
            <tbody>
              {(status.jobs || []).map(j => {
                const st = jobState(j)
                return (
                  <tr key={j.name} className="border-t border-gray-800">
                    <td className="px-3 py-1.5 text-gray-300">{j.name.replace(/^fetch_/, '')}</td>
                    <td className={`px-3 py-1.5 ${st.cls}`}>{st.label}</td>
                    <td className="px-3 py-1.5 text-right text-gray-500">{every(j.interval_s)}</td>
                    <td className="px-3 py-1.5 text-right text-gray-400">{ago(j.last_success)}</td>
                    <td className="px-3 py-1.5 text-right text-gray-500 tabular-nums">
                      {j.last_duration != null ? `${j.last_duration}s` : '—'}
                    </td>
                    <td className="px-3 py-1.5 text-right text-gray-400 tabular-nums">{j.last_result ?? '—'}</td>
                    <td className="px-3 py-1.5 text-right text-gray-500 tabular-nums">
                      {j.runs} / <span className={j.failures ? 'text-red-400' : ''}>{j.failures}</span>
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      </section>

      {rss.total != null && (
        <section>
          <h2 className="text-xs font-bold uppercase text-brand mb-2 tracking-wider">
            RSS feeds — last sweep {ago(rss.at)}
          </h2>
          <p className="text-xs text-gray-400 mb-2">
            {rss.ok} ok · {rss.empty} empty · {rss.fail} failing of {rss.total} sources
          </p>
          {[['Failing', rss.failing, 'text-red-400'], ['Empty', rss.empty_sources, 'text-yellow-400']].map(
            ([label, list, cls]) => list?.length > 0 && (
              <div key={label} className="mb-2">
                <p className={`text-[10px] uppercase mb-1 ${cls}`}>{label}</p>
                <div className="flex flex-wrap gap-1">
                  {list.map(n => (
                    <span key={n} className="text-[11px] bg-gray-900 border border-gray-800 rounded px-2 py-0.5 text-gray-300">{n}</span>
                  ))}
                </div>
              </div>
            )
          )}
        </section>
      )}
    </div>
  )
}
