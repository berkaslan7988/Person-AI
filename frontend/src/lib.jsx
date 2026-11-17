import React from 'react'

// ── RP markdown: **bold**, *action*, `code` ─────────────────
const RP = /(\*\*([\s\S]+?)\*\*)|(\*([^*\n][^*]*?)\*)|(`([^`\n]+?)`)/g
export function RpText({ text }) {
  const out = []
  let last = 0
  let k = 0
  for (const m of text.matchAll(RP)) {
    if (m.index > last) out.push(text.slice(last, m.index))
    if (m[1]) out.push(<strong key={k++}>{m[2]}</strong>)
    else if (m[3]) out.push(<em key={k++} className="rp-action">{m[4]}</em>)
    else if (m[5]) out.push(<code key={k++}>{m[6]}</code>)
    last = m.index + m[0].length
  }
  if (last < text.length) out.push(text.slice(last))
  return out
}

// ── time ─────────────────────────────────────────────────────
export function parseTime(s) {
  if (!s) return null
  // SQLite "YYYY-MM-DD HH:MM:SS" is UTC; ISO strings carry their own zone (or are local)
  const iso = /^\d{4}-\d\d-\d\d \d\d:\d\d:\d\d$/.test(s) ? s.replace(' ', 'T') + 'Z' : s
  const d = new Date(iso)
  return isNaN(d) ? null : d
}
export function relTime(s, lang) {
  const d = parseTime(s)
  if (!d) return ''
  const diff = (Date.now() - d.getTime()) / 1000
  const rtf = new Intl.RelativeTimeFormat(lang, { numeric: 'auto' })
  if (diff < 45) return lang === 'en' ? 'just now' : 'şimdi'
  if (diff < 3600) return rtf.format(-Math.round(diff / 60), 'minute')
  if (diff < 86400) return rtf.format(-Math.round(diff / 3600), 'hour')
  if (diff < 86400 * 7) return rtf.format(-Math.round(diff / 86400), 'day')
  return d.toLocaleDateString(lang, { day: 'numeric', month: 'short' })
}
export function clockTime(s, lang) {
  const d = parseTime(s)
  return d ? d.toLocaleTimeString(lang, { hour: '2-digit', minute: '2-digit' }) : ''
}

// ── images ───────────────────────────────────────────────────
export function readFile(file, as = 'dataURL') {
  return new Promise((res, rej) => {
    const r = new FileReader()
    r.onload = () => res(r.result)
    r.onerror = rej
    if (as === 'buffer') r.readAsArrayBuffer(file)
    else if (as === 'text') r.readAsText(file)
    else r.readAsDataURL(file)
  })
}

/** Resize an image (File or URL) into a compact JPEG/WebP data URL. */
export async function imageToDataUrl(src, max = 384, quality = 0.86) {
  const url = typeof src === 'string' ? src : await readFile(src)
  const img = await new Promise((res, rej) => {
    const i = new Image()
    i.onload = () => res(i)
    i.onerror = rej
    i.src = url
  })
  const scale = Math.min(1, max / Math.max(img.width, img.height))
  const w = Math.round(img.width * scale)
  const h = Math.round(img.height * scale)
  const c = document.createElement('canvas')
  c.width = w
  c.height = h
  c.getContext('2d').drawImage(img, 0, 0, w, h)
  return c.toDataURL('image/webp', quality)
}

// ── SillyTavern V2 cards ─────────────────────────────────────
function b64ToUtf8(b64) {
  const bin = atob(b64.trim())
  const bytes = Uint8Array.from(bin, (c) => c.charCodeAt(0))
  return new TextDecoder().decode(bytes)
}

/** Read the "chara" (or "ccv3") tEXt chunk from a PNG character card. */
export function pngCardJson(buffer) {
  const v = new DataView(buffer)
  if (v.getUint32(0) !== 0x89504e47) return null
  let off = 8
  const latin = new TextDecoder('latin1')
  const found = {}
  while (off < buffer.byteLength) {
    const len = v.getUint32(off)
    const type = latin.decode(new Uint8Array(buffer, off + 4, 4))
    if (type === 'tEXt') {
      const data = new Uint8Array(buffer, off + 8, len)
      const zero = data.indexOf(0)
      const key = latin.decode(data.slice(0, zero)).toLowerCase()
      if (key === 'chara' || key === 'ccv3') found[key] = latin.decode(data.slice(zero + 1))
    }
    if (type === 'IEND') break
    off += 12 + len
  }
  const raw = found.chara || found.ccv3
  return raw ? JSON.parse(b64ToUtf8(raw)) : null
}

export function fromSillyTavern(card) {
  const d = card?.data || card || {}
  const ex = (d.mes_example || '').split('\n').map((s) => s.trim()).filter((s) => s && s !== '<START>')
  const traits = [d.description, d.personality && `Personality: ${d.personality}`].filter(Boolean).join('\n\n')
  return {
    name: d.name || 'Imported',
    traits,
    greeting: d.first_mes || '',
    examples: ex,
    tags: Array.isArray(d.tags) ? d.tags : [],
    scenario: d.scenario || '',
    alt_greetings: Array.isArray(d.alternate_greetings) ? d.alternate_greetings.filter((g) => typeof g === 'string' && g.trim()) : [],
    avatar_url: '',
  }
}

// Imported cards that describe a minor are refused (explicit signals only, to avoid false positives).
const MINOR_CARD_RE = new RegExp([
  String.raw`\b(loli|lolicon|shota|shotacon|underage|under-age|preteen|pre-teen|jailbait)\b`,
  String.raw`\b(1[0-7]|[1-9])[ -]?(years?[ -]old|yo|y\/o)\b`,
  String.raw`\b(aged?|age of|age:)\s*(1[0-7]|[1-9])\b`,
  String.raw`\b(elementary|middle|junior high)[ -]school(er)?\b`,
  String.raw`(1[0-7]|[1-9])\s*yaşında`,
  String.raw`(reşit olmayan|ilkokul|ortaokul)`,
].join('|'), 'i')

export function cardLooksUnderage(card) {
  const d = card?.data || card || {}
  const text = [d.name, d.description, d.personality, d.scenario, d.first_mes, d.mes_example,
    ...(d.alternate_greetings || []), ...(d.tags || [])].filter((x) => typeof x === 'string').join('\n')
  return MINOR_CARD_RE.test(text)
}

export function toSillyTavern(c) {
  return {
    spec: 'chara_card_v2',
    spec_version: '2.0',
    data: {
      name: c.name, description: c.traits, personality: '', scenario: c.scenario || '',
      first_mes: c.greeting, mes_example: (c.examples || []).join('\n'),
      creator_notes: '', system_prompt: '', post_history_instructions: '',
      alternate_greetings: c.alt_greetings || [], tags: c.tags || [], creator: 'Person AI',
      character_version: '1.0', extensions: {},
    },
  }
}

export function downloadJson(obj, filename) {
  const blob = new Blob([JSON.stringify(obj, null, 2)], { type: 'application/json' })
  const a = document.createElement('a')
  a.href = URL.createObjectURL(blob)
  a.download = filename
  a.click()
  setTimeout(() => URL.revokeObjectURL(a.href), 1000)
}

export function pollinationsAvatar(name, traits) {
  const desc = `${name}. ${(traits || '').slice(0, 220)}`
  const prompt = `portrait avatar, head and shoulders, ${desc}, detailed digital painting, soft cinematic light`
  const seed = Math.floor(Math.random() * 1e6)
  return `https://image.pollinations.ai/prompt/${encodeURIComponent(prompt)}?width=512&height=512&nologo=true&seed=${seed}`
}

export const initials = (name) =>
  (name || '?').trim().split(/\s+/).slice(0, 2).map((w) => w[0]?.toUpperCase() || '').join('') || '?'

// a stable hue from a string, for avatar fallbacks
export function hueOf(s) {
  let h = 0
  for (const ch of s || '') h = (h * 31 + ch.charCodeAt(0)) % 360
  return h
}
