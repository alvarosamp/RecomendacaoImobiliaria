import { useState, useEffect } from 'react'
import { fetchRuns } from '../api'

const MLFLOW_UI = 'http://localhost:5000'

export default function MlopsPanel() {
  const [runs, setRuns]       = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError]     = useState(null)

  useEffect(() => {
    fetchRuns()
      .then(data => {
        if (data.error) throw new Error(data.error)
        setRuns(Array.isArray(data) ? data : data.runs ?? [])
      })
      .catch(err => setError(err.message))
      .finally(() => setLoading(false))
  }, [])

  const fmt = (val, prefix = 'R$ ') =>
    val != null ? `${prefix}${Number(val).toLocaleString('pt-BR', { maximumFractionDigits: 0 })}` : '–'

  return (
    <div className="panel">
      <div className="panel-header">
        <h2>Experimentos MLflow</h2>
        <a href={MLFLOW_UI} target="_blank" rel="noreferrer" className="external-link">
          Abrir MLflow UI →
        </a>
      </div>

      {loading && <p style={{ color: '#64748b' }}>Carregando experimentos…</p>}
      {error   && <p className="error">MLflow indisponível: {error}</p>}

      {!loading && !error && (
        <table className="data-table">
          <thead>
            <tr>
              <th>Run ID</th>
              <th>Experimento</th>
              <th>Data</th>
              <th>Status</th>
              <th>CV MAE</th>
              <th>R² holdout</th>
              <th>Linhas</th>
            </tr>
          </thead>
          <tbody>
            {runs.length === 0 ? (
              <tr>
                <td colSpan={7} style={{ color: '#64748b', textAlign: 'center', padding: 24 }}>
                  Nenhum experimento ainda. Rode <code>train-price</code> para registrar o primeiro.
                </td>
              </tr>
            ) : runs.map(run => (
              <tr key={run.run_id}>
                <td><code>{run.run_id.slice(0, 8)}…</code></td>
                <td>{run.experiment}</td>
                <td>{run.start_time ?? '–'}</td>
                <td>
                  <span className="badge" style={{ background: run.status === 'FINISHED' ? '#16a34a' : '#ca8a04' }}>
                    {run.status}
                  </span>
                </td>
                <td>{run.metrics?.cv_mae_mean ? fmt(run.metrics.cv_mae_mean) : '–'}</td>
                <td>{run.metrics?.r2_holdout  ? Number(run.metrics.r2_holdout).toFixed(3) : '–'}</td>
                <td>{run.params?.n_rows ?? '–'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  )
}
