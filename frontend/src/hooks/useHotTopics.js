import { useState, useEffect, useCallback } from 'react'
import api from '../lib/api'

export function useHotTopics(hours = 6, interval = 180000) {
  const [topics,  setTopics]  = useState([])
  const [loading, setLoading] = useState(true)

  const fetch = useCallback(() => {
    api.get('/articles/hot', { params: { hours, limit: 60 } })
      .then(r => { setTopics(r.data); setLoading(false) })
      .catch(() => setLoading(false))
  }, [hours])

  useEffect(() => {
    fetch()
    const id = setInterval(fetch, interval)
    return () => clearInterval(id)
  }, [fetch, interval])

  return { topics, loading }
}
