import { useState, useEffect, useRef } from 'react'

const CATEGORIES = [
  { value: '',                label: 'All' },
  { value: 'politics',        label: 'Politics' },
  { value: 'geopolitics',     label: 'Geopolitics' },
  { value: 'defense',         label: '⚔️ Defense' },
  { value: 'business',        label: 'Business' },
  { value: 'technology',      label: 'Technology' },
  { value: 'security',        label: 'Security' },
  { value: 'health',          label: '🏥 Health' },
  { value: 'emergency',       label: '🚨 Emergency' },
  { value: 'startups',        label: 'Startups' },
  { value: 'venture-capital', label: 'VC' },
  { value: 'science',         label: 'Science' },
]

const REGIONS = [
  { value: '',             label: 'All Regions' },
  { value: 'global',       label: 'Global' },
  { value: 'us',           label: 'US' },
  { value: 'eu',           label: 'Europe' },
  { value: 'asia',         label: 'Asia' },
  { value: 'middle-east',  label: 'Middle East' },
]

const COUNTRIES = [
  { value: '',            label: 'All Countries' },
  { value: 'US',         label: '🇺🇸 US' },
  { value: 'UK',         label: '🇬🇧 UK' },
  { value: 'India',      label: '🇮🇳 India' },
  { value: 'Sweden',     label: '🇸🇪 Sweden' },
  { value: 'Germany',    label: '🇩🇪 Germany' },
  { value: 'Japan',      label: '🇯🇵 Japan' },
  { value: 'Singapore',  label: '🇸🇬 Singapore' },
  { value: 'Australia',  label: '🇦🇺 Australia' },
  { value: 'China',      label: '🇨🇳 China' },
]

export default function FilterBar({ filters, onChange, newCount = 0, onMarkRead }) {
  const set = (key, val) => onChange({ ...filters, [key]: val })

  // Search is debounced so typing doesn't fire a request per keystroke
  const [q, setQ] = useState(filters.q || '')
  const searchRef = useRef(null)
  useEffect(() => {
    if (q === (filters.q || '')) return
    const id = setTimeout(() => set('q', q), 350)
    return () => clearTimeout(id)
  }, [q])

  // "/" focuses search, Escape clears it
  useEffect(() => {
    const onKey = e => {
      const typing = ['INPUT', 'TEXTAREA', 'SELECT'].includes(document.activeElement?.tagName)
      if (e.key === '/' && !typing) {
        e.preventDefault()
        searchRef.current?.focus()
      }
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [])

  return (
    <div className="flex flex-wrap items-center gap-3 px-4 py-2 bg-gray-900 border-b border-gray-800">
      {/* Category pills */}
      <div className="flex gap-1.5 flex-wrap">
        {CATEGORIES.map(c => (
          <button
            key={c.value}
            onClick={() => set('category', c.value)}
            className={`px-2.5 py-0.5 rounded text-xs font-medium transition-colors
              ${filters.category === c.value
                ? 'bg-brand text-gray-950'
                : 'bg-gray-800 text-gray-400 hover:bg-gray-700 hover:text-white'
              }`}
          >
            {c.label}
          </button>
        ))}
      </div>

      <div className="h-4 w-px bg-gray-700" />

      {/* Region select */}
      <select
        value={filters.region || ''}
        onChange={e => set('region', e.target.value)}
        className="bg-gray-800 border border-gray-700 text-gray-300 text-xs rounded px-2 py-1 focus:outline-none focus:ring-1 focus:ring-brand"
      >
        {REGIONS.map(r => (
          <option key={r.value} value={r.value}>{r.label}</option>
        ))}
      </select>

      {/* Country select */}
      <select
        value={filters.country || ''}
        onChange={e => set('country', e.target.value)}
        className="bg-gray-800 border border-gray-700 text-gray-300 text-xs rounded px-2 py-1 focus:outline-none focus:ring-1 focus:ring-brand"
      >
        {COUNTRIES.map(c => (
          <option key={c.value} value={c.value}>{c.label}</option>
        ))}
      </select>

      {/* Search */}
      <input
        ref={searchRef}
        type="search"
        placeholder="Search…  ( / )"
        aria-label="Search articles"
        value={q}
        onChange={e => setQ(e.target.value)}
        onKeyDown={e => { if (e.key === 'Escape') { setQ(''); e.currentTarget.blur() } }}
        className="bg-gray-800 border border-gray-700 text-gray-300 text-xs rounded px-2 py-1 w-40 focus:outline-none focus:ring-1 focus:ring-brand placeholder-gray-600"
      />

      <div className="ml-auto flex items-center gap-2">
        {newCount > 0 && (
          <button
            type="button"
            onClick={onMarkRead}
            className="text-xs text-brand hover:underline"
          >
            {newCount} new · mark read
          </button>
        )}
        {filters.lastUpdate && (
          <span className="text-gray-600 text-xs">
            Updated {filters.lastUpdate.toLocaleTimeString()}
          </span>
        )}
      </div>
    </div>
  )
}
