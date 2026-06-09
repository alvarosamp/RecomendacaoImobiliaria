import { useState } from 'react'

const PRIORITY_COLOR = { alta: '#16a34a', media: '#ca8a04', baixa: '#6b7280', investigar: '#dc2626' }
const RISK_COLOR     = { baixo: '#16a34a', medio: '#ca8a04', alto: '#dc2626' }

export default function OpportunitiesTable({ data }) {
  const [sortKey, setSortKey] = useState('score_residencial')
  const [sortDir, setSortDir] = useState('desc')

  const handleSort = (key) => {
    if (sortKey === key) setSortDir(d => d === 'desc' ? 'asc' : 'desc')
    else { setSortKey(key); setSortDir('desc') }
  }

  const sorted = [...data].sort((a, b) => {
    const va = a[sortKey] ?? 0
    const vb = b[sortKey] ?? 0
    return sortDir === 'desc' ? vb - va : va - vb
  })

  const Th = ({ col, label }) => (
    <th className="sortable" onClick={() => handleSort(col)}>
      {label} {sortKey === col ? (sortDir === 'desc' ? '↓' : '↑') : ''}
    </th>
  )

  return (
    <div className="table-wrapper">
      <table className="data-table">
        <thead>
          <tr>
            <th>H3 ID</th>
            <Th col="score_residencial" label="Residencial" />
            <Th col="score_comercial"   label="Comercial" />
            <th>Prioridade</th>
            <th>Uso primário</th>
            <th>Risco</th>
            <th>NDVI</th>
            <th>Resumo</th>
          </tr>
        </thead>
        <tbody>
          {sorted.map(row => (
            <tr key={row.h3_id}>
              <td><code>{row.h3_id}</code></td>
              <td>{row.score_residencial?.toFixed(1) ?? '-'}</td>
              <td>{row.score_comercial?.toFixed(1) ?? '-'}</td>
              <td>
                <span className="badge" style={{ background: PRIORITY_COLOR[row.priority] ?? '#6b7280' }}>
                  {row.priority ?? '-'}
                </span>
              </td>
              <td>{row.primary_use ?? '-'}</td>
              <td>
                <span className="badge" style={{ background: RISK_COLOR[row.risk_level] ?? '#6b7280' }}>
                  {row.risk_level ?? '-'}
                </span>
              </td>
              <td>{row.ndvi_mean_90?.toFixed(3) ?? '-'}</td>
              <td className="summary">{row.summary ?? ''}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
