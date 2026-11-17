import React, { useEffect, useMemo, useRef, useState } from 'react'
import { motion } from 'motion/react'
import { ArrowDownUp, Download, FileUp, Menu, MessageCirclePlus, Play, Plus, Search, Star, Trash2, Users, X } from 'lucide-react'
import { useStore } from '../store.jsx'
import { api } from '../api.js'
import {
  downloadJson, fromSillyTavern, imageToDataUrl, pngCardJson, pollinationsAvatar, readFile, relTime, toSillyTavern, hueOf, initials,
} from '../lib.jsx'
import { AutoTextarea, Avatar, Button, Field, IconButton, ImageInput, Modal } from './ui.jsx'

const blank = { name: '', traits: '', greeting: '', examples: [], tags: [], avatar_url: '', scenario: '', alt_greetings: [] }

function toForm(c) {
  return {
    name: c.name || '',
    traits: c.traits || '',
    greeting: c.greeting || '',
    examples: (c.examples || []).join('\n'),
    tags: (c.tags || []).join(', '),
    avatar_url: c.avatar_url || '',
    scenario: c.scenario || '',
    alt_greetings: [...(c.alt_greetings || [])],
    favorite: !!c.favorite,
  }
}
function fromForm(f) {
  return {
    name: f.name.trim() || 'Unnamed',
    traits: f.traits.trim(),
    greeting: f.greeting.trim(),
    examples: f.examples.split('\n').map((s) => s.trim()).filter(Boolean),
    tags: f.tags.split(',').map((s) => s.trim()).filter(Boolean),
    avatar_url: f.avatar_url.trim(),
    scenario: f.scenario.trim(),
    alt_greetings: f.alt_greetings.map((g) => g.trim()).filter(Boolean),
    favorite: f.favorite,
  }
}

function GreetingsEditor({ value, onChange }) {
  const { t } = useStore()
  return (
    <div className="greetings">
      {value.map((g, i) => (
        <div key={i} className="greeting-item">
          <span className="greeting-num mono">{i + 2}</span>
          <AutoTextarea value={g} onChange={(v) => onChange(value.map((x, j) => (j === i ? v : x)))} minRows={2} />
          <IconButton icon={X} label={t('remove')} size={14} onClick={() => onChange(value.filter((_, j) => j !== i))} />
        </div>
      ))}
      <Button variant="ghost" icon={Plus} onClick={() => onChange([...value, ''])}>{t('add_greeting')}</Button>
    </div>
  )
}

export function useAvatarGenerator() {
  const { t, toast } = useStore()
  const [busy, setBusy] = useState(false)
  const run = async (name, traits, apply) => {
    if (!name.trim() && !traits.trim()) { toast(t('avatar_need_desc'), 'error'); return }
    setBusy(true)
    const url = pollinationsAvatar(name, traits)
    try {
      await new Promise((res, rej) => {
        const img = new Image()
        img.onload = res
        img.onerror = rej
        img.src = url
        setTimeout(rej, 90000)
      })
      apply(url)
      toast(t('avatar_generated'), 'success')
    } catch {
      toast(t('avatar_failed'), 'error')
    } finally {
      setBusy(false)
    }
  }
  return [busy, run]
}

function SessionsTab({ char, onOpen }) {
  const { t, lang, openSession, deleteSession, sessions: allSessions } = useStore()
  const [list, setList] = useState(null)
  useEffect(() => {
    api.sessions(char.id).then((r) => setList(r.sessions)).catch(() => setList([]))
  }, [char.id, allSessions])
  if (!list) return <div className="tab-loading" />
  if (!list.length) return <div className="empty-small">{t('no_sessions')}</div>
  return (
    <div className="session-list">
      {list.map((s) => (
        <div key={s.id} className="session-row">
          <button type="button" className="session-main" onClick={() => { openSession(s.id); onOpen() }}>
            <span className="session-title">{s.title || t('new_chat')}</span>
            <span className="session-preview">{s.last_ai_preview || s.preview || t('empty_chat')}</span>
            <span className="session-meta mono">{s.message_count} {t('messages_count')} · {relTime(s.updated_at, lang)}</span>
          </button>
          <div className="session-actions">
            <IconButton icon={Play} label={t('continue_chat')} onClick={() => { openSession(s.id); onOpen() }} />
            <IconButton icon={Trash2} label={t('delete')} className="danger" onClick={() => deleteSession(s.id)} />
          </div>
        </div>
      ))}
    </div>
  )
}

export function CharacterModal({ open, char, initialTab = 'edit', onClose }) {
  const { t, saveCharacter, deleteCharacter, newChat } = useStore()
  const [tab, setTab] = useState(initialTab)
  const [form, setForm] = useState(toForm(char || blank))
  const [saving, setSaving] = useState(false)
  const [genBusy, generate] = useAvatarGenerator()
  useEffect(() => {
    if (open) { setForm(toForm(char || blank)); setTab(char ? initialTab : 'edit') }
  }, [open, char, initialTab])
  const set = (k) => (v) => setForm((f) => ({ ...f, [k]: v }))
  const isEdit = !!char?.id

  const save = async () => {
    setSaving(true)
    try {
      await saveCharacter(fromForm(form), char?.id)
      onClose()
    } finally { setSaving(false) }
  }

  return (
    <Modal open={open} onClose={onClose} width={620} className="char-modal" labelledBy="char-modal-title">
      <div className="modal-head">
        <Avatar src={form.avatar_url} name={form.name || '?'} size={40} />
        <div className="modal-head-text">
          <div className="eyebrow">{isEdit ? t('form_edit') : t('form_create')}</div>
          <h2 id="char-modal-title" className="display sm">{form.name || t('field_name')}</h2>
        </div>
        {isEdit && (
          <Button variant="primary" icon={MessageCirclePlus} onClick={() => { newChat(char); onClose() }}>{t('new_chat')}</Button>
        )}
      </div>

      {isEdit && (
        <div className="tabs">
          {['edit', 'sessions'].map((k) => (
            <button key={k} type="button" className={tab === k ? 'on' : ''} onClick={() => setTab(k)}>
              {t(k === 'edit' ? 'tab_edit' : 'tab_sessions')}
              {tab === k && <span className="tab-line" />}
            </button>
          ))}
        </div>
      )}

      <div className="modal-body">
        {tab === 'edit' ? (
          <div className="form">
            <Field label={t('field_avatar')}>
              <ImageInput
                value={form.avatar_url}
                onChange={set('avatar_url')}
                name={form.name}
                onGenerate={() => generate(form.name, form.traits, set('avatar_url'))}
                generating={genBusy}
              />
            </Field>
            <Field label={t('field_name')}>
              <input className="input" value={form.name} onChange={(e) => set('name')(e.target.value)} autoFocus={!isEdit} />
            </Field>
            <Field label={t('field_traits')}>
              <AutoTextarea value={form.traits} onChange={set('traits')} minRows={4} placeholder={t('field_traits_hint')} />
            </Field>
            <Field label={t('field_scenario')} hint={t('field_scenario_hint')}>
              <AutoTextarea value={form.scenario} onChange={set('scenario')} minRows={2} />
            </Field>
            <Field label={t('field_greeting')} hint={t('field_greeting_hint')}>
              <AutoTextarea value={form.greeting} onChange={set('greeting')} minRows={2} />
            </Field>
            <Field label={t('field_alt_greetings')} hint={t('field_alt_greetings_hint')}>
              <GreetingsEditor value={form.alt_greetings} onChange={set('alt_greetings')} />
            </Field>
            <Field label={t('field_examples')} hint={t('field_examples_hint')}>
              <AutoTextarea value={form.examples} onChange={set('examples')} minRows={3} className="mono-ish" />
            </Field>
            <Field label={t('field_tags')}>
              <input className="input" value={form.tags} onChange={(e) => set('tags')(e.target.value)} placeholder={t('field_tags_hint')} />
            </Field>
          </div>
        ) : (
          <SessionsTab char={char} onOpen={onClose} />
        )}
      </div>

      {tab === 'edit' && (
        <div className="modal-foot">
          {isEdit && (
            <>
              <IconButton icon={Trash2} label={t('delete')} className="danger" onClick={async () => { if (await deleteCharacter(char)) onClose() }} />
              <IconButton
                icon={Download}
                label={t('export_card')}
                onClick={() => downloadJson(toSillyTavern(fromForm(form)), `${form.name || 'character'}_v2.json`)}
              />
            </>
          )}
          <span className="grow" />
          <Button variant="ghost" onClick={onClose}>{t('cancel')}</Button>
          <Button variant="primary" onClick={save} disabled={saving}>{t('save')}</Button>
        </div>
      )}
    </Modal>
  )
}

function CharacterCard({ c, onOpen, i }) {
  const { t, lang, newChat, openSession, toggleFavorite } = useStore()
  const [broken, setBroken] = useState(false)
  useEffect(() => setBroken(false), [c.avatar_url])
  return (
    <motion.article
      className="card"
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.35, delay: Math.min(i * 0.035, 0.3), ease: [0.2, 0.7, 0.2, 1] }}
      onClick={onOpen}
    >
      <div className="card-media" style={{ '--h': hueOf(c.name) }}>
        {c.avatar_url && !broken ? (
          <img src={c.avatar_url} alt="" onError={() => setBroken(true)} loading="lazy" />
        ) : (
          <span className="card-initials">{initials(c.name)}</span>
        )}
        <div className="card-shade" />
        <button
          type="button"
          className={`card-fav ${c.favorite ? 'on' : ''}`}
          onClick={(e) => { e.stopPropagation(); toggleFavorite(c) }}
          aria-label={t(c.favorite ? 'unfavorite' : 'favorite')}
          data-tip={t(c.favorite ? 'unfavorite' : 'favorite')}
        >
          <Star size={15} strokeWidth={1.9} fill={c.favorite ? 'currentColor' : 'none'} />
        </button>
        <div className="card-name">
          <h3 className="display sm">{c.name}</h3>
          {!!c.tags?.length && <div className="tags">{c.tags.slice(0, 3).map((x) => <span key={x} className="tag on-media">{x}</span>)}</div>}
        </div>
      </div>
      <div className="card-body">
        <p className="card-traits">{c.traits}</p>
        <div className="card-foot">
          <span className="card-last">
            {c.last_session ? (
              <>{c.session_count} {t(c.session_count === 1 ? 'session_count_one' : 'sessions_count')} · {relTime(c.last_session.updated_at, lang)}</>
            ) : t('new_chat')}
          </span>
          <div className="row gap-4" onClick={(e) => e.stopPropagation()}>
            {c.last_session && <IconButton icon={Play} label={t('continue_chat')} onClick={() => openSession(c.last_session.id)} />}
            <Button variant="soft" icon={MessageCirclePlus} onClick={() => newChat(c)}>{t('start_chat')}</Button>
          </div>
        </div>
      </div>
    </motion.article>
  )
}

export default function CharactersView({ onMenu }) {
  const { t, lang, characters, importCards } = useStore()
  const [modal, setModal] = useState({ open: false, char: null })
  const fileRef = useRef(null)
  const saved = (() => { try { return JSON.parse(localStorage.getItem('pai.gallery') || '{}') } catch { return {} } })()
  const [q, setQ] = useState('')
  const [sort, setSort] = useState(saved.sort || 'recent')
  const [tags, setTags] = useState([])
  const [favOnly, setFavOnly] = useState(false)
  useEffect(() => { try { localStorage.setItem('pai.gallery', JSON.stringify({ sort })) } catch { /* ignore */ } }, [sort])

  const allTags = useMemo(() => {
    const count = {}
    for (const c of characters) for (const tag of c.tags || []) { const k = tag.toLowerCase(); count[k] = count[k] || { tag, n: 0 }; count[k].n++ }
    return Object.values(count).sort((a, b) => b.n - a.n || a.tag.localeCompare(b.tag))
  }, [characters])

  const shown = useMemo(() => {
    const needle = q.trim().toLocaleLowerCase()
    let list = characters.filter((c) => {
      if (favOnly && !c.favorite) return false
      const ct = (c.tags || []).map((x) => x.toLowerCase())
      if (tags.some((tg) => !ct.includes(tg.toLowerCase()))) return false
      if (!needle) return true
      return [c.name, c.traits, c.scenario, ...(c.tags || [])].join(' ').toLocaleLowerCase().includes(needle)
    })
    const last = (c) => c.last_session?.updated_at || ''
    const by = {
      recent: (a, b) => last(b).localeCompare(last(a)) || b.id - a.id,
      popular: (a, b) => (b.message_count || 0) - (a.message_count || 0) || b.id - a.id,
      new: (a, b) => b.id - a.id,
      name: (a, b) => a.name.localeCompare(b.name, lang),
    }[sort]
    list = [...list].sort((a, b) => (b.favorite - a.favorite) || by(a, b))
    return list
  }, [characters, q, tags, favOnly, sort, lang])
  const filtered = q || tags.length || favOnly
  const toggleTag = (tag) => setTags((ts) => (ts.includes(tag) ? ts.filter((x) => x !== tag) : [...ts, tag]))

  const importFile = async (e) => {
    const files = [...(e.target.files || [])]
    e.target.value = ''
    await importCards(files)
  }

  return (
    <section className="page">
      <header className="topbar page-top">
        <IconButton icon={Menu} label="Menu" className="only-mobile" onClick={onMenu} />
        <span className="grow" />
      </header>
      <div className="page-scroll">
        <div className="page-inner wide">
          <div className="page-head">
            <div>
              <h1 className="display">{t('characters_title')}</h1>
              <p className="page-sub">{t('characters_sub')}</p>
            </div>
            <div className="row gap-8 wrap">
              <Button variant="soft" icon={FileUp} onClick={() => fileRef.current?.click()} data-tip={t('import_hint')}>{t('import_card')}</Button>
              <Button variant="primary" icon={Plus} onClick={() => setModal({ open: true, char: null })}>{t('new_character')}</Button>
              <input ref={fileRef} type="file" multiple accept=".json,.png,application/json,image/png" hidden onChange={importFile} />
            </div>
          </div>

          <div className="gallery-tools">
            <div className="search gallery-search">
              <Search size={14} strokeWidth={1.8} />
              <input value={q} onChange={(e) => setQ(e.target.value)} placeholder={t('search_characters')} />
              {q && <IconButton icon={X} label={t('close')} size={13} onClick={() => setQ('')} />}
            </div>
            <label className="sort">
              <ArrowDownUp size={14} strokeWidth={1.8} />
              <select value={sort} onChange={(e) => setSort(e.target.value)}>
                {['recent', 'popular', 'new', 'name'].map((k) => <option key={k} value={k}>{t('sort_' + k)}</option>)}
              </select>
            </label>
          </div>
          <div className="chips">
            <button type="button" className={`chip ${!filtered ? 'on' : ''}`} onClick={() => { setTags([]); setFavOnly(false); setQ('') }}>{t('all')}</button>
            <button type="button" className={`chip ${favOnly ? 'on' : ''}`} onClick={() => setFavOnly((v) => !v)}>
              <Star size={12} strokeWidth={2} fill={favOnly ? 'currentColor' : 'none'} /> {t('favorites')}
            </button>
            {allTags.map(({ tag, n }) => (
              <button key={tag} type="button" className={`chip ${tags.includes(tag) ? 'on' : ''}`} onClick={() => toggleTag(tag)}>
                {tag}<span className="chip-n mono">{n}</span>
              </button>
            ))}
          </div>

          {characters.length && !shown.length ? (
            <div className="empty-small col">
              <span>{t('no_match')}</span>
              <Button variant="soft" onClick={() => { setTags([]); setFavOnly(false); setQ('') }}>{t('clear_filters')}</Button>
            </div>
          ) : characters.length ? (
            <div className="grid">
              {shown.map((c, i) => (
                <CharacterCard key={c.id} c={c} i={i} onOpen={() => setModal({ open: true, char: c })} />
              ))}
            </div>
          ) : (
            <div className="empty-small"><Users size={20} strokeWidth={1.5} /> {t('no_characters')}</div>
          )}
        </div>
      </div>
      <CharacterModal open={modal.open} char={modal.char} onClose={() => setModal((m) => ({ ...m, open: false }))} />
    </section>
  )
}
