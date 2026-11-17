import React, { useEffect, useState } from 'react'
import { AnimatePresence, motion } from 'motion/react'
import { ArrowLeft, ArrowRight, Eye, EyeOff, LoaderCircle, LockKeyhole, X } from 'lucide-react'
import { useStore } from '../store.jsx'
import { api } from '../api.js'
import { hueOf } from '../lib.jsx'
import Logo from './Logo.jsx'
import { Modal } from './ui.jsx'

// Turkish letters → ASCII, spaces → _, only [a-z0-9_]
const TR = { ç: 'c', ğ: 'g', ı: 'i', ö: 'o', ş: 's', ü: 'u', â: 'a', î: 'i', û: 'u' }
export function toUsername(v) {
  return v
    .toLocaleLowerCase('tr-TR')
    .replace(/[çğıöşüâîû]/g, (c) => TR[c])
    .replace(/[\s.\-]+/g, '_')
    .replace(/[^a-z0-9_]/g, '')
    .slice(0, 32)
}

// Demo scenes on the landing page: [who, tr, en]. The cast are the starter cards every new
// account gets (core/starter_cards.py); colours come from hueOf(name), same as their in-app avatars.
const CAST = [
  {
    name: 'Haruki', role: ['Çay evi sahibi', 'Tea house owner'],
    lines: [
      ['ai', '*bir fincan çayı sessizce önüne bırakır* Uzun yürümüşsün. Otur. Çay, yoldan iyidir.', '*sets a cup down without being asked* You\'ve walked a long way. Sit. Tea is better than the road.'],
      ['user', 'Yüzümden mi okunuyor?', 'Is it that obvious?'],
      ['ai', '*hafifçe gülümser* Ayakkabıların anlattı. Yüzün sadece onayladı.', '*a faint smile* Your boots told me. Your face only agreed.'],
    ],
  },
  {
    name: 'Elena', role: ['Gemi mühendisi', 'Starship engineer'],
    lines: [
      ['ai', '*konsolun altından çıkar* Ne zaman kalkacağımızı soracaksan cevap: o anahtarı uzattığında.', '*slides out from under the console* If you\'re asking when we move: when you hand me that wrench.'],
      ['user', '*anahtarı uzatır* Bu sefer ne bozuldu?', '*hands it over* What broke this time?'],
      ['ai', 'Soğutma hattı. Bir de sabrım. Hangisini önce tamir edeyim?', 'The coolant line. And my patience. Which should I fix first?'],
    ],
  },
  {
    name: 'Iris', role: ['Kütüphaneci', 'Librarian'],
    lines: [
      ['ai', '*kitap yığınını neredeyse düşürür* A-ah! Herkes gitti sanıyordum.', '*nearly drops a stack of books* Oh! I thought everyone had left.'],
      ['user', 'Korkma, buradayım. Ne okuyordun?', 'Don\'t worry, I\'m here. What were you reading?'],
      ['ai', '*kitabı göğsüne bastırır* Eski şiirler. Fırtınalı gecelere yakışan türden.', '*hugs the book* Old poetry. The kind that suits stormy nights.'],
    ],
  },
  {
    name: 'Rook', role: ['Paralı asker', 'Mercenary'],
    lines: [
      ['ai', '*bardağından başını kaldırmaz* Önce para. Sonra kimi aradığını anlatırsın.', '*doesn\'t look up from his drink* Coin first. Then tell me who you\'re after.'],
      ['user', 'Kimseyi aramıyorum. Bir yol arkadaşı arıyorum.', 'I\'m not after anyone. I need a travel companion.'],
      ['ai', '*nihayet bakar* …Bu daha pahalı.', '*finally looks up* …That costs more.'],
    ],
  },
]

const FAQ = [
  ['faq1_q', 'faq1_a'],
  ['faq2_q', 'faq2_a'],
  ['faq3_q', 'faq3_a'],
  ['faq4_q', 'faq4_a'],
]

function Rp({ text }) {
  return text.split(/(\*[^*]+\*)/).map((p, i) => (p.startsWith('*') ? <em key={i}>{p.slice(1, -1)}</em> : <span key={i}>{p}</span>))
}

function Face({ c, size = 40 }) {
  return <span className="lp-face" style={{ '--h': hueOf(c.name), width: size, height: size, fontSize: size * 0.4 }}>{c.name[0]}</span>
}

/** A small chat window that plays a scene line by line, with typing dots in between. */
function Stage({ lang }) {
  const { t } = useStore()
  const [who, setWho] = useState(0)
  const [shown, setShown] = useState(0)
  const c = CAST[who]
  const li = lang === 'en' ? 1 : 0
  useEffect(() => { setShown(0) }, [who])
  useEffect(() => {
    const done = shown >= c.lines.length
    const id = setTimeout(() => {
      if (done) setWho((w) => (w + 1) % CAST.length)
      else setShown((n) => n + 1)
    }, done ? 4200 : shown === 0 ? 700 : 1500)
    return () => clearTimeout(id)
  }, [shown, who, c.lines.length])
  const next = c.lines[shown]
  return (
    <div className="lp-stage">
      <aside className="lp-cast" aria-label={t('lp_cast')}>
        <div className="lp-cast-label">{t('lp_cast')}</div>
        {CAST.map((x, i) => (
          <button key={x.name} type="button" className={`lp-cast-item ${i === who ? 'on' : ''}`} onClick={() => setWho(i)}>
            <Face c={x} size={32} />
            <span className="lp-cast-text"><b>{x.name}</b><small>{x.role[li]}</small></span>
          </button>
        ))}
      </aside>
      <div className="lp-chat">
        <div className="lp-chat-top">
          <Face c={c} size={30} />
          <div><div className="lp-chat-name">{c.name}</div><div className="lp-chat-role">{c.role[li]}</div></div>
          <span className="lp-live"><i /> {t('lp_live')}</span>
        </div>
        <div className="lp-chat-body">
          <AnimatePresence initial={false}>
            {c.lines.slice(0, shown).map(([w, ...txt], i) => (
              <motion.div key={`${who}-${i}`} className={`lp-msg ${w}`} initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.25 }}>
                <Rp text={txt[li]} />
              </motion.div>
            ))}
          </AnimatePresence>
          {next && next[0] === 'ai' && <div className="lp-msg ai typing-row"><span className="typing"><i /><i /><i /></span></div>}
        </div>
        <div className="lp-chat-input"><span>{t('type_message')}</span><span className="lp-send"><ArrowRight size={14} strokeWidth={2.2} /></span></div>
      </div>
    </div>
  )
}

const ERRORS = {
  bad_username: 'auth_err_username', bad_password: 'auth_err_password', username_taken: 'auth_err_taken',
  wrong_login: 'auth_err_login', too_many: 'auth_err_too_many', reset_local_only: 'auth_err_reset_local',
  no_such_user: 'auth_err_no_user',
}

function AuthDialog({ mode, setMode, onClose, hasUsers, local }) {
  const { t, onAuthed } = useStore()
  const [name, setName] = useState('')
  const [password, setPassword] = useState('')
  const [repeat, setRepeat] = useState('')
  const [show, setShow] = useState(false)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const register = mode === 'register'
  const reset = mode === 'reset'
  const needsRepeat = register || reset

  const switchTo = (m) => { setMode(m); setError(''); setPassword(''); setRepeat('') }

  async function submit(e) {
    e.preventDefault()
    setError('')
    if (name.length < 3) { setError(t('auth_err_username')); return }
    if (password.length < 4) { setError(t('auth_err_password')); return }
    if (needsRepeat && repeat !== password) { setError(t('auth_err_mismatch')); return }
    setBusy(true)
    try {
      const r = await api.auth(mode, name, password)
      await onAuthed(r.account, mode)
    } catch (err) {
      setError(t(ERRORS[err.message] || 'auth_err_generic'))
    } finally {
      setBusy(false)
    }
  }

  return (
    <Modal open onClose={onClose} width={400} className="auth" labelledBy="auth-title">
      <div className="auth-top">
        <Logo size={34} />
        {reset ? (
          <button type="button" className="auth-back" onClick={() => switchTo('login')}><ArrowLeft size={14} strokeWidth={2} /> {t('auth_back')}</button>
        ) : (
          <div className="auth-tabs" role="tablist">
            {['login', 'register'].map((m) => (
              <button key={m} type="button" role="tab" aria-selected={mode === m} className={mode === m ? 'on' : ''} onClick={() => switchTo(m)}>
                <span>{t(m === 'login' ? 'auth_login_btn' : 'auth_signup')}</span>
              </button>
            ))}
          </div>
        )}
      </div>
      <h2 id="auth-title" className="display auth-title">{t(register ? 'auth_reg_title' : reset ? 'auth_reset_title' : 'auth_login_title')}</h2>
      <p className="auth-sub">{t(register ? 'auth_reg_sub' : reset ? 'auth_reset_sub' : 'auth_login_sub')}</p>

      <form onSubmit={submit} noValidate className="auth-form">
        <label className="field">
          <span className="field-label">{t('auth_username')}</span>
          <input
            className="input" name="username" autoFocus autoComplete="off" autoCapitalize="none" spellCheck={false}
            maxLength={32} value={name} onChange={(e) => setName(toUsername(e.target.value))}
            placeholder={register ? t('auth_username_ph_new') : t('auth_username_ph')}
          />
          {register && <span className="field-hint">{t('auth_username_hint')}</span>}
        </label>
        <label className="field">
          <span className="field-head">
            <span className="field-label">{reset ? t('auth_new_password') : t('auth_password')}</span>
            {mode === 'login' && <button type="button" className="link-btn" onClick={() => switchTo('reset')}>{t('auth_forgot')}</button>}
          </span>
          <span className="input-icon pw">
            <input
              className="input" name="password" type={show ? 'text' : 'password'}
              autoComplete={mode === 'login' ? 'current-password' : 'new-password'}
              maxLength={128} value={password} onChange={(e) => setPassword(e.target.value)} placeholder={t('auth_password_ph')}
            />
            <button type="button" className="icon-btn" aria-label={t(show ? 'auth_hide' : 'auth_show')} onClick={() => setShow((v) => !v)}>
              {show ? <EyeOff size={15} strokeWidth={1.8} /> : <Eye size={15} strokeWidth={1.8} />}
            </button>
          </span>
        </label>
        {needsRepeat && (
          <label className="field">
            <span className="field-label">{reset ? t('auth_new_password_again') : t('auth_password_again')}</span>
            <input className="input" type={show ? 'text' : 'password'} autoComplete="new-password" maxLength={128}
              value={repeat} onChange={(e) => setRepeat(e.target.value)} placeholder={t('auth_again_ph')} />
          </label>
        )}
        {reset && !local && <div className="auth-note">{t('auth_err_reset_local')}</div>}
        {register && !hasUsers && <div className="auth-note">{t('auth_first_note')}</div>}
        <AnimatePresence>
          {error && (
            <motion.div className="alert" role="alert" initial={{ opacity: 0, y: -4 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}>
              <X size={15} strokeWidth={2.2} /><span>{error}</span>
            </motion.div>
          )}
        </AnimatePresence>
        <button className="btn btn-primary btn-lg block" disabled={busy}>
          {busy ? <LoaderCircle className="spin" size={17} /> : <>
            <span>{register ? t('auth_create') : reset ? t('auth_reset_btn') : t('auth_login_btn')}</span>
            <ArrowRight size={17} strokeWidth={2} />
          </>}
        </button>
      </form>
      <div className="auth-private"><LockKeyhole size={13} strokeWidth={1.8} /> {t('auth_private')}</div>
    </Modal>
  )
}

export default function Landing() {
  const { t, lang, setGuestLang, guest } = useStore()
  const [auth, setAuth] = useState(null)

  return (
    <div className="landing">
      <div className="lp-aura" aria-hidden="true" />
      <header className="lp-hdr">
        <span className="lp-brand"><Logo size={28} /><span className="brand-name">Person <i>AI</i></span></span>
        <div className="row gap-8">
          <button type="button" className="lp-lang mono" onClick={() => setGuestLang(lang === 'en' ? 'tr' : 'en')} aria-label={t('language')}>
            {lang === 'en' ? 'TR' : 'EN'}
          </button>
          <button type="button" className="btn btn-soft" onClick={() => setAuth('login')}>{t('auth_login_btn')}</button>
        </div>
      </header>

      <main className="lp-main">
        <section className="lp-hero">
          <motion.div className="lp-faces" initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.5 }}>
            {CAST.map((c, i) => <motion.span key={c.name} animate={{ y: [0, -4, 0] }} transition={{ duration: 3.2, delay: i * 0.4, repeat: Infinity, ease: 'easeInOut' }}><Face c={c} size={38} /></motion.span>)}
            <span className="lp-faces-more mono">+∞</span>
          </motion.div>
          <motion.h1 className="display lp-title" initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.6, delay: 0.05 }}>
            {t('lp_title_1')}<br /><em>{t('lp_title_2')}</em>
          </motion.h1>
          <motion.p className="lp-lead" initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ duration: 0.6, delay: 0.15 }}>{t('lp_lead')}</motion.p>
          <motion.div className="lp-cta" initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ duration: 0.6, delay: 0.25 }}>
            <button type="button" className="btn btn-primary btn-lg" onClick={() => setAuth('login')}>
              <span>{t('auth_login_btn')}</span><ArrowRight size={17} strokeWidth={2} />
            </button>
            <button type="button" className="btn btn-ghost btn-lg" onClick={() => setAuth('register')}>
              {t('lp_cta_new')}
            </button>
          </motion.div>
        </section>

        <motion.section initial={{ opacity: 0, y: 18 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.6, delay: 0.3 }}>
          <Stage lang={lang} />
        </motion.section>

        <section className="lp-faq">
          <h2 className="display lp-faq-title">{t('lp_faq_title')}</h2>
          {FAQ.map(([q, a], i) => (
            <motion.div key={q} className="lp-qa" initial={{ opacity: 0, y: 10 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true, margin: '-40px' }} transition={{ duration: 0.4, delay: i * 0.05 }}>
              <div className="lp-q">{t(q)}</div>
              <div className="lp-a"><Logo size={26} /><p>{t(a)}</p></div>
            </motion.div>
          ))}
        </section>
      </main>

      <footer className="lp-foot">
        <span className="lp-brand"><Logo size={18} /><span className="brand-name sm">Person <i>AI</i></span></span>
        <span>{t('foot_note')}</span>
      </footer>

      {auth && <AuthDialog mode={auth} setMode={setAuth} onClose={() => setAuth(null)} hasUsers={guest.hasUsers} local={guest.local} />}
    </div>
  )
}
