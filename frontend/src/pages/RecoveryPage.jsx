import {useState} from 'react'
import {Link} from 'react-router-dom'
import {api} from '../api'
export default function RecoveryPage(){
 const [token,setToken]=useState(''),[password,setPassword]=useState(''),[status,setStatus]=useState(''),[busy,setBusy]=useState(false)
 const submit=async e=>{e.preventDefault();setBusy(true);setStatus('');try{await api.post('/auth/recovery/complete',{token,password});setToken('');setPassword('');setStatus('Senha atualizada. Entre novamente; as sessões anteriores foram encerradas.')}catch(err){setStatus(err.message)}finally{setBusy(false)}}
 return <main className="page"><section className="case-inputs"><h1>Recuperar acesso</h1><p>Solicite um código de recuperação ao responsável pela demonstração, que deverá verificar sua identidade. O código vale por 15 minutos e só pode ser usado uma vez.</p><form onSubmit={submit}><label>Código de recuperação<input required autoComplete="off" value={token} onChange={e=>setToken(e.target.value)}/></label><label>Nova senha<input required type="password" minLength={10} maxLength={72} autoComplete="new-password" value={password} onChange={e=>setPassword(e.target.value)}/></label><button disabled={busy}>Atualizar senha</button></form>{status&&<p role="status">{status}</p>}<Link to="/login">Voltar para entrar</Link></section></main>
}
