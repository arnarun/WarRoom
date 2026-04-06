import { formatDistanceToNow } from 'date-fns'

const SEVERITY_STYLES = {
  critical: 'bg-red-900 text-red-300 border-red-700',
  high:     'bg-orange-900 text-orange-300 border-orange-700',
  medium:   'bg-yellow-900 text-yellow-300 border-yellow-700',
  low:      'bg-gray-800 text-gray-400 border-gray-600',
}

const SOURCE_ICONS = {
  cisa:           '🛡',
  'ncsc-uk':      '🛡',
  enisa:          '🛡',
  bsi:            '🛡',
  'cert-in':      '🛡',
  urlhaus:        '🔗',
  malwarebazaar:  '🦠',
  acled:          '⚔',
  alienvault:     '👁',
  nvd:            '🩹',
  'darkweb-news': '🌐',
  tor:            '🧅',
  haveibeenpwned: '🔓',
  'DataBreaches.net': '🔓',
}

const TYPE_BADGES = {
  breach:       'bg-blue-900 text-blue-300 border-blue-700',
  darkweb:      'bg-purple-900 text-purple-300 border-purple-700',
  'threat-intel': 'bg-orange-900 text-orange-300 border-orange-700',
  'threat-actor': 'bg-red-900 text-red-300 border-red-700',
  people:        'bg-teal-900 text-teal-300 border-teal-700',
  vulnerability: 'bg-rose-900 text-rose-300 border-rose-700',
}

const COUNTRY_FLAGS = {
  US:        '🇺🇸',
  UK:        '🇬🇧',
  India:     '🇮🇳',
  Sweden:    '🇸🇪',
  Germany:   '🇩🇪',
  Japan:     '🇯🇵',
  Singapore: '🇸🇬',
  Australia: '🇦🇺',
  China:     '🇨🇳',
  EU:        '🇪🇺',
}

function timeAgo(iso) {
  if (!iso) return ''
  try { return formatDistanceToNow(new Date(iso), { addSuffix: true }) } catch { return '' }
}

export default function SignalCard({ signal }) {
  const sev = SEVERITY_STYLES[signal.severity] || SEVERITY_STYLES.low
  const typeBadge = TYPE_BADGES[signal.type] || ''

  return (
    <a
      href={signal.url || '#'}
      target="_blank"
      rel="noopener noreferrer"
      className="block p-3 border border-gray-800 rounded bg-gray-900 hover:border-gray-600 transition-colors"
    >
      <div className="flex items-start gap-2 mb-1 flex-wrap">
        <span className="text-sm">{SOURCE_ICONS[signal.source] || '⚠'}</span>
        <span className={`text-[10px] font-bold uppercase border rounded px-1.5 py-0.5 ${sev}`}>
          {signal.severity || 'info'}
        </span>
        {typeBadge ? (
          <span className={`text-[10px] font-semibold uppercase border rounded px-1.5 py-0.5 ${typeBadge}`}>
            {signal.type}
          </span>
        ) : (
          <span className="text-[10px] text-gray-500 uppercase">{signal.type}</span>
        )}
        {signal.country && (
          <span className="text-[10px] text-gray-500">
            {COUNTRY_FLAGS[signal.country] || ''} {signal.country}
          </span>
        )}
        <span className="ml-auto text-[10px] text-gray-600">{timeAgo(signal.published_at)}</span>
      </div>
      <p className="text-xs text-gray-200 leading-snug line-clamp-3">{signal.title}</p>
      {signal.description && (
        <p className="mt-1 text-[10px] text-gray-500 line-clamp-2">{signal.description}</p>
      )}
      <p className="mt-1 text-[10px] text-gray-600 uppercase">{signal.source}</p>
    </a>
  )
}
