import React from 'react'

/** Person AI mark: a friendly speech bubble with a face, on an accent tile. */
export function logoSvg(accent = '#8b5cf6', size = 32) {
  return `<svg xmlns="http://www.w3.org/2000/svg" width="${size}" height="${size}" viewBox="0 0 32 32">`
    + `<rect width="32" height="32" rx="9" fill="${accent}"/>`
    + `<path d="M7.5 11.2A4.2 4.2 0 0 1 11.7 7h8.6a4.2 4.2 0 0 1 4.2 4.2v5.6a4.2 4.2 0 0 1-4.2 4.2h-4.6l-4.3 3.6c-.6.5-1.5.1-1.5-.7V21a4.2 4.2 0 0 1-2.4-3.8z" fill="#fff"/>`
    + `<circle cx="13.3" cy="13.4" r="1.35" fill="${accent}"/>`
    + `<circle cx="18.7" cy="13.4" r="1.35" fill="${accent}"/>`
    + `<path d="M13.4 16.5q2.6 2 5.2 0" fill="none" stroke="${accent}" stroke-width="1.5" stroke-linecap="round"/>`
    + `</svg>`
}

export default function Logo({ size = 28, className = '' }) {
  return (
    <svg className={`logo ${className}`} width={size} height={size} viewBox="0 0 32 32" aria-hidden="true">
      <rect width="32" height="32" rx="9" fill="var(--accent)" />
      <path
        d="M7.5 11.2A4.2 4.2 0 0 1 11.7 7h8.6a4.2 4.2 0 0 1 4.2 4.2v5.6a4.2 4.2 0 0 1-4.2 4.2h-4.6l-4.3 3.6c-.6.5-1.5.1-1.5-.7V21a4.2 4.2 0 0 1-2.4-3.8z"
        fill="#fff"
      />
      <circle cx="13.3" cy="13.4" r="1.35" fill="var(--accent)" />
      <circle cx="18.7" cy="13.4" r="1.35" fill="var(--accent)" />
      <path d="M13.4 16.5q2.6 2 5.2 0" fill="none" stroke="var(--accent)" strokeWidth="1.5" strokeLinecap="round" />
    </svg>
  )
}

/** Keep the browser-tab icon in the current accent colour. */
export function setFavicon(accent) {
  try {
    let link = document.querySelector('link[rel="icon"]')
    if (!link) { link = document.createElement('link'); link.rel = 'icon'; document.head.appendChild(link) }
    link.type = 'image/svg+xml'
    link.href = 'data:image/svg+xml,' + encodeURIComponent(logoSvg(accent || '#8b5cf6', 64))
  } catch { /* ignore */ }
}
