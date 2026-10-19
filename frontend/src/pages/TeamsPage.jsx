import RecoveryAdmin from '../components/RecoveryAdmin'
import { useEffect, useState } from 'react'
import { addMember, changeMemberRole, createOrganization, fetchMembers, fetchOrganizations, removeMember } from '../api'
const labels = { owner: 'Responsável', editor: 'Editor', viewer: 'Leitor' }
export default function TeamsPage() {
  const [teams, setTeams] = useState([])
  const [selected, setSelected] = useState('')
  const [members, setMembers] = useState([])
  const [name, setName] = useState('')
  const [email, setEmail] = useState('')
  const [role, setRole] = useState('viewer')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [status, setStatus] = useState('')
  const team = teams.find(item => item.id === Number(selected))
  const run = async task => { setBusy(true); setError(''); try { await task() } catch (err) { setError(err.message) } finally { setBusy(false) } }
  useEffect(() => { let active = true; fetchOrganizations().then(rows => { if (active) setTeams(rows) }).catch(err => { if (active) setError(err.message) }); return () => { active = false } }, [])
  useEffect(() => { let active = true; setMembers([]); if (team?.role === 'owner') fetchMembers(team.id).then(rows => { if (active) setMembers(rows) }).catch(err => { if (active) setError(err.message) }); return () => { active = false } }, [team?.id, team?.role])
  const reloadMembers = async () => setMembers(await fetchMembers(team.id))
  return <section className="page teams-page"><div className="page-header"><div className="page-eyebrow">Colaboração</div><h2>Equipes e acesso</h2><p>Organize projetos de terrenos com sua equipe. O perfil de trabalho organiza ferramentas; a participação na equipe define acesso aos projetos compartilhados.</p></div>
    {error && <div role="alert" className="error-msg">{error}</div>}<p role="status">{status}</p>
    <form className="study-fields" onSubmit={event => { event.preventDefault(); run(async () => { const created = await createOrganization(name); setTeams(current => [...current, created]); setSelected(String(created.id)); setName(''); setStatus('Equipe criada') }) }}><label>Nome da nova equipe<input required maxLength={160} value={name} onChange={event => setName(event.target.value)} disabled={busy} /></label><button disabled={busy || !name.trim()} className="report-download">Criar equipe</button></form>
    <label>Equipe<select className="team-select" value={selected} disabled={busy} onChange={event => { setSelected(event.target.value); setError(''); setStatus('') }}><option value="">Selecione uma equipe</option>{teams.map(item => <option key={item.id} value={item.id}>{item.name} · {labels[item.role]}</option>)}</select></label>
    {team && <div className="workspace-card"><h3>{team.name}</h3><p>Seu acesso: {labels[team.role]}. Responsáveis gerenciam membros; editores criam e alteram estudos; leitores consultam e exportam.</p>{team.role === 'owner' && <>
      <form className="study-fields" onSubmit={event => { event.preventDefault(); run(async () => { await addMember(team.id, { email, role }); setEmail(''); await reloadMembers(); setStatus('Membro adicionado') }) }}><label>Email de uma conta cadastrada<input required type="email" value={email} onChange={event => setEmail(event.target.value)} disabled={busy} /></label><label>Acesso do novo membro<select disabled={busy} value={role} onChange={event => setRole(event.target.value)}><option value="viewer">Leitor</option><option value="editor">Editor</option></select></label><button className="report-download" disabled={busy}>Adicionar membro</button></form>
      <p>O membro precisa ter uma conta na Urbia. A inclusão não envia email. Projetos pessoais só ficam disponíveis após compartilhamento explícito.</p>
      <div className="comparison-table-wrap"><table className="comparison-table"><thead><tr><th>Membro</th><th>Acesso</th><th>Ação</th></tr></thead><tbody>{members.map(member => <tr key={member.user_id}><td>{member.name}<small>{member.email}</small></td><td>{member.role === 'owner' ? labels.owner : <select aria-label={`Acesso de ${member.name}`} disabled={busy} value={member.role} onChange={event => run(async () => { await changeMemberRole(team.id, member.user_id, event.target.value); await reloadMembers(); setStatus('Acesso atualizado') })}><option value="viewer">Leitor</option><option value="editor">Editor</option></select>}</td><td>{member.role !== 'owner' && <button disabled={busy} onClick={() => { if (window.confirm(`Remover ${member.name} desta equipe? O acesso aos projetos compartilhados será revogado.`)) run(async () => { await removeMember(team.id, member.user_id); await reloadMembers(); setStatus('Membro removido') }) }}>Remover</button>}</td></tr>)}</tbody></table></div>
    </>}</div>}
  <RecoveryAdmin /></section>
}
