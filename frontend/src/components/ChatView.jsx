import React, { useEffect, useLayoutEffect, useRef, useState } from 'react'
import { AnimatePresence, motion } from 'motion/react'
import {
  ArrowDown, ArrowUp, Brain, Check, ChevronDown, ChevronLeft, ChevronRight, Copy, KeyRound, Menu, Pencil, PenSquare, RefreshCw,
  RotateCcw, Square, Trash2, Eraser, X,
} from 'lucide-react'
import { useStore } from '../store.jsx'
import { RpText, clockTime } from '../lib.jsx'
import { AutoTextarea, Avatar, Button, IconButton, Popover } from './ui.jsx'

function ModelPicker() {
  const { t, models, settings, updateSettings, setView, setSettingsSection, refreshModels } = useStore()
  const [open, setOpen] = useState(false)
  useEffect(() => { if (open) refreshModels() }, [open, refreshModels])
  const current = models.find((m) => m.label === settings.selected_model)
  return (
    <div className="model-picker">
      <button type="button" className="model-pill" onClick={() => setOpen((o) => !o)} aria-label={t('switch_model')}>
        <span className={`dot ${current?.available ? 'ok' : ''}`} />
        <span>{current?.label || settings.selected_model || t('needs_key')}</span>
        <ChevronDown size={13} strokeWidth={2} />
      </button>
      <Popover open={open} onClose={() => setOpen(false)} className="model-menu">
        <div className="popover-label">{t('model_section')}</div>
        {models.map((m, i) => (
          <React.Fragment key={m.label}>
          {m.local && !models[i - 1]?.local && <div className="popover-label sep">{t('local_models')}</div>}
          <button
            type="button"
            disabled={!m.available}
            className={`menu-item ${m.label === settings.selected_model ? 'on' : ''}`}
            onClick={() => { updateSettings({ selected_model: m.label }); setOpen(false) }}
          >
            <span className="menu-item-body">
              <span>{m.label}</span>
              <span className="menu-item-sub">{m.local ? m.detail || t('badge_local') : `${m.provider_label} · ${m.available ? t(m.badge) : t('needs_key')}`}</span>
            </span>
            {m.label === settings.selected_model && <Check size={14} strokeWidth={2.2} />}
          </button>
          </React.Fragment>
        ))}
        <button type="button" className="menu-item subtle" onClick={() => { setSettingsSection('model'); setView('settings'); setOpen(false) }}>
          <KeyRound size={14} strokeWidth={1.8} /> <span>{t('api_keys')}</span>
        </button>
      </Popover>
    </div>
  )
}

function Message({ msg, index, char, isLast, busy }) {
  const { t, lang, settings, regenerate, editMessage, deleteMessage, toast, swipe } = useStore()
  const swipes = msg.swipes?.length || 1
  const swipeIdx = msg.swipe || 0
  const canSwipe = !isUserRole(msg) && isLast && (swipes > 1 || index > 0)
  const [editing, setEditing] = useState(false)
  const [draft, setDraft] = useState(msg.content)
  const isUser = msg.role === 'user'
  const userName = settings.user_name || t('you')

  const copy = async () => {
    try { await navigator.clipboard.writeText(msg.content); toast(t('copied'), 'success') } catch { toast(t('copy_failed'), 'error') }
  }
  const save = () => { setEditing(false); if (draft.trim() && draft !== msg.content) editMessage(index, draft.trim()) }

  return (
    <motion.div
      className={`msg ${isUser ? 'user' : 'ai'}`}
      initial={{ opacity: 0, y: 6 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.22, ease: [0.2, 0.7, 0.2, 1] }}
    >
      {!isUser && <Avatar src={char?.avatar_url} name={char?.name} size={30} className="msg-avatar" />}
      <div className="msg-col">
        <div className="msg-head">
          <span className="msg-name">{isUser ? userName : char?.name}</span>
          <span className="msg-time mono">{clockTime(msg.timestamp, lang)}</span>
        </div>
        {editing ? (
          <div className="msg-edit">
            <AutoTextarea
              value={draft}
              onChange={setDraft}
              minRows={2}
              autoFocus
              onKeyDown={(e) => {
                if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) save()
                if (e.key === 'Escape') { setEditing(false); setDraft(msg.content) }
              }}
            />
            <div className="row gap-6 end">
              <Button variant="ghost" onClick={() => { setEditing(false); setDraft(msg.content) }}>{t('cancel')}</Button>
              <Button variant="primary" onClick={save}>{isUser ? t('save_and_regen') : t('save')}</Button>
            </div>
          </div>
        ) : (
          <div className="msg-body">
            <div className="msg-text"><RpText text={msg.content} /></div>
          </div>
        )}
        {!editing && (
          <div className={`msg-actions ${isLast ? 'last' : ''}`}>
            {canSwipe && (
              <div className="swipe-nav">
                <IconButton icon={ChevronLeft} label={t('prev_swipe')} size={15} onClick={() => swipe(index, -1)} disabled={busy || swipeIdx === 0} />
                <span className="mono">{swipeIdx + 1}/{swipes}</span>
                <IconButton icon={ChevronRight} label={t('next_swipe')} size={15} onClick={() => swipe(index, 1)} disabled={busy || (index === 0 && swipeIdx === swipes - 1)} />
              </div>
            )}
            {!canSwipe && swipes > 1 && <span className="swipe-static mono">{swipeIdx + 1}/{swipes}</span>}
            <IconButton icon={Copy} label={t('copy')} size={14} onClick={copy} />
            {!isUser && index > 0 && <IconButton icon={RotateCcw} label={t('regenerate')} size={14} onClick={() => regenerate(index)} disabled={busy} />}
            <IconButton icon={Pencil} label={t('edit')} size={14} onClick={() => { setDraft(msg.content); setEditing(true) }} disabled={busy} />
            <IconButton icon={Trash2} label={t('delete')} size={14} className="danger" onClick={() => deleteMessage(index)} disabled={busy} />
          </div>
        )}
      </div>
      {isUser && settings.user_avatar_url && <Avatar src={settings.user_avatar_url} name={userName} size={30} className="msg-avatar" />}
    </motion.div>
  )
}

const isUserRole = (m) => m.role === 'user'

function MemoryPanel({ open, onClose }) {
  const { t, session, settings, memoryBusy, summarize, updateMemory } = useStore()
  const mem = session.memory || { summary: '', notes: '', summary_upto: 0 }
  const [summary, setSummary] = useState(mem.summary)
  const [notes, setNotes] = useState(mem.notes)
  const timers = useRef({})
  useEffect(() => { setSummary(mem.summary) }, [mem.summary, session.id])
  useEffect(() => { setNotes(mem.notes) }, [mem.notes, session.id])
  const save = (k, v) => {
    clearTimeout(timers.current[k])
    timers.current[k] = setTimeout(() => updateMemory({ [k]: v }), 600)
  }
  const n = settings.memory_size
  return (
    <AnimatePresence>
      {open && (
        <motion.aside
          key="memory"
          className="memory-panel"
          initial={{ x: 24, opacity: 0 }}
          animate={{ x: 0, opacity: 1 }}
          exit={{ x: 24, opacity: 0 }}
          transition={{ type: 'spring', stiffness: 420, damping: 38 }}
        >
          <div className="memory-head">
            <Brain size={16} strokeWidth={1.8} />
            <h3>{t('memory')}</h3>
            <span className="grow" />
            <IconButton icon={X} label={t('close')} onClick={onClose} />
          </div>
          <p className="memory-desc">{t('memory_desc', { n })}</p>
          {!session.id ? (
            <div className="memory-unsaved">{t('memory_unsaved')}</div>
          ) : (
            <>
              <div className="field">
                <span className="field-head">
                  <span className="field-label">{t('memory_summary')}</span>
                  {mem.summary_upto > 0 && <span className="field-hint mono">{t('memory_covered', { n: mem.summary_upto })}</span>}
                </span>
                <AutoTextarea
                  value={summary}
                  onChange={(v) => { setSummary(v); save('summary', v) }}
                  minRows={6}
                  maxRows={18}
                  placeholder={t('memory_empty', { n: n + 6 })}
                />
                <span className="field-hint">{t('memory_summary_hint')}</span>
              </div>
              <div className="row gap-6 wrap">
                <Button variant="soft" icon={RefreshCw} onClick={() => summarize(false, { quiet: false })} disabled={memoryBusy} className={memoryBusy ? 'spinning' : ''}>
                  {memoryBusy ? t('memory_busy') : t('memory_update')}
                </Button>
                <Button variant="ghost" onClick={() => summarize(true, { quiet: false })} disabled={memoryBusy}>{t('memory_rebuild')}</Button>
              </div>
              <div className="field">
                <span className="field-label">{t('memory_notes')}</span>
                <AutoTextarea value={notes} onChange={(v) => { setNotes(v); save('notes', v) }} minRows={4} maxRows={12} placeholder={t('memory_notes_hint')} />
              </div>
            </>
          )}
        </motion.aside>
      )}
    </AnimatePresence>
  )
}

function LiveMessage({ char, text }) {
  const { t } = useStore()
  return (
    <div className="msg ai live">
      <Avatar src={char?.avatar_url} name={char?.name} size={30} className="msg-avatar" />
      <div className="msg-col">
        <div className="msg-head">
          <span className="msg-name">{char?.name}</span>
          {!text && <span className="msg-time">{t('generating')}</span>}
        </div>
        <div className="msg-body">
          {text ? (
            <div className="msg-text"><RpText text={text} /><span className="caret" /></div>
          ) : (
            <div className="typing" aria-label={t('generating')}><i /><i /><i /></div>
          )}
        </div>
      </div>
    </div>
  )
}

function EmptyState({ char }) {
  const { t } = useStore()
  if (!char) return null
  const traits = char.traits || ''
  return (
    <motion.div className="empty" initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.4 }}>
      <Avatar src={char.avatar_url} name={char.name} size={88} ring />
      <h1 className="display">{char.name}</h1>
      {traits && <p className="empty-traits">{traits.length > 160 ? traits.slice(0, 160).trimEnd() + '…' : traits}</p>}
      <p className="empty-greet">“{char.greeting || t('greeting_default', { name: char.name })}”</p>
      {!!char.tags?.length && (
        <div className="tags center">{char.tags.slice(0, 5).map((x) => <span key={x} className="tag">{x}</span>)}</div>
      )}
    </motion.div>
  )
}

function Composer() {
  const { t, send, stop, streaming, hasModel, setView, setSettingsSection, session } = useStore()
  const [text, setText] = useState('')
  const ref = useRef(null)
  useEffect(() => { ref.current?.querySelector('textarea')?.focus() }, [session.id, session.character_id])
  const submit = async () => {
    if (streaming || !text.trim()) return
    const v = text
    setText('')
    const ok = await send(v)
    if (!ok) setText(v)
  }
  return (
    <div className="composer-wrap">
      {!hasModel && (
        <div className="composer-banner">
          <KeyRound size={14} strokeWidth={1.8} />
          <span>{t('no_key_hint')}</span>
          <Button variant="soft" onClick={() => { setSettingsSection('model'); setView('settings') }}>{t('go_settings')}</Button>
        </div>
      )}
      <div className="composer" ref={ref}>
        <AutoTextarea
          value={text}
          onChange={setText}
          minRows={1}
          maxRows={8}
          placeholder={t('type_message')}
          onKeyDown={(e) => {
            if (e.key === 'Enter' && !e.shiftKey && !e.nativeEvent.isComposing) { e.preventDefault(); submit() }
          }}
        />
        {streaming ? (
          <button type="button" className="send stop" onClick={stop} aria-label={t('stop')} data-tip={t('stop')}>
            <Square size={13} fill="currentColor" strokeWidth={0} />
          </button>
        ) : (
          <button type="button" className="send" onClick={submit} disabled={!text.trim()} aria-label={t('send')} data-tip={t('send')}>
            <ArrowUp size={17} strokeWidth={2.2} />
          </button>
        )}
      </div>
      <div className="composer-hint">{t('composer_hint')}</div>
    </div>
  )
}

export default function ChatView({ onMenu }) {
  const { t, session, activeCharacter: char, streaming, streamText, swipeTarget, clearChat, newChat, settings, memoryBusy } = useStore()
  const [memOpen, setMemOpen] = useState(false)
  const hasMemory = !!(session.memory?.summary || session.memory?.notes)
  const scrollRef = useRef(null)
  const stick = useRef(true)
  const [showDown, setShowDown] = useState(false)
  const msgs = session.messages

  const onScroll = () => {
    const el = scrollRef.current
    const dist = el.scrollHeight - el.scrollTop - el.clientHeight
    stick.current = dist < 120
    setShowDown(dist > 220)
  }
  const toBottom = (smooth) => {
    const el = scrollRef.current
    if (el) el.scrollTo({ top: el.scrollHeight, behavior: smooth ? 'smooth' : 'auto' })
  }
  useLayoutEffect(() => { stick.current = true; toBottom(false) }, [session.id, session.character_id])
  useLayoutEffect(() => { if (stick.current) toBottom(false) }, [msgs.length, streamText, streaming])

  const bg = settings.chat_background_url

  return (
    <section className="chat">
      <header className="topbar">
        <IconButton icon={Menu} label="Menu" className="only-mobile" onClick={onMenu} />
        <div className="topbar-id">
          <Avatar src={char?.avatar_url} name={char?.name} size={34} />
          <div className="topbar-text">
            <div className="topbar-name">{char?.name}</div>
            <ModelPicker />
          </div>
        </div>
        <div className="topbar-actions">
          <button
            type="button"
            className={`mem-pill ${memOpen ? 'on' : ''} ${memoryBusy ? 'busy' : ''}`}
            onClick={() => setMemOpen((o) => !o)}
            aria-pressed={memOpen}
            data-tip={memoryBusy ? t('memory_busy') : t('memory_tip')}
          >
            <Brain size={15} strokeWidth={1.8} />
            <span className="mem-label">{t('memory')}</span>
            {hasMemory && <span className="mem-dot" />}
          </button>
          <span className="topbar-sep" />
          <IconButton icon={Eraser} label={t('clear_chat')} onClick={clearChat} disabled={!msgs.length} />
          <IconButton icon={PenSquare} label={t('new_chat')} onClick={() => newChat(char)} />
        </div>
      </header>

      <div className={`chat-stage ${bg ? 'has-bg' : ''}`}>
        {bg && <div className="chat-bg" style={{ backgroundImage: `url("${bg.replace(/"/g, '%22')}")` }} />}
        <div className="chat-scroll" ref={scrollRef} onScroll={onScroll}>
          <div className="thread">
            {!msgs.length && !streaming && <EmptyState char={char} />}
            {msgs.map((m, i) => (streaming && swipeTarget === i
              ? <LiveMessage key="live" char={char} text={streamText} />
              : <Message key={`${session.id}-${i}-${m.timestamp}`} msg={m} index={i} char={char} isLast={i === msgs.length - 1} busy={streaming} />
            ))}
            {streaming && swipeTarget == null && <LiveMessage char={char} text={streamText} />}
          </div>
        </div>
        <AnimatePresence>
          {showDown && (
            <motion.button
              type="button"
              className="to-bottom"
              onClick={() => toBottom(true)}
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: 8 }}
              aria-label={t('scroll_down')}
            >
              <ArrowDown size={16} strokeWidth={2} />
            </motion.button>
          )}
        </AnimatePresence>
      </div>
      <Composer />
      <MemoryPanel open={memOpen} onClose={() => setMemOpen(false)} />
    </section>
  )
}
