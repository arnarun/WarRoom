// localStorage can throw (private mode, blocked site data) — never let it break the UI
export function load(key, fallback) {
  try {
    const raw = localStorage.getItem(key)
    return raw == null ? fallback : JSON.parse(raw)
  } catch {
    return fallback
  }
}

export function save(key, value) {
  try {
    localStorage.setItem(key, JSON.stringify(value))
  } catch {
    /* ignore */
  }
}

// Feed URLs are untrusted; only allow http(s) hrefs
export function safeUrl(url) {
  return typeof url === 'string' && /^https?:\/\//i.test(url.trim()) ? url : undefined
}
