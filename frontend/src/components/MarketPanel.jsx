import { useMarket } from '../hooks/useMarket'

function fmt(n) {
  if (n == null) return '—'
  if (n >= 1e9)  return `$${(n / 1e9).toFixed(1)}B`
  if (n >= 1e6)  return `$${(n / 1e6).toFixed(1)}M`
  if (n >= 1000) return n.toLocaleString('en-US', { maximumFractionDigits: 2 })
  return n.toLocaleString('en-US', { maximumFractionDigits: 6 })
}

function pct(n) {
  if (n == null) return <span className="text-gray-600">—</span>
  const c = n >= 0 ? 'text-green-400' : 'text-red-400'
  return <span className={c}>{n >= 0 ? '+' : ''}{n.toFixed(2)}%</span>
}

function Row({ item }) {
  return (
    <tr className="border-b border-gray-800 hover:bg-gray-800/50">
      <td className="px-3 py-1.5 font-mono text-xs font-semibold text-gray-300">{item.symbol}</td>
      <td className="px-3 py-1.5 text-xs text-gray-400 max-w-[120px] truncate">{item.name}</td>
      <td className="px-3 py-1.5 text-xs text-white text-right font-mono">${fmt(item.price)}</td>
      <td className="px-3 py-1.5 text-xs text-right">{pct(item.change_24h)}</td>
      <td className="px-3 py-1.5 text-xs text-right">{pct(item.change_7d)}</td>
      <td className="px-3 py-1.5 text-xs text-gray-500 text-right">{fmt(item.market_cap)}</td>
    </tr>
  )
}

export default function MarketPanel({ type = 'crypto' }) {
  const { prices } = useMarket()
  const rows = prices.filter(p => p.type === type)

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-left">
        <thead>
          <tr className="border-b border-gray-700 text-[10px] uppercase text-gray-600">
            <th className="px-3 py-1.5">Symbol</th>
            <th className="px-3 py-1.5">Name</th>
            <th className="px-3 py-1.5 text-right">Price</th>
            <th className="px-3 py-1.5 text-right">24h</th>
            <th className="px-3 py-1.5 text-right">7d</th>
            <th className="px-3 py-1.5 text-right">Mkt Cap</th>
          </tr>
        </thead>
        <tbody>
          {rows.length === 0 && (
            <tr><td colSpan={6} className="px-3 py-4 text-center text-gray-600 text-xs">Loading…</td></tr>
          )}
          {rows.map(r => <Row key={r.symbol} item={r} />)}
        </tbody>
      </table>
    </div>
  )
}
