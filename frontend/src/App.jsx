import { useState } from 'react'
import MarketTicker  from './components/MarketTicker'
import FilterBar     from './components/FilterBar'
import FeedColumn    from './components/FeedColumn'
import ArticleCard   from './components/ArticleCard'
import SignalCard    from './components/SignalCard'
import SocialCard    from './components/SocialCard'
import MarketPanel   from './components/MarketPanel'
import WorldClock        from './components/WorldClock'
import HotTopicsBanner  from './components/HotTopicsBanner'
import { useArticles } from './hooks/useArticles'
import { useOsint }    from './hooks/useOsint'

const VIEWS = ['feed', 'market', 'osint', 'social']

export default function App() {
  const [view,    setView]    = useState('feed')
  const [filters, setFilters] = useState({ category: '', region: '', country: '', q: '' })

  const { articles, loading: artLoading, lastUpdate } = useArticles(filters, 30000)
  const { signals,  loading: osintLoading }            = useOsint({}, 60000)

  // Group articles by category for multi-column layout
  const grouped = {}
  for (const a of articles) {
    const cat = a.category || 'other'
    if (!grouped[cat]) grouped[cat] = []
    grouped[cat].push(a)
  }

  const CATEGORY_ICONS = {
    politics:         '🗳',
    geopolitics:      '🌍',
    business:         '📈',
    technology:       '💻',
    security:         '🔐',
    defense:          '⚔️',
    health:           '🏥',
    emergency:        '🚨',
    startups:         '🚀',
    'venture-capital':'💰',
    science:          '🔬',
    people:           '👤',
    other:            '📰',
  }

  return (
    <div className="flex flex-col h-screen bg-gray-950 text-gray-100">
      {/* Top bar */}
      <header className="flex items-center gap-4 px-4 py-2 bg-gray-900 border-b border-gray-800">
        <h1 className="text-sm font-bold text-brand tracking-widest uppercase">
          ⬡ WarRoom
        </h1>
        <span className="text-gray-600 text-xs hidden sm:inline">Global Intelligence Dashboard</span>

        <div className="ml-auto mr-4">
          <WorldClock />
        </div>

        <nav className="flex gap-1">
          {VIEWS.map(v => (
            <button
              key={v}
              onClick={() => setView(v)}
              className={`px-3 py-1 rounded text-xs uppercase font-medium transition-colors
                ${view === v
                  ? 'bg-brand text-gray-950'
                  : 'text-gray-500 hover:text-white hover:bg-gray-800'
                }`}
            >
              {v}
            </button>
          ))}
        </nav>
      </header>

      {/* Live price ticker */}
      <MarketTicker />

      {/* Filter bar (only for feed view) */}
      {view === 'feed' && (
        <FilterBar
          filters={{ ...filters, lastUpdate }}
          onChange={f => setFilters({ category: f.category, region: f.region, country: f.country || '', q: f.q })}
        />
      )}

      {/* Main content */}
      <main className="flex-1 overflow-hidden">

        {/* FEED VIEW — multi-column by category */}
        {view === 'feed' && (
          <div className="flex flex-col h-full">
            {/* Hot topics banner — top of feed */}
            <HotTopicsBanner />

          <div className="flex gap-0 flex-1 overflow-x-auto border-t border-gray-800">
            {artLoading && articles.length === 0 && (
              <div className="flex-1 flex items-center justify-center text-gray-600 text-sm">
                Fetching feeds… (first run may take ~60s)
              </div>
            )}

            {/* If a specific category is selected, show single column */}
            {filters.category ? (
              <FeedColumn
                title={filters.category}
                icon={CATEGORY_ICONS[filters.category]}
                count={articles.length}
                className="flex-1 max-w-none"
              >
                {articles.map(a => <ArticleCard key={a.id} article={a} />)}
              </FeedColumn>
            ) : (
              /* Multi-column: one per category */
              Object.entries(grouped).sort().map(([cat, arts]) => (
                <FeedColumn
                  key={cat}
                  title={cat}
                  icon={CATEGORY_ICONS[cat]}
                  count={arts.length}
                  className="border-r border-gray-800"
                >
                  {arts.slice(0, 40).map(a => <ArticleCard key={a.id} article={a} />)}
                </FeedColumn>
              ))
            )}
          </div>
          </div>
        )}

        {/* MARKET VIEW */}
        {view === 'market' && (
          <div className="h-full overflow-y-auto p-4 space-y-6">
            <section>
              <h2 className="text-xs font-bold uppercase text-brand mb-2 tracking-wider">
                Crypto — Top 10
              </h2>
              <div className="border border-gray-800 rounded overflow-hidden">
                <MarketPanel type="crypto" />
              </div>
            </section>
            <section>
              <h2 className="text-xs font-bold uppercase text-brand mb-2 tracking-wider">
                Stocks &amp; ETFs
              </h2>
              <div className="border border-gray-800 rounded overflow-hidden">
                <MarketPanel type="stock" />
              </div>
            </section>
            <section>
              <h2 className="text-xs font-bold uppercase text-brand mb-2 tracking-wider">
                Forex
              </h2>
              <div className="border border-gray-800 rounded overflow-hidden">
                <MarketPanel type="forex" />
              </div>
            </section>
          </div>
        )}

        {/* OSINT VIEW */}
        {view === 'osint' && (
          <OsintView signals={signals} loading={osintLoading} />
        )}

        {/* SOCIAL VIEW */}
        {view === 'social' && (
          <SocialView />
        )}

      </main>

      {/* Status bar */}
      <footer className="flex items-center gap-4 px-4 py-1 bg-gray-900 border-t border-gray-800 text-[10px] text-gray-600">
        <span>{articles.length} articles</span>
        <span>{signals.length} signals</span>
        <span className="ml-auto">WarRoom v1.0 — {new Date().toLocaleTimeString()}</span>
      </footer>
    </div>
  )
}

const OSINT_COUNTRIES = ['All', 'US', 'UK', 'India', 'Germany', 'EU', 'Sweden', 'Japan', 'Singapore', 'Australia']
const OSINT_TYPES     = ['All', 'vulnerability', 'cyber-threat', 'malware', 'breach', 'threat-intel', 'threat-actor', 'darkweb', 'conflict', 'people']

function OsintView({ signals, loading }) {
  const [countryTab, setCountryTab] = useState('All')
  const [typeTab,    setTypeTab]    = useState('All')

  const filtered = signals.filter(s => {
    const matchCountry = countryTab === 'All' || s.country === countryTab
    const matchType    = typeTab    === 'All' || s.type    === typeTab
    return matchCountry && matchType
  })

  const cisa    = filtered.filter(s => ['cisa', 'ncsc-uk', 'enisa', 'bsi', 'cert-in'].includes(s.source))
  const nvd     = filtered.filter(s => s.source === 'nvd')
  const malware = filtered.filter(s => ['urlhaus', 'malwarebazaar'].includes(s.source))
  const threat  = filtered.filter(s => ['alienvault'].includes(s.source))
  const breach  = filtered.filter(s => s.type === 'breach')
  const darkweb = filtered.filter(s => ['darkweb-news', 'tor'].includes(s.source) || s.type === 'darkweb')

  return (
    <div className="flex flex-col h-full">
      {/* Filter bar */}
      <div className="flex flex-wrap gap-2 px-4 py-2 border-b border-gray-800 bg-gray-900">
        <div className="flex gap-1 flex-wrap">
          {OSINT_COUNTRIES.map(c => (
            <button key={c} onClick={() => setCountryTab(c)}
              className={`px-2 py-0.5 rounded text-[10px] uppercase font-medium transition-colors
                ${countryTab === c ? 'bg-brand text-gray-950' : 'text-gray-500 hover:text-white hover:bg-gray-800'}`}>
              {c}
            </button>
          ))}
        </div>
        <div className="h-4 w-px bg-gray-700 self-center" />
        <div className="flex gap-1 flex-wrap">
          {OSINT_TYPES.map(t => (
            <button key={t} onClick={() => setTypeTab(t)}
              className={`px-2 py-0.5 rounded text-[10px] uppercase font-medium transition-colors
                ${typeTab === t ? 'bg-brand text-gray-950' : 'text-gray-500 hover:text-white hover:bg-gray-800'}`}>
              {t}
            </button>
          ))}
        </div>
      </div>

      {/* Columns */}
      <div className="flex gap-0 flex-1 overflow-x-auto border-t border-gray-800">
        <FeedColumn title="CERT Alerts" icon="🛡" className="border-r border-gray-800 flex-1">
          {cisa.map(s => <SignalCard key={s.id} signal={s} />)}
          {!loading && cisa.length === 0 && <p className="text-gray-600 text-xs p-2">No signals yet.</p>}
        </FeedColumn>

        <FeedColumn title="CVEs (NVD)" icon="🩹" className="border-r border-gray-800 flex-1">
          {nvd.map(s => <SignalCard key={s.id} signal={s} />)}
          {!loading && nvd.length === 0 && <p className="text-gray-600 text-xs p-2">No CVEs yet. Fetching every 30 min.</p>}
        </FeedColumn>

        <FeedColumn title="Malware" icon="🦠" className="border-r border-gray-800 flex-1">
          {malware.map(s => <SignalCard key={s.id} signal={s} />)}
          {!loading && malware.length === 0 && <p className="text-gray-600 text-xs p-2">No signals yet.</p>}
        </FeedColumn>

        <FeedColumn title="AlienVault OTX" icon="👁" className="border-r border-gray-800 flex-1">
          {threat.map(s => <SignalCard key={s.id} signal={s} />)}
          {!loading && threat.length === 0 && <p className="text-gray-600 text-xs p-2">No signals yet.</p>}
        </FeedColumn>

        <FeedColumn title="Breaches" icon="🔓" className="border-r border-gray-800 flex-1">
          {breach.map(s => <SignalCard key={s.id} signal={s} />)}
          {!loading && breach.length === 0 && <p className="text-gray-600 text-xs p-2">No signals yet.</p>}
        </FeedColumn>

        <FeedColumn title="Dark Web 🌐" icon="🧅" className="flex-1">
          {darkweb.map(s => <SignalCard key={s.id} signal={s} />)}
          {!loading && darkweb.length === 0 && (
            <p className="text-gray-600 text-xs p-2">
              Clearnet aggregators populate within 30 min.
            </p>
          )}
        </FeedColumn>
      </div>
    </div>
  )
}

function SocialView() {
  const [platform, setPlatform] = useState('hackernews')
  const [posts, setPosts]       = useState([])
  const [loading, setLoading]   = useState(true)

  useState(() => {
    import('./lib/api').then(({ default: api }) => {
      api.get('/social', { params: { limit: 100 } })
        .then(r => { setPosts(r.data); setLoading(false) })
        .catch(() => setLoading(false))
    })
  })

  const platforms = ['hackernews', 'reddit', 'stocktwits']
  const filtered = posts.filter(p => p.platform === platform)

  return (
    <div className="flex flex-col h-full">
      <div className="flex gap-1 px-4 py-2 border-b border-gray-800 bg-gray-900">
        {platforms.map(p => (
          <button
            key={p}
            onClick={() => setPlatform(p)}
            className={`px-3 py-0.5 rounded text-xs uppercase font-medium transition-colors
              ${platform === p ? 'bg-brand text-gray-950' : 'text-gray-500 hover:text-white hover:bg-gray-800'}`}
          >
            {p}
          </button>
        ))}
      </div>
      <div className="flex-1 overflow-y-auto p-2 space-y-2 max-w-2xl mx-auto w-full">
        {loading && <p className="text-gray-600 text-xs text-center py-8">Loading…</p>}
        {filtered.map(p => <SocialCard key={p.id} post={p} />)}
        {!loading && filtered.length === 0 && (
          <p className="text-gray-600 text-xs text-center py-8">No posts yet. Fetching every 30 min.</p>
        )}
      </div>
    </div>
  )
}
