import { formatDistanceToNow } from 'date-fns'

const PLATFORM_STYLES = {
  reddit:      { label: 'r/', color: 'text-orange-400' },
  hackernews:  { label: 'HN', color: 'text-yellow-400' },
  stocktwits:  { label: 'ST', color: 'text-blue-400'   },
}

const SENTIMENT_STYLES = {
  bullish: 'text-green-400',
  bearish: 'text-red-400',
  neutral: 'text-gray-400',
}

function timeAgo(iso) {
  if (!iso) return ''
  try { return formatDistanceToNow(new Date(iso), { addSuffix: true }) } catch { return '' }
}

export default function SocialCard({ post }) {
  const pt = PLATFORM_STYLES[post.platform] || { label: post.platform, color: 'text-gray-400' }

  return (
    <a
      href={post.url || '#'}
      target="_blank"
      rel="noopener noreferrer"
      className="block p-3 border border-gray-800 rounded bg-gray-900 hover:border-gray-600 transition-colors"
    >
      <div className="flex items-center gap-2 mb-1">
        <span className={`text-[10px] font-bold ${pt.color}`}>
          {pt.label}{post.community && post.platform === 'reddit' ? post.community : ''}
        </span>
        {post.sentiment && (
          <span className={`text-[10px] font-semibold ${SENTIMENT_STYLES[post.sentiment] || 'text-gray-400'}`}>
            ▲ {post.sentiment}
          </span>
        )}
        <span className="ml-auto text-[10px] text-gray-600">{timeAgo(post.published_at)}</span>
      </div>
      <p className="text-xs text-gray-200 leading-snug line-clamp-3">{post.title}</p>
      <div className="mt-1.5 flex items-center gap-3 text-[10px] text-gray-600">
        {post.score != null     && <span>▲ {post.score.toLocaleString()}</span>}
        {post.num_comments != null && <span>💬 {post.num_comments.toLocaleString()}</span>}
      </div>
    </a>
  )
}
