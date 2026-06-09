import { useMemo } from 'react'

export default function TimeSlider({ dates = [], selectedDate, onChange }) {
  const sorted = useMemo(() => [...dates].sort(), [dates])

  if (!sorted.length) return null

  const idx = selectedDate ? sorted.indexOf(selectedDate) : -1
  const active = idx >= 0

  const step = delta => {
    const next = active
      ? Math.max(0, Math.min(sorted.length - 1, idx + delta))
      : sorted.length - 1
    onChange(sorted[next])
  }

  return (
    <div className="time-slider">
      <div className="time-slider-header">
        <span className="time-slider-label">
          {active ? 'NDVI / NDBI temporal' : 'Modo: scores de oportunidade'}
        </span>
        <span className="time-slider-count">{sorted.length} datas disponíveis</span>
      </div>

      <div className="time-slider-controls">
        <button className="ts-btn" onClick={() => step(-1)} title="Anterior">‹</button>

        <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: 4 }}>
          <input
            type="range"
            className="ts-range"
            min={0}
            max={sorted.length - 1}
            value={active ? idx : sorted.length - 1}
            onChange={e => onChange(sorted[+e.target.value])}
          />
          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 10, color: '#94a3b8' }}>
            <span>{sorted[0]}</span>
            <span>{sorted.at(-1)}</span>
          </div>
        </div>

        <button className="ts-btn" onClick={() => step(+1)} title="Próxima">›</button>

        <div className="ts-date">
          {active ? selectedDate : '–'}
        </div>

        {active && (
          <button
            className="ts-clear"
            onClick={() => onChange(null)}
            title="Voltar ao modo scores"
          >
            ✕
          </button>
        )}
      </div>
    </div>
  )
}
