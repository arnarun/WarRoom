import { useMarket } from '../hooks/useMarket'

// Priority order for ticker display
const TICKER_ORDER = ['S&P 500', 'Dow Jones', 'NASDAQ', 'Gold', 'Silver', 'BTC', 'ETH', 'SOL', 'BNB']

const TYPE_COLORS = {
  crypto: 'text-yellow-400',
  stock:  'text-cyan-400',
  forex:  'text-purple-400',
}

const TYPE_LABELS = {
  crypto: '',
  stock:  '',
  forex:  '',
}

function fmt(n, type) {
  if (n == null) return '—'
  if (type === 'forex') {
    return n.toLocaleString('en-US', { maximumFractionDigits: 4, minimumFractionDigits: 4 })
  }
  if (n >= 1000) {
    return n.toLocaleString('en-US', { maximumFractionDigits: 2, minimumFractionDigits: 2 })
  }
  return n.toLocaleString('en-US', { maximumFractionDigits: 4, minimumFractionDigits: 2 })
}

function fmtChange(n) {
  if (n == null) return null
  return `${n >= 0 ? '+' : ''}${n.toFixed(2)}%`
}

function PriceChip({ item }) {
  const chg   = item.change_24h
  const color = chg == null ? 'text-gray-400' : chg >= 0 ? 'text-green-400' : 'text-red-400'
  const arrow = chg == null ? '' : chg >= 0 ? '▲' : '▼'
  const typeColor = TYPE_COLORS[item.type] || 'text-gray-400'

  return (
    <span className="inline-flex items-center gap-1.5 shrink-0 px-3 border-r border-gray-800">
      <span className={`text-[11px] font-bold ${typeColor}`}>{item.name || item.symbol}</span>
      <span className="text-white text-[11px] font-mono">{fmt(item.price, item.type)}</span>
      {chg != null && (
        <span className={`text-[10px] ${color}`}>{arrow} {fmtChange(chg)}</span>
      )}
    </span>
  )
}

function sortPrices(prices) {
  // Sort: S&P 500 first, then gold, then crypto, then other stocks, then forex
  return [...prices].sort((a, b) => {
    const ai = TICKER_ORDER.indexOf(a.name || a.symbol)
    const bi = TICKER_ORDER.indexOf(b.name || b.symbol)
    if (ai !== -1 && bi !== -1) return ai - bi
    if (ai !== -1) return -1
    if (bi !== -1) return 1
    // crypto before stock before forex
    const typeOrder = { stock: 0, crypto: 1, forex: 2 }
    return (typeOrder[a.type] ?? 3) - (typeOrder[b.type] ?? 3)
  })
}

export default function MarketTicker() {
  const { prices, connected } = useMarket()
  const sorted = sortPrices(prices)

  // Duplicate items so the scroll loops seamlessly
  const items = sorted.length > 0 ? [...sorted, ...sorted] : []

  return (
    <div className="flex items-center bg-gray-900 border-b border-gray-800 overflow-hidden h-8">
      {/* Live indicator — fixed left */}
      <span className={`shrink-0 text-[10px] font-bold px-3 border-r border-gray-800 ${connected ? 'text-brand' : 'text-yellow-500'}`}>
        {connected ? '● LIVE' : '○ …'}
      </span>

      {sorted.length === 0 ? (
        <span className="text-gray-600 text-xs px-4">Loading prices…</span>
      ) : (
        /* Scrolling marquee */
        <div className="flex-1 overflow-hidden">
          <div
            className="flex items-center"
            style={{
              display: 'flex',
              animation: `ticker-scroll ${sorted.length * 4}s linear infinite`,
              width: 'max-content',
            }}
          >
            {items.map((p, i) => (
              <PriceChip key={`${p.symbol}-${i}`} item={p} />
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
