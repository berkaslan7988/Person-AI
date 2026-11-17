import React, { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState } from 'react'
import { api, generate } from './api.js'
import { makeT } from './i18n.js'
import { setFavicon } from './components/Logo.jsx'
import { cardLooksUnderage, fromSillyTavern, imageToDataUrl, pngCardJson, readFile } from './lib.jsx'

const Ctx = createContext(null)
export const useStore = () => useContext(Ctx)

const nowIso = () => new Date().toISOString()
const EMPTY_MEMORY = { summary: '', summary_upto: 0, notes: '' }
function firstMessage(char) {
  const greets = [char?.greeting, ...(char?.alt_greetings || [])].filter((g) => g && g.trim())
  if (!greets.length) return []
  const m = { role: 'assistant', content: greets[0], timestamp: nowIso() }
  if (greets.length > 1) { m.swipes = greets; m.swipe = 0 }
  return [m]
}
const freshSession = (char) => ({
  id: null,
  character_id: char?.id ?? null,
  messages: firstMessage(char),
  memory: EMPTY_MEMORY,
})

export function StoreProvider({ children }) {
  const [ready, setReady] = useState(false)
  const [bootError, setBootError] = useState('')
  const [settings, setSettings] = useState(null)
  const [models, setModels] = useState([])
  const [ollama, setOllama] = useState({ running: false, models: [] })
  const [keys, setKeys] = useState({})
  const [characters, setCharacters] = useState([])
  const [sessions, setSessions] = useState([])
  const [view, setView] = useState('chat')
  const [settingsSection, setSettingsSection] = useState('model')
  const [session, _setSession] = useState(freshSession(null))
  const sessionRef = useRef(session)
  const epochRef = useRef(0) // bumps whenever a different chat is opened
  const setSession = useCallback((s, switching = true) => {
    if (switching && typeof s !== 'function') epochRef.current += 1
    sessionRef.current = typeof s === 'function' ? s(sessionRef.current) : s
    _setSession(sessionRef.current)
  }, [])
  const [streaming, setStreaming] = useState(false)
  const [streamText, setStreamText] = useState('')
  const abortRef = useRef(null)
  const [toasts, setToasts] = useState([])
  const [confirmState, setConfirmState] = useState(null)

  const [account, setAccount] = useState(null)
  const [guest, setGuest] = useState({ hasUsers: true, local: true })
  const [guestLang, _setGuestLang] = useState(() => { try { return localStorage.getItem('pai.lang') || 'tr' } catch { return 'tr' } })
  const setGuestLang = useCallback((l) => { _setGuestLang(l); try { localStorage.setItem('pai.lang', l) } catch { /* ignore */ } }, [])
  const lang = settings?.language || guestLang
  const t = useMemo(() => makeT(lang), [lang])
  const tRef = useRef(t)
  tRef.current = t

  // ── toasts & confirm ─────────────────────────────────────
  const toast = useCallback((text, kind = 'info') => {
    const id = Math.random().toString(36).slice(2)
    setToasts((ts) => [...ts.slice(-3), { id, text, kind }])
    setTimeout(() => setToasts((ts) => ts.filter((x) => x.id !== id)), kind === 'error' ? 5200 : 3000)
  }, [])

  const confirm = useCallback((opts) => new Promise((resolve) => {
    setConfirmState({ ...opts, resolve: (v) => { setConfirmState(null); resolve(v) } })
  }), [])

  // ── boot ─────────────────────────────────────────────────
  const applyBoot = useCallback((d) => {
    setSettings(d.settings)
    setModels(d.models)
    setOllama(d.ollama || { running: false, models: [] })
    setKeys(d.keys)
    setCharacters(d.characters)
    setSessions(d.sessions)
    const s = d.active.session
    if (s) setSession({ id: s.id, character_id: s.character_id, messages: s.messages, memory: s.memory || EMPTY_MEMORY })
    else setSession(freshSession(d.characters.find((c) => c.id === d.active.character_id)))
  }, [setSession])

  const boot = useCallback(async () => {
    try {
      const me = await api.me()
      setGuest({ hasUsers: me.has_users, local: me.local })
      setAccount(me.account)
      if (me.account) {
        const d = await api.bootstrap()
        applyBoot(d)
        if (!d.models.some((m) => m.available)) { setView('settings'); setSettingsSection('model') }
      }
      setReady(true)
    } catch {
      setBootError(tRef.current('err_server'))
    }
  }, [applyBoot])

  useEffect(() => { boot() }, [boot])

  // ── account ──────────────────────────────────────────────
  const signedOut = useCallback(() => {
    abortRef.current?.abort()
    setAccount(null)
    setSettings(null)
    setCharacters([])
    setSessions([])
    setView('chat')
    setSettingsSection('model')
    setSession(freshSession(null))
    setGuest((g) => ({ ...g, hasUsers: true }))
  }, [setSession])

  useEffect(() => {
    const onOut = () => { if (account) { signedOut(); toast(tRef.current('session_expired'), 'info') } }
    window.addEventListener('pai:signed-out', onOut)
    return () => window.removeEventListener('pai:signed-out', onOut)
  }, [account, signedOut]) // eslint-disable-line

  const onAuthed = useCallback(async (acct, mode) => {
    const d = await api.bootstrap()
    applyBoot(d)
    setAccount(acct) // only after settings exist, so the app never renders half-loaded
    setView(d.models.some((m) => m.available) ? 'chat' : 'settings')
    if (!d.models.some((m) => m.available)) setSettingsSection('model')
    toast(tRef.current(mode === 'register' ? 'welcome_new' : 'welcome_back', { name: acct.username }), 'success')
  }, [applyBoot]) // eslint-disable-line

  const logout = useCallback(async () => {
    try { await api.logout() } catch { /* ignore */ }
    signedOut()
  }, [signedOut])

  const refreshLists = useCallback(async () => {
    try {
      const [c, s] = await Promise.all([fetch('/api/characters').then((r) => r.json()), api.sessions()])
      setCharacters(c.characters)
      setSessions(s.sessions)
    } catch { /* ignore */ }
  }, [])

  const refreshListsRef = useRef(refreshLists)
  refreshListsRef.current = refreshLists

  // ── theme ────────────────────────────────────────────────
  useEffect(() => {
    if (settings?.language) setGuestLang(settings.language)
  }, [settings?.language]) // eslint-disable-line

  useEffect(() => {
    if (!settings) return
    const root = document.documentElement
    const mq = matchMedia('(prefers-color-scheme: light)')
    const apply = () => {
      const m = settings.theme_mode === 'system' ? (mq.matches ? 'light' : 'dark') : settings.theme_mode
      root.dataset.theme = m
    }
    apply()
    if (settings.accent_color) root.style.setProperty('--accent', settings.accent_color)
    else root.style.removeProperty('--accent')
    setFavicon(settings.accent_color || getComputedStyle(root).getPropertyValue('--accent').trim())
    root.lang = settings.language
    try {
      localStorage.setItem('pai.theme', settings.theme_mode)
      if (settings.accent_color) localStorage.setItem('pai.accent', settings.accent_color)
      else localStorage.removeItem('pai.accent')
    } catch { /* ignore */ }
    mq.addEventListener('change', apply)
    return () => mq.removeEventListener('change', apply)
  }, [settings?.theme_mode, settings?.accent_color, settings?.language]) // eslint-disable-line

  // ── settings / keys ──────────────────────────────────────
  const updateSettings = useCallback(async (patch) => {
    setSettings((s) => ({ ...s, ...patch }))
    try {
      const r = await api.patchSettings(patch)
      setSettings(r.settings)
    } catch { toast(tRef.current('err_server'), 'error') }
  }, [toast])

  const saveKey = useCallback(async (provider, key) => {
    let r
    try { r = await api.setKey(provider, key) } catch (e) {
      toast(tRef.current(e.message === 'keys_local_only' ? 'keys_local_only' : 'err_server'), 'error')
      return
    }
    setKeys(r.keys)
    setModels(r.models)
    setSettings(r.settings)
    const label = r.keys[provider]?.label || provider
    toast(tRef.current(key ? 'key_saved' : 'key_removed', { p: label }), 'success')
  }, [toast])

  const refreshModels = useCallback(async () => {
    try {
      const r = await api.models()
      setModels(r.models)
      setOllama(r.ollama)
      setSettings(r.settings)
    } catch { /* ignore */ }
  }, [])

  // ── derived ──────────────────────────────────────────────
  const activeCharacter = useMemo(
    () => characters.find((c) => c.id === session.character_id) || characters[0] || null,
    [characters, session.character_id],
  )
  const hasModel = models.some((m) => m.available) || (settings?.selected_model || '').startsWith('Ollama: ')

  // ── session persistence ──────────────────────────────────
  const persistQueue = useRef(Promise.resolve())
  const persist = useCallback(() => {
    persistQueue.current = persistQueue.current.then(async () => {
      const s = sessionRef.current
      if (!s.id && !s.messages.some((m) => m.role === 'user')) return
      try {
        const r = s.id
          ? await api.updateSession(s.id, s.character_id, s.messages)
          : await api.createSession(s.character_id, s.messages)
        if (!sessionRef.current.id && sessionRef.current.character_id === s.character_id) {
          setSession((cur) => ({ ...cur, id: r.session.id }), false)
        }
        await refreshListsRef.current()
      } catch { toast(tRef.current('err_server'), 'error') }
    })
    return persistQueue.current
  }, [setSession, toast])

  const setMessages = useCallback((fn) => {
    setSession((s) => ({ ...s, messages: typeof fn === 'function' ? fn(s.messages) : fn }), false)
  }, [setSession])

  // ── long-term memory ─────────────────────────────────────
  const [memoryBusy, setMemoryBusy] = useState(false)
  const settingsRef = useRef(settings)
  settingsRef.current = settings

  const summarize = useCallback(async (full = false, { quiet = true } = {}) => {
    const s = sessionRef.current
    if (!s.id) return
    const epoch = epochRef.current
    setMemoryBusy(true)
    try {
      const res = await fetch(`/api/sessions/${s.id}/summarize`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ full }),
      })
      const r = await res.json()
      if (!res.ok) throw new Error(r.error || 'error')
      if (epochRef.current === epoch) setSession((cur) => ({ ...cur, memory: r.memory }), false)
      if (!quiet) toast(tRef.current(r.changed ? 'memory_updated' : 'memory_nothing'), 'success')
    } catch (e) {
      if (!quiet) toast(tRef.current('memory_failed'), 'error')
      console.warn('[memory]', e)
    } finally { setMemoryBusy(false) }
  }, [setSession, toast])

  const maybeSummarize = useCallback(() => {
    const s = sessionRef.current
    const win = settingsRef.current?.memory_size || 20
    const cutoff = s.messages.length - win
    if (s.id && cutoff - (s.memory?.summary_upto || 0) >= 6) summarize(false)
  }, [summarize])

  const updateMemory = useCallback(async (patch) => {
    const s = sessionRef.current
    setSession((cur) => ({ ...cur, memory: { ...cur.memory, ...patch } }), false)
    if (!s.id) return
    try {
      const res = await fetch(`/api/sessions/${s.id}/memory`, {
        method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(patch),
      })
      if (!res.ok) throw new Error()
    } catch { toast(tRef.current('err_server'), 'error') }
  }, [setSession, toast])

  // ── generation ───────────────────────────────────────────
  const [swipeTarget, setSwipeTarget] = useState(null)
  const stop = useCallback(() => { abortRef.current?.abort() }, [])

  /** target = null → append a new reply; target = index → add a new swipe to that message. */
  const runGeneration = useCallback(async (target = null) => {
    const s = sessionRef.current
    const epoch = epochRef.current
    const tt = tRef.current
    const ctrl = new AbortController()
    abortRef.current = ctrl
    setSwipeTarget(target)
    setStreaming(true)
    setStreamText('')
    let acc = ''
    let raf = 0
    const flush = () => { raf = 0; setStreamText(acc) }
    let failed = false
    try {
      await generate({
        character_id: s.character_id,
        session_id: s.id,
        messages: target == null ? s.messages : s.messages.slice(0, target),
        signal: ctrl.signal,
        onEvent: (ev) => {
          if (ev.t === 'token') {
            acc += ev.v
            if (!raf) raf = requestAnimationFrame(flush)
          } else if (ev.t === 'fallback') {
            toast(tt('model_limit', { m: ev.model }), 'info')
            setSettings((st) => ({ ...st, selected_model: ev.model }))
          } else if (ev.t === 'error') {
            failed = true
            const msg = tt('err_' + ev.code)
            toast(msg === 'err_' + ev.code ? tt('err_unknown') : msg, 'error')
            if (ev.detail) console.warn('[provider]', ev.code, ev.detail)
          }
        },
      })
    } catch (e) {
      if (e.name !== 'AbortError') { failed = true; toast(tt('err_server'), 'error') }
    } finally {
      if (raf) cancelAnimationFrame(raf)
      abortRef.current = null
    }
    const text = acc.replace(/\s+$/, '')
    const sameChat = epochRef.current === epoch
    if (text.trim() && sameChat) {
      if (target == null) {
        setMessages((ms) => [...ms, { role: 'assistant', content: text, timestamp: nowIso() }])
      } else {
        setMessages((ms) => ms.map((m, i) => {
          if (i !== target) return m
          const swipes = [...(m.swipes || [m.content]), text]
          return { ...m, content: text, swipes, swipe: swipes.length - 1, timestamp: nowIso() }
        }))
      }
    } else if (!text.trim() && !failed && !ctrl.signal.aborted) {
      toast(tt('empty_reply'), 'error')
    }
    setStreaming(false)
    setStreamText('')
    setSwipeTarget(null)
    if (sameChat) persist().then(maybeSummarize)
  }, [maybeSummarize, persist, setMessages, toast])

  const send = useCallback(async (text) => {
    text = text.trim()
    if (!text || abortRef.current) return false
    if (!hasModel) { toast(tRef.current('add_key_first'), 'error'); return false }
    setMessages((ms) => [...ms, { role: 'user', content: text, timestamp: nowIso() }])
    await persist()
    runGeneration()
    return true
  }, [hasModel, persist, runGeneration, setMessages, toast])

  /** New swipe for an AI message (later messages are dropped, older swipes are kept). */
  const regenerate = useCallback(async (idx) => {
    if (abortRef.current) return
    const ms = sessionRef.current.messages
    if (idx < 1 || idx >= ms.length || ms[idx].role !== 'assistant') return
    if (!hasModel) { toast(tRef.current('add_key_first'), 'error'); return }
    setMessages(ms.slice(0, idx + 1))
    await persist()
    runGeneration(idx)
  }, [hasModel, persist, runGeneration, setMessages, toast])

  /** Move between swipes of the last AI message; past the end generates a new one. */
  const swipe = useCallback((idx, dir) => {
    if (abortRef.current) return
    const ms = sessionRef.current.messages
    const m = ms[idx]
    if (!m || m.role !== 'assistant' || idx !== ms.length - 1) return
    const list = m.swipes || [m.content]
    const cur = m.swipe || 0
    const next = cur + dir
    if (next < 0) return
    if (next >= list.length) {
      if (idx === 0) return // greeting without context: nothing to generate from
      regenerate(idx)
      return
    }
    setMessages(ms.map((x, i) => (i === idx ? { ...x, content: list[next], swipe: next, swipes: list } : x)))
    persist()
  }, [persist, regenerate, setMessages])

  const editMessage = useCallback(async (idx, text) => {
    const ms = sessionRef.current.messages
    if (idx < 0 || idx >= ms.length || !text.trim()) return
    const msg = { ...ms[idx], content: text }
    if (msg.swipes) { msg.swipes = msg.swipes.map((x, i) => (i === (msg.swipe || 0) ? text : x)) }
    if (msg.role === 'user') {
      // drop everything after the edited message and answer again
      setMessages([...ms.slice(0, idx), msg])
      await persist()
      if (hasModel) runGeneration()
      else toast(tRef.current('add_key_first'), 'error')
    } else {
      setMessages(ms.map((m, i) => (i === idx ? msg : m)))
      persist()
    }
  }, [hasModel, persist, runGeneration, setMessages, toast])

  const deleteMessage = useCallback((idx) => {
    setMessages((ms) => ms.filter((_, i) => i !== idx))
    persist()
  }, [persist, setMessages])

  const clearChat = useCallback(async () => {
    const tt = tRef.current
    const ok = await confirm({ title: tt('clear_chat_title'), body: tt('clear_chat_body'), ok: tt('btn_clear'), danger: true })
    if (!ok) return
    stop()
    const s = sessionRef.current
    if (s.id) {
      await api.deleteSession(s.id).catch(() => {})
    }
    setSession(freshSession(characters.find((c) => c.id === s.character_id)))
    refreshLists()
    toast(tt('chat_cleared'), 'success')
  }, [characters, confirm, refreshLists, setSession, stop, toast])

  // ── navigation between chats ─────────────────────────────
  const newChat = useCallback((char, silent) => {
    stop()
    const c = char || activeCharacter
    if (!c) return
    setSession(freshSession(c))
    setView('chat')
    if (!silent) toast(tRef.current('chat_started', { name: c.name }), 'success')
  }, [activeCharacter, setSession, stop, toast])

  const openSession = useCallback(async (id) => {
    stop()
    try {
      const r = await api.session(id)
      setSession({ id: r.session.id, character_id: r.session.character_id, messages: r.session.messages, memory: r.session.memory || EMPTY_MEMORY })
      setView('chat')
    } catch { toast(tRef.current('err_server'), 'error') }
  }, [setSession, stop, toast])

  const deleteSession = useCallback(async (id) => {
    const tt = tRef.current
    const ok = await confirm({ title: tt('delete_session_title'), body: tt('irreversible'), ok: tt('delete'), danger: true })
    if (!ok) return false
    await api.deleteSession(id)
    if (sessionRef.current.id === id) {
      stop()
      setSession(freshSession(characters.find((c) => c.id === sessionRef.current.character_id)))
    }
    await refreshLists()
    toast(tt('session_deleted'), 'success')
    return true
  }, [characters, confirm, refreshLists, setSession, stop, toast])

  // ── characters ───────────────────────────────────────────
  const saveCharacter = useCallback(async (data, id, { quiet } = {}) => {
    const r = id ? await api.updateCharacter(id, data) : await api.createCharacter(data)
    setCharacters(r.characters)
    if (!quiet) toast(tRef.current('char_saved', { name: r.character.name }), 'success')
    return r.character
  }, [toast])

  /** Import SillyTavern V2 cards (.png with embedded data or .json); several at once. */
  const importCards = useCallback(async (fileList) => {
    const tt = tRef.current
    const files = [...(fileList || [])]
    if (!files.length) return
    let ok = 0
    let last = null
    const skipped = { underage: 0, invalid: 0 }
    for (const f of files) {
      try {
        let card = null
        let avatar = ''
        if (/\.png$/i.test(f.name) || f.type === 'image/png') {
          card = pngCardJson(await readFile(f, 'buffer'))
          if (card) avatar = await imageToDataUrl(f, 512)
        } else if (/\.json$/i.test(f.name) || f.type === 'application/json') {
          card = JSON.parse(await readFile(f, 'text'))
        }
        if (!card) { skipped.invalid++; continue }
        if (cardLooksUnderage(card)) { skipped.underage++; continue }
        const data = fromSillyTavern(card)
        if (avatar) data.avatar_url = avatar
        const r = await api.createCharacter(data)
        setCharacters(r.characters)
        last = r.character
        ok++
      } catch { skipped.invalid++ }
    }
    if (ok === 1 && last) toast(tt('char_imported', { name: last.name }), 'success')
    else if (ok > 1) toast(tt('cards_imported', { n: ok }), 'success')
    if (skipped.underage) toast(tt('import_underage', { n: skipped.underage }), 'error')
    if (skipped.invalid) toast(tt(files.length === 1 ? 'png_no_meta' : 'import_invalid_n', { n: skipped.invalid }), 'error')
    if (ok) setView('characters')
  }, [toast])

  const toggleFavorite = useCallback(async (char) => {
    setCharacters((cs) => cs.map((c) => (c.id === char.id ? { ...c, favorite: !c.favorite } : c)))
    try {
      const res = await fetch(`/api/characters/${char.id}/favorite`, {
        method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ favorite: !char.favorite }),
      })
      setCharacters((await res.json()).characters)
    } catch { toast(tRef.current('err_server'), 'error') }
  }, [toast])

  const deleteCharacter = useCallback(async (char) => {
    const tt = tRef.current
    const ok = await confirm({ title: tt('delete_char_title', { name: char.name }), body: tt('delete_char_body'), ok: tt('delete'), danger: true })
    if (!ok) return false
    await api.deleteCharacter(char.id)
    if (sessionRef.current.character_id === char.id) {
      stop()
      const d = await api.bootstrap()
      applyBoot(d)
    } else {
      await refreshLists()
    }
    toast(tt('char_deleted', { name: char.name }), 'success')
    return true
  }, [applyBoot, confirm, refreshLists, stop, toast])

  const resetAll = useCallback(async () => {
    const tt = tRef.current
    const ok = await confirm({ title: tt('reset_confirm_title'), body: tt('reset_confirm_body'), ok: tt('reset_btn'), danger: true })
    if (!ok) return
    stop()
    await api.reset()
    const d = await api.bootstrap()
    applyBoot(d)
    toast(tt('all_reset_done'), 'success')
  }, [applyBoot, confirm, stop, toast])

  const value = {
    ready, bootError, t, lang, settings, account, setAccount, guest, setGuestLang, onAuthed, logout, models, ollama, refreshModels, keys, characters, sessions,
    view, setView, settingsSection, setSettingsSection,
    session, activeCharacter, hasModel, streaming, streamText, swipeTarget, swipe, memoryBusy, summarize, updateMemory, toggleFavorite, importCards,
    toasts, toast, confirmState, confirm,
    updateSettings, saveKey, send, stop, regenerate, editMessage, deleteMessage, clearChat,
    newChat, openSession, deleteSession, saveCharacter, deleteCharacter, resetAll, refreshLists,
  }
  return <Ctx.Provider value={value}>{children}</Ctx.Provider>
}
