import { useState, useEffect, useCallback } from 'react'
import api from '../lib/api'

export function useArticles(filters = {}, interval = 30000) {
  const [articles, setArticles] = useState([])
  const [loading,  setLoading]  = useState(true)
  const [error,    setError]    = useState(null)
  const [lastUpdate, setLastUpdate] = useState(null)

  const fetch = useCallback(async () => {
    try {
      const params = Object.fromEntries(
        Object.entries(filters).filter(([_, v]) => v != null && v !== '')
      )
      const { data } = await api.get('/articles', { params })
      setArticles(Array.isArray(data) ? data : [])
      setLastUpdate(new Date())
      setError(null)
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }, [JSON.stringify(filters)])

  useEffect(() => {
    fetch()
    const id = setInterval(fetch, interval)
    return () => clearInterval(id)
  }, [fetch, interval])

  return { articles, loading, error, lastUpdate, refetch: fetch }
}
