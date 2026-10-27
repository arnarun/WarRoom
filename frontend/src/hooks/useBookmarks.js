import { useState, useEffect, useCallback, createContext, useContext } from 'react'
import { load, save } from '../lib/storage'

const KEY = 'warroom.bookmarks'
const MAX = 500

// Saved articles live in the viewer's browser only (keyed by URL, newest first)
export function useBookmarkStore() {
  const [items, setItems] = useState(() => load(KEY, []))

  useEffect(() => { save(KEY, items) }, [items])

  const isSaved = useCallback(url => items.some(i => i.url === url), [items])

  const toggle = useCallback(article => {
    setItems(prev => prev.some(i => i.url === article.url)
      ? prev.filter(i => i.url !== article.url)
      : [{ ...article, saved_at: new Date().toISOString() }, ...prev].slice(0, MAX))
  }, [])

  const clear = useCallback(() => setItems([]), [])

  return { items, isSaved, toggle, clear }
}

export const BookmarkContext = createContext(null)
export const useBookmarks = () => useContext(BookmarkContext)
