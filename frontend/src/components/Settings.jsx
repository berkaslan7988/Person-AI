import React, { useEffect, useRef, useState } from 'react'
import { AnimatePresence, motion } from 'motion/react'
import {
  Bot, Check, CircleUser, Database, Download, ExternalLink, Eye, EyeOff, KeyRound, Laptop, Menu, Moon, Palette,
  SlidersHorizontal, Sparkles, Sun, Trash2, Users, Zap, Brain, Gift, Cpu, RefreshCw, Terminal,
  AtSign, LogOut, ShieldCheck, X,
} from 'lucide-react'
import { useStore } from '../store.jsx'
import { AutoTextarea, Avatar, Button, Field, IconButton, ImageInput, Range, Segmented } from './ui.jsx'
import { useAvatarGenerator } from './Characters.jsx'
import { toUsername } from './Landing.jsx'
import { api } from '../api.js'
import { parseTime } from '../lib.jsx'

const ACCENTS = ['', '#8b5cf6', '#3b82f6', '#10b981', '#f59e0b', '#ec4899', '#ef4444']
const DEFAULTS = { temperature: 1.4, top_p: 0.9, frequency_penalty: 0, max_tokens: 2048, memory_size: 20, local_num_ctx: 8192 }

/** Local draft that saves itself (debounced) — returns [value, setValue]. */
function useAutosave(initial, save, delay = 550) {
  const [v, setV] = useState(initial)
  const first = useRef(true)
  const saveRef = useRef(save)
  saveRef.current = save
  useEffect(() => { setV(initial) }, [initial]) // eslint-disable-line
  useEffect(() => {
    if (first.current) { first.current = false; return }
    if (v === initial) return
    const id = setTimeout(() => saveRef.current(v), delay)
    return () => clearTimeout(id)
  }, [v]) // eslint-disable-line
  return [v, setV]
}

function SavedPulse({ tick }) {
  const { t } = useStore()
  return (
    <AnimatePresence>
      {tick > 0 && (
        <motion.span key={tick} className="saved-pulse" initial={{ opacity: 0 }} animate={{ opacity: [0, 1, 1, 0] }} transition={{ duration: 1.8, times: [0, 0.1, 0.75, 1] }}>
          <Check size={12} strokeWidth={2.4} /> {t('saved')}
        </motion.span>
      )}
    </AnimatePresence>
  )
}

function Section({ title, desc, children, aside }) {
  return (
    <section className="set-section">
      <div className="set-section-head">
        <div>
          <h3>{title}</h3>
          {desc && <p>{desc}</p>}
        </div>
        {aside}
      </div>
      <div className="set-section-body">{children}</div>
    </section>
  )
}

// ── Model ─────────────────────────────────────────────────────
function KeyRow({ provider, info }) {
  const { t, saveKey } = useStore()
  const [val, setVal] = useState('')
  const [show, setShow] = useState(false)
  const [busy, setBusy] = useState(false)
  const submit = async (key) => {
    setBusy(true)
    try { await saveKey(provider, key); setVal('') } finally { setBusy(false) }
  }
  return (
    <div className="key-row">
      <div className="key-meta">
        <span className={`dot ${info.set ? 'ok' : ''}`} />
        <span className="key-name">{info.label}</span>
        <span className="key-state mono">
          {info.set ? `${info.hint} · ${t(info.source === 'env' ? 'key_from_env' : 'key_from_app')}` : t('key_missing')}
        </span>
        <a className="key-link" href={info.key_url} target="_blank" rel="noreferrer">{t('get_key')} <ExternalLink size={11} /></a>
      </div>
      <form className="key-input" onSubmit={(e) => { e.preventDefault(); if (val.trim()) submit(val.trim()) }}>
        <div className="input-icon">
          <KeyRound size={14} strokeWidth={1.75} />
          <input
            className="input mono"
            type={show ? 'text' : 'password'}
            value={val}
            onChange={(e) => setVal(e.target.value)}
            placeholder={t('key_placeholder')}
            autoComplete="off"
            spellCheck={false}
          />
          <IconButton icon={show ? EyeOff : Eye} label={show ? 'Hide' : 'Show'} size={14} onClick={() => setShow((s) => !s)} />
        </div>
        <Button variant="primary" type="submit" disabled={!val.trim() || busy}>{t('save')}</Button>
        {info.source === 'app' && <IconButton icon={Trash2} label={t('remove')} className="danger" onClick={() => submit('')} />}
      </form>
    </div>
  )
}

function ModelCards({ list }) {
  const { t, settings, updateSettings } = useStore()
  const badgeIcon = { badge_fast: Zap, badge_smart: Brain, badge_free: Gift, badge_local: Cpu }
  return (
        <div className="model-grid">
          {list.map((m) => {
            const on = m.label === settings.selected_model
            const B = badgeIcon[m.badge] || Sparkles
            return (
              <button
                key={m.label}
                type="button"
                className={`model-card ${on ? 'on' : ''}`}
                disabled={!m.available}
                onClick={() => updateSettings({ selected_model: m.label })}
              >
                <span className="model-radio">{on && <motion.span layoutId="model-dot" className="model-radio-dot" />}</span>
                <span className="model-card-body">
                  <span className="model-card-name">{m.local ? m.id : m.label}</span>
                  <span className="model-card-sub mono">{m.local ? m.detail || 'Ollama' : `${m.provider_label} · ${m.id}`}</span>
                </span>
                <span className={`badge ${m.available ? '' : 'muted'}`}>
                  {m.available ? <><B size={11} strokeWidth={2} /> {t(m.badge)}</> : t('needs_key')}
                </span>
              </button>
            )
          })}
        </div>
  )
}

function LocalModels() {
  const { t, models, ollama, refreshModels } = useStore()
  const [busy, setBusy] = useState(false)
  const local = models.filter((m) => m.local)
  useEffect(() => { refreshModels() }, [refreshModels])
  const refresh = async () => { setBusy(true); await refreshModels(); setBusy(false) }
  return (
    <Section
      title={t('local_models')}
      desc={t('local_models_desc')}
      aside={<Button variant="soft" icon={RefreshCw} onClick={refresh} disabled={busy} className={busy ? 'spinning' : ''}>{t('refresh')}</Button>}
    >
      <div className="ollama-status">
        <span className={`dot ${ollama.running ? 'ok' : ''}`} />
        <span>{ollama.running ? t('ollama_running') : t('ollama_down')}</span>
        {ollama.running && <span className="mono dim">{ollama.url?.replace('http://', '')}</span>}
        {!ollama.running && (
          <a className="key-link" href="https://ollama.com/download" target="_blank" rel="noreferrer">{t('ollama_install')} <ExternalLink size={11} /></a>
        )}
      </div>
      {local.length ? (
        <div className="mt-16"><ModelCards list={local} /></div>
      ) : ollama.running ? (
        <div className="ollama-empty">
          <span>{t('ollama_no_models')}</span>
          <code className="mono"><Terminal size={13} /> ollama pull llama3.1:8b</code>
        </div>
      ) : null}
      {ollama.running && <div className="field-hint mt-8">{t('ollama_hint')}</div>}
    </Section>
  )
}

function ModelSection() {
  const { t, models, keys } = useStore()
  return (
    <>
      <Section title={t('model_section')} desc={t('model_section_desc')}>
        <ModelCards list={models.filter((m) => !m.local)} />
      </Section>
      <LocalModels />
      <Section title={t('api_keys')} desc={t('api_keys_desc')}>
        <div className="key-list">
          {Object.entries(keys).map(([p, info]) => <KeyRow key={p} provider={p} info={info} />)}
        </div>
      </Section>
    </>
  )
}

// ── Character (quick) ─────────────────────────────────────────
function CharacterSection() {
  const { t, activeCharacter: c, saveCharacter, setView } = useStore()
  const [tick, setTick] = useState(0)
  const [genBusy, generate] = useAvatarGenerator()
  const initial = c ? { name: c.name, traits: c.traits, greeting: c.greeting, avatar_url: c.avatar_url } : null
  const key = c ? `${c.id}` : ''
  const [form, setForm] = useState(initial)
  const saveTimer = useRef(null)
  useEffect(() => { setForm(initial) }, [key]) // eslint-disable-line
  if (!c || !form) return null
  const set = (k) => (v) => {
    const next = { ...form, [k]: v }
    setForm(next)
    clearTimeout(saveTimer.current)
    saveTimer.current = setTimeout(async () => {
      await saveCharacter({ ...c, ...next, name: next.name.trim() || c.name }, c.id, { quiet: true })
      setTick((x) => x + 1)
    }, 600)
  }
  return (
    <Section
      title={t('character_section')}
      desc={t('character_section_desc')}
      aside={<div className="row gap-8"><SavedPulse tick={tick} /><Button variant="soft" icon={Users} onClick={() => setView('characters')}>{t('open_characters')}</Button></div>}
    >
      <div className="form">
        <Field label={t('field_avatar')}>
          <ImageInput value={form.avatar_url} onChange={set('avatar_url')} name={form.name} onGenerate={() => generate(form.name, form.traits, set('avatar_url'))} generating={genBusy} />
        </Field>
        <Field label={t('field_name')}>
          <input className="input" value={form.name} onChange={(e) => set('name')(e.target.value)} />
        </Field>
        <Field label={t('field_traits')}>
          <AutoTextarea value={form.traits} onChange={set('traits')} minRows={4} />
        </Field>
        <Field label={t('field_greeting')} hint={t('field_greeting_hint')}>
          <AutoTextarea value={form.greeting} onChange={set('greeting')} minRows={2} />
        </Field>
      </div>
    </Section>
  )
}

// ── Appearance ────────────────────────────────────────────────
function AppearanceSection() {
  const { t, settings, updateSettings } = useStore()
  return (
    <>
      <Section title={t('language')}>
        <Segmented
          value={settings.language}
          onChange={(v) => updateSettings({ language: v })}
          options={[{ value: 'tr', label: 'Türkçe' }, { value: 'en', label: 'English' }]}
        />
      </Section>
      <Section title={t('theme')}>
        <Segmented
          value={settings.theme_mode}
          onChange={(v) => updateSettings({ theme_mode: v })}
          options={[
            { value: 'dark', label: t('dark'), icon: Moon },
            { value: 'light', label: t('light'), icon: Sun },
            { value: 'system', label: t('system'), icon: Laptop },
          ]}
        />
        <div className="field-label mt-16">{t('accent')}</div>
        <div className="swatches">
          {ACCENTS.map((a) => {
            const on = (settings.accent_color || '') === a
            return (
              <button
                key={a || 'default'}
                type="button"
                className={`swatch ${on ? 'on' : ''} ${a ? '' : 'default'}`}
                style={a ? { '--sw': a } : undefined}
                onClick={() => updateSettings({ accent_color: a })}
                aria-label={a || t('accent_default')}
                data-tip={a || t('accent_default')}
              >
                {on && <Check size={13} strokeWidth={2.6} />}
              </button>
            )
          })}
        </div>
      </Section>
      <Section title={t('chat_bg_section')} desc={t('chat_bg_desc')}>
        <ImageInput
          value={settings.chat_background_url}
          onChange={(v) => updateSettings({ chat_background_url: v })}
          round={false}
          maxSize={1800}
        />
      </Section>
    </>
  )
}

// ── Profile ───────────────────────────────────────────────────
function ProfileSection() {
  const { t, settings, updateSettings } = useStore()
  const [tick, setTick] = useState(0)
  const saver = (k) => async (v) => { await updateSettings({ [k]: v.trim() }); setTick((x) => x + 1) }
  const [name, setName] = useAutosave(settings.user_name, saver('user_name'))
  const [persona, setPersona] = useAutosave(settings.user_persona, saver('user_persona'), 800)
  return (
    <Section title={t('user_profile_section')} desc={t('user_profile_desc')} aside={<SavedPulse tick={tick} />}>
      <div className="form">
        <Field label={t('user_avatar_label')}>
          <ImageInput value={settings.user_avatar_url} onChange={(v) => updateSettings({ user_avatar_url: v })} name={name || t('you')} />
        </Field>
        <Field label={t('user_name_label')} hint={t('user_name_hint')}>
          <input className="input" value={name} onChange={(e) => setName(e.target.value)} />
        </Field>
        <Field label={t('user_persona_label')} hint={t('user_persona_desc')}>
          <AutoTextarea value={persona} onChange={setPersona} minRows={4} placeholder={t('user_persona_hint')} />
        </Field>
      </div>
    </Section>
  )
}

// ── Account ───────────────────────────────────────────────────
const ACCOUNT_ERRORS = {
  bad_username: 'auth_err_username', username_taken: 'auth_err_taken', wrong_current: 'pw_err_current',
  bad_password: 'auth_err_password', too_many: 'auth_err_too_many',
}

function AccountSection() {
  const { t, lang, account, setAccount, logout, toast } = useStore()
  const [name, setName] = useState(account?.username || '')
  const [nameErr, setNameErr] = useState('')
  const [nameBusy, setNameBusy] = useState(false)
  const [cur, setCur] = useState('')
  const [pw, setPw] = useState('')
  const [pw2, setPw2] = useState('')
  const [show, setShow] = useState(false)
  const [pwErr, setPwErr] = useState('')
  const [pwBusy, setPwBusy] = useState(false)
  if (!account) return null
  const since = parseTime(account.created_at)?.toLocaleDateString(lang, { day: 'numeric', month: 'long', year: 'numeric' }) || ''

  const saveName = async (e) => {
    e.preventDefault()
    setNameErr('')
    if (name.length < 3) { setNameErr(t('auth_err_username')); return }
    if (name === account.username) return
    setNameBusy(true)
    try {
      const r = await api.rename(name)
      setAccount(r.account)
      toast(t('username_saved'), 'success')
    } catch (err) { setNameErr(t(ACCOUNT_ERRORS[err.message] || 'auth_err_generic')) } finally { setNameBusy(false) }
  }
  const savePw = async (e) => {
    e.preventDefault()
    setPwErr('')
    if (!cur) { setPwErr(t('pw_err_current')); return }
    if (pw.length < 4) { setPwErr(t('auth_err_password')); return }
    if (pw !== pw2) { setPwErr(t('auth_err_mismatch')); return }
    setPwBusy(true)
    try {
      await api.changePassword(cur, pw)
      setCur(''); setPw(''); setPw2('')
      toast(t('password_saved'), 'success')
    } catch (err) { setPwErr(t(ACCOUNT_ERRORS[err.message] || 'auth_err_generic')) } finally { setPwBusy(false) }
  }

  return (
    <>
      <Section title={t('account_section')} desc={t('account_desc')}
        aside={<Button variant="soft" icon={LogOut} onClick={logout}>{t('logout')}</Button>}>
        <div className="account-card">
          <Avatar name={account.username} size={46} />
          <div>
            <div className="account-name mono">@{account.username}</div>
            {since && <div className="field-hint">{t('member_since', { d: since })}</div>}
          </div>
        </div>
      </Section>
      <Section title={t('username_section')} desc={t('username_desc')}>
        <form className="inline-form" onSubmit={saveName} noValidate>
          <div className="input-icon">
            <AtSign size={14} strokeWidth={1.75} />
            <input className="input" value={name} maxLength={32} autoComplete="off" autoCapitalize="none" spellCheck={false}
              onChange={(e) => setName(toUsername(e.target.value))} />
          </div>
          <Button variant="primary" type="submit" disabled={nameBusy || name === account.username}>{t('save')}</Button>
        </form>
        <div className="field-hint mt-8">{t('auth_username_hint')}</div>
        {nameErr && <div className="alert mt-8" role="alert"><X size={15} strokeWidth={2.2} /><span>{nameErr}</span></div>}
      </Section>
      <Section title={t('password_section')} desc={t('password_desc')}>
        <form className="pw-form" onSubmit={savePw} noValidate>
          <Field label={t('password_current')}>
            <div className="input-icon">
              <KeyRound size={14} strokeWidth={1.75} />
              <input className="input" type={show ? 'text' : 'password'} autoComplete="current-password" value={cur} onChange={(e) => setCur(e.target.value)} />
              <IconButton icon={show ? EyeOff : Eye} label={t(show ? 'auth_hide' : 'auth_show')} size={14} onClick={() => setShow((s) => !s)} />
            </div>
          </Field>
          <div className="pw-grid">
            <Field label={t('auth_new_password')}>
              <input className="input" type={show ? 'text' : 'password'} autoComplete="new-password" placeholder={t('auth_password_ph')} value={pw} onChange={(e) => setPw(e.target.value)} />
            </Field>
            <Field label={t('auth_new_password_again')}>
              <input className="input" type={show ? 'text' : 'password'} autoComplete="new-password" placeholder={t('auth_again_ph')} value={pw2} onChange={(e) => setPw2(e.target.value)} />
            </Field>
          </div>
          {pwErr && <div className="alert" role="alert"><X size={15} strokeWidth={2.2} /><span>{pwErr}</span></div>}
          <div><Button variant="primary" type="submit" disabled={pwBusy}>{t('password_section')}</Button></div>
        </form>
      </Section>
    </>
  )
}

// ── Data ──────────────────────────────────────────────────────
function DataSection() {
  const { t, characters, deleteCharacter, resetAll } = useStore()
  return (
    <>
      <Section title={t('saved_characters')}>
        <div className="data-list">
          {characters.map((c) => (
            <div key={c.id} className="data-row">
              <Avatar src={c.avatar_url} name={c.name} size={30} />
              <div className="data-row-body">
                <span className="data-row-name">{c.name}</span>
                <span className="data-row-meta mono">{c.session_count} {t('sessions_count')}</span>
              </div>
              <IconButton icon={Trash2} label={t('delete')} className="danger" onClick={() => deleteCharacter(c)} />
            </div>
          ))}
        </div>
      </Section>
      <Section title={t('export_all')} desc={t('export_all_desc')}>
        <a className="btn btn-soft" href="/api/export" download="person_ai_export.json"><Download size={15} strokeWidth={1.9} /><span>JSON</span></a>
      </Section>
      <section className="set-section danger-zone">
        <div className="set-section-head">
          <div>
            <h3>{t('reset_all')}</h3>
            <p>{t('reset_all_desc')}</p>
          </div>
          <Button variant="danger" icon={Trash2} onClick={resetAll}>{t('reset_btn')}</Button>
        </div>
      </section>
    </>
  )
}

// ── Advanced ──────────────────────────────────────────────────
function AdvancedSection() {
  const { t, settings, updateSettings } = useStore()
  const [local, setLocal] = useState(() => ({ ...DEFAULTS, ...pick(settings) }))
  const timer = useRef(null)
  function pick(s) { return Object.fromEntries(Object.keys(DEFAULTS).map((k) => [k, s[k]])) }
  const set = (k) => (v) => {
    setLocal((l) => ({ ...l, [k]: v }))
    clearTimeout(timer.current)
    timer.current = setTimeout(() => updateSettings({ [k]: v }), 250)
  }
  return (
    <Section
      title={t('advanced_section')}
      desc={t('advanced_desc')}
      aside={<Button variant="ghost" onClick={() => { setLocal(DEFAULTS); updateSettings(DEFAULTS) }}>{t('reset_defaults')}</Button>}
    >
      <div className="ranges">
        <Range label={t('temperature_label')} desc={t('temperature_desc')} value={local.temperature} min={0} max={2} step={0.1} onChange={set('temperature')} format={(v) => v.toFixed(1)} />
        <Range label={t('top_p_label')} desc={t('top_p_desc')} value={local.top_p} min={0} max={1} step={0.05} onChange={set('top_p')} format={(v) => v.toFixed(2)} />
        <Range label={t('fp_label')} desc={t('fp_desc')} value={local.frequency_penalty} min={-2} max={2} step={0.1} onChange={set('frequency_penalty')} format={(v) => (v > 0 ? '+' : '') + v.toFixed(1)} />
        <Range label={t('max_tokens_label')} desc={t('max_tokens_desc')} value={local.max_tokens} min={256} max={8192} step={256} onChange={set('max_tokens')} />
        <Range label={t('context_label')} desc={t('context_desc')} value={local.memory_size} min={4} max={50} step={1} onChange={set('memory_size')} format={(v) => `${v} ${t('messages_count')}`} />
        <Range label={t('local_ctx_label')} desc={t('local_ctx_desc')} value={local.local_num_ctx} min={2048} max={32768} step={1024} onChange={set('local_num_ctx')} format={(v) => `${(v / 1024).toFixed(0)}K ${t('tokens')}`} />
      </div>
    </Section>
  )
}

export default function SettingsView({ onMenu }) {
  const { t, settingsSection: sec, setSettingsSection: setSec } = useStore()
  const items = [
    { id: 'model', icon: Bot, label: t('sec_model') },
    { id: 'character', icon: Sparkles, label: t('sec_character') },
    { id: 'appearance', icon: Palette, label: t('sec_appearance') },
    { id: 'profile', icon: CircleUser, label: t('sec_profile') },
    { id: 'account', icon: ShieldCheck, label: t('sec_account') },
    { id: 'data', icon: Database, label: t('sec_data') },
    { id: 'advanced', icon: SlidersHorizontal, label: t('sec_advanced') },
  ]
  const Body = { model: ModelSection, character: CharacterSection, appearance: AppearanceSection, profile: ProfileSection, account: AccountSection, data: DataSection, advanced: AdvancedSection }[sec] || ModelSection
  const scrollRef = useRef(null)
  useEffect(() => { scrollRef.current?.scrollTo({ top: 0 }) }, [sec])
  return (
    <section className="page">
      <header className="topbar page-top">
        <IconButton icon={Menu} label="Menu" className="only-mobile" onClick={onMenu} />
        <span className="grow" />
      </header>
      <div className="page-scroll" ref={scrollRef}>
        <div className="page-inner left">
          <div className="page-head">
            <div>
              <h1 className="display">{t('nav_settings')}</h1>
              <p className="page-sub">{t('saved_auto')}</p>
            </div>
          </div>
          <div className="settings">
            <nav className="set-nav">
              {items.map((it) => (
                <button key={it.id} type="button" className={sec === it.id ? 'on' : ''} onClick={() => setSec(it.id)}>
                  {sec === it.id && <motion.span layoutId="set-nav-pill" className="set-nav-pill" transition={{ type: 'spring', stiffness: 500, damping: 40 }} />}
                  <it.icon size={15} strokeWidth={1.8} />
                  <span>{it.label}</span>
                </button>
              ))}
            </nav>
            <motion.div
              key={sec}
              className="set-body"
              initial={{ opacity: 0, y: 6 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.2, ease: [0.2, 0.7, 0.2, 1] }}
            >
              <Body />
            </motion.div>
          </div>
        </div>
      </div>
    </section>
  )
}
