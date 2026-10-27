import { formatDistanceToNow } from 'date-fns'
import { safeUrl } from '../lib/storage'
import { useBookmarks } from '../hooks/useBookmarks'

const COUNTRY_FLAGS = {
  US:        '🇺🇸 ',
  UK:        '🇬🇧 ',
  India:     '🇮🇳 ',
  Sweden:    '🇸🇪 ',
  Germany:   '🇩🇪 ',
  Japan:     '🇯🇵 ',
  Singapore: '🇸🇬 ',
  Australia: '🇦🇺 ',
  China:     '🇨🇳 ',
}

const CATEGORY_COLORS = {
  politics:         'text-blue-400 border-blue-800',
  geopolitics:      'text-orange-400 border-orange-800',
  business:         'text-yellow-400 border-yellow-800',
  technology:       'text-cyan-400 border-cyan-800',
  security:         'text-red-400 border-red-800',
  startups:         'text-purple-400 border-purple-800',
  'venture-capital':'text-pink-400 border-pink-800',
  science:          'text-teal-400 border-teal-800',
}

function timeAgo(iso) {
  if (!iso) return ''
  try {
    return formatDistanceToNow(new Date(iso), { addSuffix: true })
  } catch {
    return ''
  }
}

export default function ArticleCard({ article, isNew = false }) {
  const cc = CATEGORY_COLORS[article.category] || 'text-gray-400 border-gray-700'
  const bookmarks = useBookmarks()
  const saved = bookmarks?.isSaved(article.url)

  return (
    <div className="relative group">
      <a
        href={safeUrl(article.url)}
        target="_blank"
        rel="noopener noreferrer"
        className={`block p-3 border rounded bg-gray-900 hover:border-gray-600 hover:bg-gray-800 transition-colors
          ${isNew ? 'border-brand/50' : 'border-gray-800'}`}
      >
        {safeUrl(article.image_url) && (
          <img
            src={safeUrl(article.image_url)}
            alt=""
            loading="lazy"
            referrerPolicy="no-referrer"
            className="w-full h-24 object-cover rounded mb-2 opacity-80 group-hover:opacity-100"
            onError={e => { e.target.style.display = 'none' }}
          />
        )}

        <div className="flex items-center gap-2 mb-1 flex-wrap pr-6">
          {isNew && (
            <span className="text-[10px] font-bold uppercase tracking-wider bg-brand text-gray-950 rounded px-1.5 py-0.5">
              New
            </span>
          )}
          <span className={`text-[10px] font-semibold uppercase tracking-wider border rounded px-1.5 py-0.5 ${cc}`}>
            {article.category || 'news'}
          </span>
          {article.country && (
            <span className="text-[10px] bg-gray-800 text-gray-400 rounded px-1.5 py-0.5">
              {COUNTRY_FLAGS[article.country] || ''}{article.country}
            </span>
          )}
          {article.region && !article.country && (
            <span className="text-[10px] text-gray-600 uppercase">{article.region}</span>
          )}
          <span className="ml-auto text-[10px] text-gray-600">{timeAgo(article.published_at || article.fetched_at)}</span>
        </div>

        <p className="text-sm text-gray-200 font-medium leading-snug line-clamp-3 group-hover:text-white">
          {article.title}
        </p>

        {article.summary && (
          <p className="mt-1 text-xs text-gray-500 line-clamp-2">{article.summary}</p>
        )}

        <p className="mt-1.5 text-[10px] text-gray-600 truncate">{article.source}</p>
      </a>

      {bookmarks && (
        <button
          type="button"
          onClick={() => bookmarks.toggle(article)}
          title={saved ? 'Remove from saved' : 'Save for later'}
          aria-label={saved ? 'Remove from saved' : 'Save for later'}
          aria-pressed={saved}
          className={`absolute top-2 right-2 w-6 h-6 flex items-center justify-center rounded text-sm transition-opacity
            ${saved ? 'text-brand opacity-100' : 'text-gray-500 hover:text-white opacity-0 group-hover:opacity-100 focus:opacity-100'}`}
        >
          {saved ? '★' : '☆'}
        </button>
      )}
    </div>
  )
}
