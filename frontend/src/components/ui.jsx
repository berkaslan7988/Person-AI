import React, { useEffect, useLayoutEffect, useRef, useState } from 'react'
import { AnimatePresence, motion } from 'motion/react'
import { AlertTriangle, CheckCircle2, ImagePlus, Info, Link2, Sparkles, X, XCircle } from 'lucide-react'
import { useStore } from '../store.jsx'
import { hueOf, imageToDataUrl, initials } from '../lib.jsx'

export function Avatar({ src, name, size = 36, className = '', ring = false }) {
  const [broken, setBroken] = useState(false)
  useEffect(() => setBroken(false), [src])
  const style = { width: size, height: size, fontSize: Math.max(11, size * 0.38) }
  if (src && !broken) {
    return (
      <span className={`avatar ${ring ? 'ring' : ''} ${className}`} style={style}>
        <img src={src} alt="" onError={() => setBroken(true)} draggable={false} />
      </span>
    )
  }
  const h = hueOf(name)
  return (
    <span
      className={`avatar fallback ${ring ? 'ring' : ''} ${className}`}
      style={{ ...style, '--h': h }}
      aria-hidden
    >
      {initials(name)}
    </span>
  )
}

export function IconButton({ icon: Icon, label, onClick, className = '', size = 16, active, ...rest }) {
  return (
    <button
      type="button"
      className={`icon-btn ${active ? 'active' : ''} ${className}`}
      onClick={onClick}
      aria-label={label}
      data-tip={label}
      {...rest}
    >
      <Icon size={size} strokeWidth={1.75} />
    </button>
  )
}

export function Button({ children, variant = 'ghost', icon: Icon, className = '', ...rest }) {
  return (
    <button type="button" className={`btn btn-${variant} ${className}`} {...rest}>
      {Icon && <Icon size={15} strokeWidth={1.9} />}
      {children && <span>{children}</span>}
    </button>
  )
}

export function Segmented({ value, options, onChange }) {
  return (
    <div className="segmented" role="radiogroup">
      {options.map((o) => (
        <button
          key={o.value}
          type="button"
          role="radio"
          aria-checked={value === o.value}
          className={value === o.value ? 'on' : ''}
          onClick={() => onChange(o.value)}
        >
          {value === o.value && <motion.span layoutId={`seg-${options.map((x) => x.value).join()}`} className="seg-pill" transition={{ type: 'spring', stiffness: 500, damping: 38 }} />}
          {o.icon && <o.icon size={14} strokeWidth={1.9} />}
          <span>{o.label}</span>
        </button>
      ))}
    </div>
  )
}

export function Field({ label, hint, children, aside }) {
  return (
    <label className="field">
      {(label || aside) && (
        <span className="field-head">
          <span className="field-label">{label}</span>
          {aside}
        </span>
      )}
      {children}
      {hint && <span className="field-hint">{hint}</span>}
    </label>
  )
}

export function AutoTextarea({ value, onChange, minRows = 2, maxRows = 14, className = '', ...rest }) {
  const ref = useRef(null)
  useLayoutEffect(() => {
    const el = ref.current
    if (!el) return
    el.style.height = 'auto'
    const lh = parseFloat(getComputedStyle(el).lineHeight) || 20
    const pad = el.offsetHeight - el.clientHeight + parseFloat(getComputedStyle(el).paddingTop) + parseFloat(getComputedStyle(el).paddingBottom)
    const h = Math.min(Math.max(el.scrollHeight, minRows * lh + pad), maxRows * lh + pad)
    el.style.height = h + 'px'
    el.style.overflowY = el.scrollHeight > h ? 'auto' : 'hidden'
  }, [value, minRows, maxRows])
  return (
    <textarea
      ref={ref}
      rows={minRows}
      value={value}
      onChange={(e) => onChange(e.target.value)}
      className={`input textarea ${className}`}
      {...rest}
    />
  )
}

export function Range({ label, desc, value, min, max, step, onChange, format = (v) => v }) {
  const pct = ((value - min) / (max - min)) * 100
  return (
    <div className="range">
      <div className="range-head">
        <div>
          <div className="field-label">{label}</div>
          {desc && <div className="field-hint">{desc}</div>}
        </div>
        <output className="mono range-val">{format(value)}</output>
      </div>
      <input
        type="range"
        min={min}
        max={max}
        step={step}
        value={value}
        style={{ '--pct': pct + '%' }}
        onChange={(e) => onChange(parseFloat(e.target.value))}
      />
    </div>
  )
}

/** URL input + file picker + optional AI generate, with preview. */
export function ImageInput({ value, onChange, name, round = true, maxSize = 384, onGenerate, generating }) {
  const { t, toast } = useStore()
  const fileRef = useRef(null)
  const isData = value?.startsWith('data:')
  const pick = async (e) => {
    const f = e.target.files?.[0]
    e.target.value = ''
    if (!f) return
    try {
      onChange(await imageToDataUrl(f, maxSize))
    } catch {
      toast(t('invalid_format'), 'error')
    }
  }
  return (
    <div className={`image-input ${round ? 'round' : 'wide'}`}>
      <div className="image-preview">
        {round ? (
          <Avatar src={value} name={name} size={64} />
        ) : value ? (
          <img src={value} alt="" />
        ) : (
          <ImagePlus size={20} strokeWidth={1.5} />
        )}
        {generating && <span className="shimmer" />}
      </div>
      <div className="image-controls">
        <div className="input-icon">
          <Link2 size={14} strokeWidth={1.75} />
          <input
            className="input"
            value={isData ? '' : value || ''}
            placeholder={isData ? '• ' + t('pick_file') : t('avatar_url_hint')}
            onChange={(e) => onChange(e.target.value)}
          />
        </div>
        <div className="row gap-6 wrap">
          <Button icon={ImagePlus} variant="soft" onClick={() => fileRef.current?.click()}>{t('pick_file')}</Button>
          {onGenerate && (
            <Button icon={Sparkles} variant="soft" onClick={onGenerate} disabled={generating}>
              {generating ? t('generating_avatar') : t('generate_avatar')}
            </Button>
          )}
          {value && <Button icon={X} variant="ghost" onClick={() => onChange('')}>{t('remove')}</Button>}
        </div>
        <input ref={fileRef} type="file" accept="image/*" hidden onChange={pick} />
      </div>
    </div>
  )
}

export function Modal({ open, onClose, children, width = 560, className = '', labelledBy }) {
  useEffect(() => {
    if (!open) return
    const onKey = (e) => e.key === 'Escape' && onClose?.()
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [open, onClose])
  return (
    <AnimatePresence>
      {open && (
        <motion.div
          key="modal-backdrop"
          className="modal-backdrop"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          transition={{ duration: 0.18 }}
          onMouseDown={(e) => e.target === e.currentTarget && onClose?.()}
        >
          <motion.div
            role="dialog"
            aria-modal="true"
            aria-labelledby={labelledBy}
            className={`modal ${className}`}
            style={{ maxWidth: width }}
            initial={{ opacity: 0, y: 14, scale: 0.985 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 8, scale: 0.99 }}
            transition={{ type: 'spring', stiffness: 420, damping: 34 }}
          >
            {children}
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  )
}

export function ConfirmHost() {
  const { confirmState: c, t } = useStore()
  return (
    <Modal open={!!c} onClose={() => c?.resolve(false)} width={420} className="confirm">
      {c && (
        <>
          <div className={`confirm-icon ${c.danger ? 'danger' : ''}`}>
            <AlertTriangle size={18} strokeWidth={1.8} />
          </div>
          <h3 className="confirm-title">{c.title}</h3>
          {c.body && <p className="confirm-body">{c.body}</p>}
          <div className="modal-actions">
            <Button variant="ghost" onClick={() => c.resolve(false)}>{t('cancel')}</Button>
            <Button variant={c.danger ? 'danger' : 'primary'} onClick={() => c.resolve(true)} autoFocus>
              {c.ok}
            </Button>
          </div>
        </>
      )}
    </Modal>
  )
}

export function Toasts() {
  const { toasts } = useStore()
  const icons = { success: CheckCircle2, error: XCircle, info: Info }
  return (
    <div className="toasts" aria-live="polite">
      <AnimatePresence initial={false}>
        {toasts.map((x) => {
          const I = icons[x.kind] || Info
          return (
            <motion.div
              key={x.id}
              layout
              className={`toast ${x.kind}`}
              initial={{ opacity: 0, y: 12, scale: 0.97 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              exit={{ opacity: 0, y: 6, scale: 0.98, transition: { duration: 0.15 } }}
              transition={{ type: 'spring', stiffness: 500, damping: 36 }}
            >
              <I size={15} strokeWidth={2} />
              <span>{x.text}</span>
            </motion.div>
          )
        })}
      </AnimatePresence>
    </div>
  )
}

export function Popover({ open, onClose, children, className = '' }) {
  const ref = useRef(null)
  useEffect(() => {
    if (!open) return
    const down = (e) => !ref.current?.contains(e.target) && onClose()
    const key = (e) => e.key === 'Escape' && onClose()
    setTimeout(() => window.addEventListener('mousedown', down), 0)
    window.addEventListener('keydown', key)
    return () => { window.removeEventListener('mousedown', down); window.removeEventListener('keydown', key) }
  }, [open, onClose])
  return (
    <AnimatePresence>
      {open && (
        <motion.div
          key="popover"
          ref={ref}
          className={`popover ${className}`}
          initial={{ opacity: 0, y: -4, scale: 0.98 }}
          animate={{ opacity: 1, y: 0, scale: 1 }}
          exit={{ opacity: 0, y: -4, scale: 0.98, transition: { duration: 0.12 } }}
          transition={{ type: 'spring', stiffness: 520, damping: 34 }}
        >
          {children}
        </motion.div>
      )}
    </AnimatePresence>
  )
}
