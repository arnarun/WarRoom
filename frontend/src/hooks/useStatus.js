import { useState, useEffect, useCallback } from 'react'
import api from '../lib/api'

// A job is stale if it hasn't succeeded within 2.5x its interval
function health(status) {
  if (!status) return 'unknown'
  const now = Date.now()
  let worst = 'ok'
  for (const j of status.jobs || []) {
    const last = j.last_success ? new Date(j.last_success).getTime() : null
    const stale = last == null || now - last > j.interval_s * 2500
    if (j.last_error && stale) return 'down'
    if (stale && j.runs > 0) worst = 'degraded'
  }
  if ((status.rss?.fail || 0) > 10) worst = 'degraded'
  return worst
}

export function useStatus(interval = 60000) {
  const [status, setStatus] = useState(null)
  const [error,  setError]  = useState(null)

  const fetch = useCallback(async () => {
    try {
      const { data } = await api.get('/status')
      setStatus(data)
      setError(null)
    } catch (e) {
      setError(e.message)
    }
  }, [])

  useEffect(() => {
    fetch()
    const id = setInterval(fetch, interval)
    return () => clearInterval(id)
  }, [fetch, interval])

  return { status, error, health: error ? 'down' : health(status), refetch: fetch }
}
