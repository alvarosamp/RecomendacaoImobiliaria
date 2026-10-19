export function ProductIcon({ name = 'building', size = 24, ...props }) {
  const paths = {
    help: <><circle cx="12" cy="12" r="9"/><path d="M9.5 9a2.5 2.5 0 0 1 5 .5c0 1.5-2.5 1.7-2.5 3.5M12 17h.01"/></>,
    building: <><path d="M4 21V8l8-5 8 5v13M2 21h20M9 21v-5h6v5M8 9h1m6 0h1M8 12h1m6 0h1" /></>,
    tools: <><path d="m4 20 9-9M14 4a5 5 0 0 0 6 6l-6 6-6-6 6-6ZM3 3l5 5M3 3v4m0-4h4M16 17l4 4" /></>,
    chart: <><path d="M4 4v16h17M8 15l4-5 4 2 5-7M17 5h4v4" /></>,
    home: <><path d="m3 10 9-7 9 7M5 9v12h14V9M9 21v-7h6v7" /></>,
    shop: <><path d="M4 10v11h16V10M3 10l2-7h14l2 7M3 10c0 3 4 3 4 0 0 3 5 3 5 0 0 3 5 3 5 0 0 3 4 3 4 0M9 21v-7h6v7" /></>,
    civic: <><path d="m3 7 9-4 9 4v2H3V7ZM5 10v8m7-8v8m7-8v8M3 21h18M3 18h18" /></>,
    arrow: <><path d="M4 12h16m-6-6 6 6-6 6" /></>,
    document: <><path d="M14 3H5v18h14V8l-5-5Zm0 0v5h5M8 12h8m-8 4h6" /></>,
    check: <path d="m5 12 4 4L19 6" />,
    pin: <><path d="M19 10c0 5-7 11-7 11S5 15 5 10a7 7 0 1 1 14 0Z" /><circle cx="12" cy="10" r="2" /></>,
  }
  return <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true" {...props}>{paths[name] || paths.building}</svg>
}

// Editorial illustration, deliberately abstract; it does not represent geographic evidence.
export function TerritoryVisual({ compact = false }) {
  return <div className={`territory-art${compact ? ' compact' : ''}`} aria-hidden="true">
    <svg viewBox="0 0 600 440" fill="none">
      <defs><pattern id="territory-grid" width="32" height="32" patternUnits="userSpaceOnUse"><path d="M32 0H0v32" stroke="#b9c8b8" strokeWidth=".7" /></pattern></defs>
      <rect width="600" height="440" fill="#e7eee1" /><rect width="600" height="440" fill="url(#territory-grid)" />
      <path d="M-30 335C95 250 76 176 211 162s140 66 245-9S529 44 640 12" stroke="#cadbc6" strokeWidth="94" />
      <path d="M-30 335C95 250 76 176 211 162s140 66 245-9S529 44 640 12" stroke="#a2c7b8" strokeWidth="31" />
      <g fill="#d3dec9" stroke="#b5c4ac" strokeWidth="1.5"><path d="m40 45 116 4-8 71-105-2Z"/><path d="m195 34 106 1 6 76-124 8Z"/><path d="m348 36 79 6-14 60-66 23Z"/><path d="m40 173 43-4-27 59-23 8Z"/><path d="m178 229 97 8-11 88-113-8Z"/><path d="m315 242 93-4 12 90-104 9Z"/><path d="m455 230 105-56 10 130-111 21Z"/><path d="m23 371 101-19 11 71-112-4Z"/><path d="m176 365 95 8-2 50-100 1Z"/><path d="m318 374 110-9 14 60-120-1Z"/></g>
      <g stroke="#fffdf6" strokeWidth="12"><path d="M0 140 315 136 471 113 600 58M139 0l-15 150-24 107-4 183M320 0l-1 139-33 85 5 216M0 347l144-5 283 10 173-35M434 0l12 121-17 100 15 219"/></g>
      <path d="m178 229 97 8-11 88-113-8Z" fill="#d4eaa2" stroke="#537950" strokeWidth="2" />
      <path d="m315 242 93-4 12 90-104 9Z" fill="#e2c8ac" stroke="#a8815c" strokeWidth="2" strokeDasharray="5 4"/>
      <g transform="translate(208 264)"><circle r="22" fill="#173d32"/><path d="M-7 0h14M0-7v14" stroke="#e0efba" strokeWidth="2"/></g>
      <g transform="translate(363 276)"><circle r="15" fill="#fffdf6"/><path d="m-4-5 8 10m0-10-8 10" stroke="#926d48" strokeWidth="1.5"/></g>
      <g transform="translate(520 365)"><circle r="24" fill="#fffdf6"/><path d="m0-13 6 22-6-4-6 4 6-22Z" stroke="#244439" strokeWidth="1.5"/></g>
    </svg>
    <span className="territory-caption">Ilustração territorial · sem valor de análise</span>
  </div>
}
