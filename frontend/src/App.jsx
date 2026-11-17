import React, { useEffect, useState } from 'react'
import { AnimatePresence, motion } from 'motion/react'
import { FileUp, MessagesSquare, SlidersHorizontal, Users } from 'lucide-react'
import { useStore } from './store.jsx'
import Sidebar from './components/Sidebar.jsx'
import Logo from './components/Logo.jsx'
import Landing from './components/Landing.jsx'
import ChatView from './components/ChatView.jsx'
import CharactersView from './components/Characters.jsx'
import SettingsView from './components/Settings.jsx'
import { Button, ConfirmHost, Modal, Toasts } from './components/ui.jsx'

function Onboarding() {
  const { t, settings, updateSettings } = useStore()
  const [step, setStep] = useState(0)
  const open = settings.onboarding_seen !== '1'
  const steps = [
    { icon: MessagesSquare, title: t('ob1_title'), desc: t('ob1_desc') },
    { icon: Users, title: t('ob2_title'), desc: t('ob2_desc') },
    { icon: SlidersHorizontal, title: t('ob3_title'), desc: t('ob3_desc') },
  ]
  const finish = () => updateSettings({ onboarding_seen: '1' })
  const s = steps[step]
  return (
    <Modal open={open} onClose={finish} width={440} className="onboarding">
      <AnimatePresence mode="wait">
        <motion.div key={step} className="ob-step" initial={{ opacity: 0, x: 14 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: -14 }} transition={{ duration: 0.2 }}>
          <div className="ob-icon"><s.icon size={22} strokeWidth={1.6} /></div>
          <div className="eyebrow mono">0{step + 1} / 03</div>
          <h2 className="display">{s.title}</h2>
          <p>{s.desc}</p>
        </motion.div>
      </AnimatePresence>
      <div className="ob-foot">
        <div className="ob-dots">{steps.map((_, i) => <span key={i} className={i === step ? 'on' : ''} />)}</div>
        <div className="row gap-6">
          <Button variant="ghost" onClick={finish}>{t('ob_skip')}</Button>
          <Button variant="primary" onClick={() => (step < steps.length - 1 ? setStep(step + 1) : finish())}>
            {step < steps.length - 1 ? t('ob_next') : t('ob_start')}
          </Button>
        </div>
      </div>
    </Modal>
  )
}

function Boot({ error }) {
  return (
    <div className="boot">
      <motion.div initial={{ opacity: 0, scale: 0.92 }} animate={{ opacity: 1, scale: 1 }} transition={{ duration: 0.5 }}><Logo size={64} /></motion.div>
      <motion.div className="boot-name" initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1, duration: 0.5 }}>
        Person <i>AI</i>
      </motion.div>
      {error ? <p className="boot-error">{error}</p> : <div className="boot-bar"><span /></div>}
    </div>
  )
}

export default function App() {
  const { ready, bootError, view, importCards, t, account, settings } = useStore()
  const [drawer, setDrawer] = useState(false)
  const [dragging, setDragging] = useState(false)
  useEffect(() => {
    let depth = 0
    const hasFiles = (e) => [...(e.dataTransfer?.types || [])].includes('Files')
    const enter = (e) => { if (!hasFiles(e)) return; e.preventDefault(); depth++; setDragging(true) }
    const over = (e) => { if (hasFiles(e)) e.preventDefault() }
    const leave = (e) => { if (!hasFiles(e)) return; depth = Math.max(0, depth - 1); if (!depth) setDragging(false) }
    const drop = (e) => {
      if (!hasFiles(e)) return
      e.preventDefault(); depth = 0; setDragging(false)
      const files = [...e.dataTransfer.files].filter((f) => /\.(png|json)$/i.test(f.name))
      if (files.length) importCards(files)
    }
    window.addEventListener('dragenter', enter)
    window.addEventListener('dragover', over)
    window.addEventListener('dragleave', leave)
    window.addEventListener('drop', drop)
    return () => {
      window.removeEventListener('dragenter', enter); window.removeEventListener('dragover', over)
      window.removeEventListener('dragleave', leave); window.removeEventListener('drop', drop)
    }
  }, [importCards])
  const [minDelay, setMinDelay] = useState(true)
  useEffect(() => { const id = setTimeout(() => setMinDelay(false), 550); return () => clearTimeout(id) }, [])
  useEffect(() => { setDrawer(false) }, [view])

  if (!ready || minDelay) return <Boot error={bootError} />
  if (!account) return (<><Landing /><ConfirmHost /><Toasts /></>)
  if (!settings) return <Boot error={bootError} />

  const View = { chat: ChatView, characters: CharactersView, settings: SettingsView }[view]
  return (
    <motion.div className={`app ${drawer ? 'drawer-open' : ''}`} initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ duration: 0.35 }}>
      <Sidebar onNavigate={() => setDrawer(false)} />
      <div className="scrim" onClick={() => setDrawer(false)} />
      <main className="main">
        <motion.div
          key={view}
          className="view"
          initial={{ opacity: 0, y: 4 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.2, ease: [0.2, 0.7, 0.2, 1] }}
        >
          <View onMenu={() => setDrawer(true)} />
        </motion.div>
      </main>
      <AnimatePresence>
        {dragging && (
          <motion.div key="drop" className="drop-overlay" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} transition={{ duration: 0.15 }}>
            <div className="drop-box">
              <FileUp size={26} strokeWidth={1.6} />
              <div className="drop-title">{t('drop_title')}</div>
              <div className="drop-sub">{t('drop_sub')}</div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
      <Onboarding />
      <ConfirmHost />
      <Toasts />
    </motion.div>
  )
}
