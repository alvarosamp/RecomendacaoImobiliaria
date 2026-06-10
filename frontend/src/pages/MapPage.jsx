import { useState } from 'react'
import H3Map from '../components/H3Map'
import TimeSlider from '../components/TimeSlider'

export default function MapPage({ scores, timeDates, timeRecords, selectedDate, onDateChange }) {
  const [priorityFilter, setPriorityFilter] = useState('')
  const [riskFilter, setRiskFilter]         = useState('')

  const filtered = scores.filter(r => {
    if (priorityFilter && r.priority !== priorityFilter) return false
    if (riskFilter     && r.risk_level !== riskFilter)  return false
    return true
  })

  return (
    <div className="map-page">
      <div className="map-topbar">
        <select value={priorityFilter} onChange={e => setPriorityFilter(e.target.value)}>
          <option value="">Todas as prioridades</option>
          <option value="alta">Alta</option>
          <option value="media">Média</option>
          <option value="baixa">Baixa</option>
        </select>
        <select value={riskFilter} onChange={e => setRiskFilter(e.target.value)}>
          <option value="">Todos os riscos</option>
          <option value="baixo">Baixo</option>
          <option value="medio">Médio</option>
          <option value="alto">Alto</option>
        </select>
        <span className="count-tag">{filtered.length} células</span>
      </div>

      <div className="map-area">
        <H3Map
          data={filtered}
          timeData={timeRecords}
          selectedDate={selectedDate}
        />
      </div>

      <TimeSlider
        dates={timeDates}
        selectedDate={selectedDate}
        onChange={onDateChange}
      />
    </div>
  )
}
