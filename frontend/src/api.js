async function req(method, url, body) {
  const res = await fetch(url, {
    method,
    headers: body !== undefined ? { 'Content-Type': 'application/json' } : undefined,
    body: body !== undefined ? JSON.stringify(body) : undefined,
  })
  let data = {}
  try { data = await res.json() } catch { /* empty */ }
  if (res.status === 401 && !url.startsWith('/api/auth/')) window.dispatchEvent(new Event('pai:signed-out'))
  if (!res.ok) throw new Error(data.error || `HTTP ${res.status}`)
  return data
}

export const api = {
  me: () => req('GET', '/api/auth/me'),
  auth: (mode, username, password) => req('POST', `/api/auth/${mode}`, { username, password }),
  logout: () => req('POST', '/api/auth/logout', {}),
  changePassword: (current, password) => req('POST', '/api/account/password', { current, password }),
  rename: (username) => req('POST', '/api/account/rename', { username }),
  bootstrap: () => req('GET', '/api/bootstrap'),
  patchSettings: (patch) => req('PATCH', '/api/settings', patch),
  setKey: (provider, key) => req('PUT', `/api/keys/${provider}`, { key }),
  models: () => req('GET', '/api/models'),
  createCharacter: (c) => req('POST', '/api/characters', c),
  updateCharacter: (id, c) => req('PUT', `/api/characters/${id}`, c),
  deleteCharacter: (id) => req('DELETE', `/api/characters/${id}`),
  sessions: (characterId) => req('GET', '/api/sessions' + (characterId != null ? `?character_id=${characterId}` : '')),
  session: (id) => req('GET', `/api/sessions/${id}`),
  createSession: (character_id, messages) => req('POST', '/api/sessions', { character_id, messages }),
  updateSession: (id, character_id, messages) => req('PUT', `/api/sessions/${id}`, { character_id, messages }),
  deleteSession: (id) => req('DELETE', `/api/sessions/${id}`),
  search: (q) => req('GET', `/api/search?q=${encodeURIComponent(q)}`),
  reset: () => req('POST', '/api/reset'),
}

/** Stream a reply. onEvent receives {t:'token'|'fallback'|'done'|'error', ...}. */
export async function generate({ character_id, session_id, messages, signal, onEvent }) {
  const res = await fetch('/api/generate', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ character_id, session_id, messages: messages.map(({ role, content }) => ({ role, content })) }),
    signal,
  })
  if (!res.ok || !res.body) throw new Error(`HTTP ${res.status}`)
  const reader = res.body.getReader()
  const dec = new TextDecoder()
  let buf = ''
  for (;;) {
    const { value, done } = await reader.read()
    if (done) break
    buf += dec.decode(value, { stream: true })
    let i
    while ((i = buf.indexOf('\n\n')) >= 0) {
      const chunk = buf.slice(0, i)
      buf = buf.slice(i + 2)
      for (const line of chunk.split('\n')) {
        if (line.startsWith('data: ')) {
          try { onEvent(JSON.parse(line.slice(6))) } catch { /* skip */ }
        }
      }
    }
  }
}
