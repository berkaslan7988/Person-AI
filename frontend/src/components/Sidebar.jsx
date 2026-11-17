import React, { useEffect, useMemo, useState } from 'react'
import { LogOut, MessageCircle, Moon, PenSquare, Search, Settings2, Sun, Trash2, Users, X } from 'lucide-react'
import { useStore } from '../store.jsx'
import { api } from '../api.js'
import { relTime } from '../lib.jsx'
import { Avatar, IconButton } from './ui.jsx'
import Logo from './Logo.jsx'

function Highlight({ text, q }) {
  if (!q) return text
  const i = text.toLowerCase().indexOf(q.toLowerCase())
  if (i < 0) return text
  return (
    <>
      {text.slice(0, i)}
      <mark>{text.slice(i, i + q.length)}</mark>
      {text.slice(i + q.length)}
    </>
  )
}

export default function Sidebar({ onNavigate }) {
  const {
    t, lang, view, setView, sessions, characters, session, activeCharacter, newChat, openSession,
    deleteSession, settings, updateSettings, setSettingsSection, account, logout,
  } = useStore()
  const [q, setQ] = useState('')
  const [results, setResults] = useState(null)

  useEffect(() => {
    const query = q.trim()
    if (!query) { setResults(null); return }
    const id = setTimeout(async () => {
      try { setResults((await api.search(query)).results) } catch { setResults([]) }
    }, 180)
    return () => clearTimeout(id)
  }, [q])

  const charById = useMemo(() => Object.fromEntries(characters.map((c) => [c.id, c])), [characters])
  const go = (v) => { setView(v); onNavigate?.() }
  const isDark = document.documentElement.dataset.theme !== 'light'

  const nav = [
    { id: 'chat', icon: MessageCircle, label: t('nav_chat') },
    { id: 'characters', icon: Users, label: t('nav_characters') },
    { id: 'settings', icon: Settings2, label: t('nav_settings') },
  ]

  return (
    <aside className="sidebar">
      <div className="brand">
        <Logo size={26} className="brand-mark" />
        <span className="brand-name">Person <i>AI</i></span>
      </div>

      <button type="button" className="new-chat" onClick={() => { newChat(activeCharacter, true); onNavigate?.() }}>
        <PenSquare size={15} strokeWidth={1.8} />
        <span>{t('new_chat')}</span>
        {activeCharacter && <Avatar src={activeCharacter.avatar_url} name={activeCharacter.name} size={20} />}
      </button>

      <div className="search">
        <Search size={14} strokeWidth={1.8} />
        <input value={q} onChange={(e) => setQ(e.target.value)} placeholder={t('search_placeholder')} />
        {q && <IconButton icon={X} label={t('close')} size={13} onClick={() => setQ('')} />}
      </div>

      <nav className="nav">
        {nav.map((n) => (
          <button key={n.id} type="button" className={`nav-item ${view === n.id ? 'on' : ''}`} onClick={() => go(n.id)}>
            <n.icon size={16} strokeWidth={1.8} />
            <span>{n.label}</span>
          </button>
        ))}
      </nav>

      <div className="side-section">
        <div className="side-label">{results ? `${t('search_placeholder').replace('…', '')} · ${results.length}` : t('recent_chats')}</div>
        <div className="side-list">
          {results ? (
            results.length ? results.map((r, i) => (
              <button key={i} type="button" className="side-item result" onClick={() => { openSession(r.session_id); onNavigate?.() }}>
                <Avatar src={charById[r.character_id]?.avatar_url} name={r.character_name} size={22} />
                <span className="side-item-body">
                  <span className="side-item-title">{r.character_name}<span className="dim"> · {r.role === 'user' ? t('you') : r.character_name}</span></span>
                  <span className="side-item-snippet"><Highlight text={r.snippet} q={q.trim()} /></span>
                </span>
              </button>
            )) : <div className="side-empty">{t('no_results')}</div>
          ) : sessions.length ? sessions.map((s) => (
            <div key={s.id} className={`side-item ${session.id === s.id ? 'on' : ''}`}>
              <button type="button" className="side-item-main" onClick={() => { openSession(s.id); onNavigate?.() }}>
                <Avatar src={charById[s.character_id]?.avatar_url} name={s.character_name} size={22} />
                <span className="side-item-body">
                  <span className="side-item-title">{s.title || s.character_name || t('new_chat')}</span>
                  <span className="side-item-meta">{s.character_name} · {relTime(s.updated_at, lang)}</span>
                </span>
              </button>
              <IconButton icon={Trash2} label={t('delete')} size={13} className="side-del" onClick={() => deleteSession(s.id)} />
            </div>
          )) : <div className="side-empty">{t('no_sessions')}</div>}
        </div>
      </div>

      <div className="side-foot">
        <button type="button" className="me" onClick={() => { setSettingsSection('account'); go('settings') }}>
          <Avatar src={settings.user_avatar_url} name={settings.user_name || account?.username || t('you')} size={28} />
          <span className="me-text">
            <span className="me-name">{settings.user_name || account?.username || t('you')}</span>
            {account && <span className="me-user mono">@{account.username}</span>}
          </span>
        </button>
        <IconButton
          icon={isDark ? Sun : Moon}
          label={t('theme')}
          onClick={() => updateSettings({ theme_mode: isDark ? 'light' : 'dark' })}
        />
        <IconButton icon={LogOut} label={t('logout')} onClick={logout} />
      </div>
    </aside>
  )
}
