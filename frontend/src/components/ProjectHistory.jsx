import { useEffect, useState } from 'react'
import { fetchProjectHistory, fetchProjectVersion } from '../api'
import ProjectVersion from './ProjectVersion'
const ACTIONS = {created:'Criação',updated:'Edição',analyzed:'Análise recalculada',shared:'Compartilhamento com equipe',premises_analyzed:'Cálculo de premissas declaradas',restored:'Recuperação de premissas'}
const FIELDS = {name:'Nome',premises:'Premissas do terreno',financial:'Premissas financeiras',technical:'Evidências técnicas',business:'Critérios de localização comercial',notes:'Observações',h3_id:'Região',intended_use:'Uso pretendido',analysis:'Resultados',organization_id:'Equipe'}
export default function ProjectHistory({ project, dirty=false, operationBusy=false, onRestore }) {
  const [items,setItems]=useState([]),[cursor,setCursor]=useState(null),[error,setError]=useState(''),[busy,setBusy]=useState(false)
  const [baseline,setBaseline]=useState(null),[selected,setSelected]=useState(null),[version,setVersion]=useState(null),[versionError,setVersionError]=useState(''),[versionBusy,setVersionBusy]=useState(false)
  useEffect(()=>{setSelected(null);setVersion(null)},[project.id,project.revision])
  useEffect(()=>{
    let active=true;setVersion(null);setVersionError('');setVersionBusy(selected!=null)
    if(selected!=null)fetchProjectVersion(project.id,selected).then(data=>{if(active)setVersion(data)}).catch(err=>{if(active)setVersionError(err.message)}).finally(()=>{if(active)setVersionBusy(false)})
    return()=>{active=false}
  },[selected,project.id,project.revision])
  useEffect(()=>{
    let active=true;setItems([]);setCursor(null);setBaseline(null);setError('');setBusy(true)
    fetchProjectHistory(project.id).then(data=>{if(active){setItems(data.items);setCursor(data.next_before_revision);setBaseline(data.baseline_snapshot)}}).catch(err=>{if(active)setError(err.message)}).finally(()=>{if(active)setBusy(false)})
    return ()=>{active=false}
  },[project.id,project.revision])
  const more=async()=>{setBusy(true);setError('');try {const data=await fetchProjectHistory(project.id,cursor);setItems(current=>[...current,...data.items]);setCursor(data.next_before_revision)} catch(err){setError(err.message)} finally{setBusy(false)}}
  return <section className="workspace-card"><h3>Histórico de atividades</h3><p>O registro começa na implantação desta funcionalidade. O conteúdo fica disponível nas revisões preservadas a partir da atualização de versões.</p>{error && <p role="alert">{error}</p>}
    {!busy && !items.length && !error && <p>Nenhuma atividade registrada.</p>}
    <ol className="project-history">{items.map(item=><li key={item.revision}><strong>Revisão {item.revision} · {ACTIONS[item.action] || item.action}</strong><p>{item.actor_name} · {new Date(item.occurred_at).toLocaleString('pt-BR')}</p><small>{item.changed_fields.map(field=>FIELDS[field]||field).join(', ') || 'Nenhum campo de entrada alterado'}</small>{item.restored_from_revision&&<p>Premissas recuperadas da revisão {item.restored_from_revision}.</p>}{item.snapshot_available&&<div><button disabled={operationBusy} onClick={()=>setSelected(item.revision)}>Consultar revisão {item.revision}</button></div>}</li>)}</ol>
    {baseline&&<p>Captura inicial preservada ao atualizar um estudo existente. <button disabled={operationBusy} onClick={()=>setSelected(baseline.revision)}>Consultar revisão {baseline.revision}</button></p>}
    {cursor && <button disabled={busy} onClick={more}>Carregar atividades anteriores</button>}{busy && <p role="status">Carregando histórico…</p>}
    {versionBusy&&<p role="status">Carregando conteúdo da revisão…</p>}{versionError&&<p role="alert">{versionError}</p>}
    {version&&<>{dirty&&<p>Salve ou descarte as alterações em andamento antes de recuperar premissas.</p>}<ProjectVersion version={version} canRestore={!!onRestore&&project.can_edit!==false&&!dirty&&!operationBusy&&version.current_revision===project.revision} onRestore={onRestore} onClose={()=>setSelected(null)} /></>}
  </section>
}
