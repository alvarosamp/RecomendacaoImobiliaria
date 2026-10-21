"""Read-only street-graph screening for an ISP expansion study.

Street paths are not cable designs. Inventory and requests are synthetic.
No geocoding service, live equipment or external routing API is called.
"""
import heapq
import json
import math
from collections import defaultdict
from pathlib import Path


from planner_errors import PlanningError
from knowledge import Knowledge, validate_context


def number(value, name, lower, upper):
    if isinstance(value, bool):
        raise PlanningError(f'{name}: informe um número válido.')
    try:
        value = float(value)
    except (ValueError, TypeError):
        raise PlanningError(f'{name}: informe um número válido.') from None
    if not math.isfinite(value) or not lower <= value <= upper:
        raise PlanningError(f'{name}: valor fora do intervalo {lower}–{upper}.')
    return value


class RoadGraph:
    def __init__(self, city):
        self.center = city['center']
        self.graph = defaultdict(dict)
        self.edges = {}
        self.xy_cache = {}
        self.building = True
        for road in city['roads']:
            for a, b in zip(road['points'], road['points'][1:]):
                a, b = tuple(a), tuple(b)
                if a == b:
                    continue
                key = tuple(sorted((a, b)))
                length = math.dist(self.xy(a), self.xy(b))
                if length < .01:
                    continue
                edge = {'a':a, 'b':b, 'name':road['name'], 'length_m':length, 'key':key}
                self.edges[key] = edge
                self.graph[a][b] = edge
                self.graph[b][a] = edge
        self.building = False

    def xy(self, point):
        point = tuple(point)
        if point in self.xy_cache:
            return self.xy_cache[point]
        result = (math.radians(point[1]-self.center[1])*6371000*math.cos(math.radians(self.center[0])), math.radians(point[0]-self.center[0])*6371000)
        if self.building:
            self.xy_cache[point] = result
        return result

    def ll(self, point):
        return (self.center[0]+math.degrees(point[1]/6371000), self.center[1]+math.degrees(point[0]/(6371000*math.cos(math.radians(self.center[0])))))

    def snap(self, point):
        p = self.xy(point)
        best = None
        for edge in self.edges.values():
            a, b = self.xy(edge['a']), self.xy(edge['b'])
            dx, dy = b[0]-a[0], b[1]-a[1]
            t = max(0, min(1, ((p[0]-a[0])*dx+(p[1]-a[1])*dy)/(dx*dx+dy*dy)))
            projection = (a[0]+t*dx, a[1]+t*dy)
            gap = math.dist(p, projection)
            if best is None or gap < best['gap_m']:
                best = {'point':self.ll(projection), 'original':tuple(point), 'gap_m':gap, 'edge':edge, 't':t}
        return best

    def search(self, seeds, limit=math.inf):
        dist, parent, roots, queue = {}, {}, {}, []
        for node, cost, root in seeds:
            if cost < dist.get(node, math.inf):
                dist[node], parent[node], roots[node] = cost, None, root
                heapq.heappush(queue, (cost,node))
        while queue:
            cost, node = heapq.heappop(queue)
            if cost != dist[node] or cost > limit:
                continue
            for neighbor, edge in self.graph[node].items():
                new = cost+edge['length_m']
                if new <= limit and new < dist.get(neighbor,math.inf):
                    dist[neighbor], parent[neighbor], roots[neighbor] = new, node, roots[node]
                    heapq.heappush(queue,(new,neighbor))
        return dist,parent,roots

    def search_from_snap(self, snap):
        edge=snap['edge']
        return self.search([(edge['a'],edge['length_m']*snap['t'],snap['point']), (edge['b'],edge['length_m']*(1-snap['t']),snap['point'])])

    def route_to_snap(self, source, target, search):
        dist,parent,_=search
        edge=source['edge']
        options=[(dist[node]+math.dist(self.xy(source['point']),self.xy(node)),node) for node in (edge['a'],edge['b']) if node in dist]
        direct=math.dist(self.xy(source['point']),self.xy(target['point'])) if edge['key']==target['edge']['key'] else math.inf
        if not options and not math.isfinite(direct):
            return None
        best,node=min(options) if options else (math.inf,None)
        if direct<=best:
            return self.pack_route([source['point'],target['point']], [edge['name']])
        points,names=[source['point']],[edge['name']]
        current=node
        points.append(current)
        while parent[current] is not None:
            nxt=parent[current]
            names.append(self.graph[current][nxt]['name'])
            points.append(nxt)
            current=nxt
        names.append(target['edge']['name'])
        points.append(target['point'])
        return self.pack_route(points,names)

    def route_to_network(self, node, search):
        dist,parent,_=search
        if node not in dist:
            return None
        points,names=[node],[]
        current=node
        while parent[current] is not None:
            nxt=parent[current]
            names.append(self.graph[current][nxt]['name'])
            points.append(nxt)
            current=nxt
        return self.pack_route(list(reversed(points)),list(reversed(names)))

    def pack_route(self, points, names):
        steps, clean, length = [], [points[0]], 0
        for index,(a,b) in enumerate(zip(points,points[1:])):
            distance=math.dist(self.xy(a),self.xy(b))
            if distance<.01:
                continue
            length+=distance
            name=names[index] if index<len(names) else 'Via sem nome no OSM'
            if steps and steps[-1]['street']==name:
                steps[-1]['length_m']+=distance
            else:
                steps.append({'street':name,'length_m':distance})
            clean.append(b)
        return {'points':[list(p) for p in clean], 'length_m':round(length,1), 'streets':[{'street':s['street'],'length_m':round(s['length_m'],1)} for s in steps]}


class Planner:
    def __init__(self, inventory, road_data, radar, knowledge=None):
        self.knowledge=knowledge
        self.inventory,self.road_data,self.radar=inventory,road_data,radar
        self.cities={c['id']:c for c in road_data['cities']}
        self.graphs={cid:RoadGraph(c) for cid,c in self.cities.items()}
        self.used=defaultdict(int)
        for client in inventory['clients']:
            if client['status']!='cancelled':self.used[client['cto_id']]+=1
        self.cto_snaps={c['id']:self.graphs[c['city_id']].snap((c['lat'],c['lng'])) for c in inventory['ctos']}
        self.request_snaps={r['id']:self.graphs[r['city_id']].snap((r['lat'],r['lng'])) for r in inventory['requests']}
        self.network_search={}
        for cid,graph in self.graphs.items():
            nodes={tuple(p) for link in inventory['links'] if link['city_id']==cid and link['status']=='operational' for p in link['points']}
            self.network_search[cid]=graph.search([(node,0,node) for node in nodes if node in graph.graph])

    @classmethod
    def from_directory(cls,path):
        path=Path(path)
        return cls(*(json.loads((path/name).read_text()) for name in ['simulation.json','roads.json','radar.json']), knowledge=Knowledge.from_directory(path))

    def plan(self, payload):
        context=validate_context(payload.get('regulatory_context'))
        cid=payload.get('city_id')
        if not isinstance(cid,str) or cid not in self.cities:raise PlanningError('Selecione uma cidade com grafo viário disponível.')
        lat=number(payload.get('lat'),'Latitude',-90,90)
        lng=number(payload.get('lng'),'Longitude',-180,180)
        max_drop=number(payload.get('max_drop_m',250),'Limite de drop',50,1000)
        slack=number(payload.get('slack_pct',10),'Reserva de cabo',0,50)
        priority=payload.get('priority','current')
        if priority not in ('current','cluster'):raise PlanningError('Prioridade inválida.')
        costs={}
        for key in ['drop_per_m','fiber_per_m','new_cto_cost']:
            raw=payload.get(key)
            costs[key]=None if raw is None or raw=='' else number(raw,key,0,1000000)
        request_id=payload.get('request_id') or None
        if request_id:
            request=next((r for r in self.inventory['requests'] if r['id']==request_id and r['city_id']==cid),None)
            if request is None or abs(request['lat']-lat)>1e-6 or abs(request['lng']-lng)>1e-6:
                raise PlanningError('O pedido selecionado não corresponde ao ponto informado.')
        graph=self.graphs[cid]
        target=graph.snap((lat,lng))
        if not target or target['gap_m']>150:
            raise PlanningError('O ponto está a mais de 150 m das vias armazenadas. Marque um ponto próximo à rua ou amplie o cadastro viário antes de calcular.')
        search=graph.search_from_snap(target)
        near_ctos=[]
        for cto in self.inventory['ctos']:
            if cto['city_id']!=cid:continue
            snap=self.cto_snaps[cto['id']]
            route=graph.route_to_snap(snap,target,search)
            if route is None:continue
            near_ctos.append({'id':cto['id'],'status':cto['status'],'free_ports':cto['capacity']-self.used[cto['id']],'route':route,'cto':cto,'snap_gap_m':round(snap['gap_m'],1),'cable_distance_m':round(route['length_m']+target['gap_m']+snap['gap_m'],1)})
        near_ctos.sort(key=lambda c:(c['cable_distance_m'],c['id']))
        proposals=[]
        for cto in near_ctos:
            if cto['status']!='operational' or cto['free_ports']<1 or cto['cable_distance_m']>max_drop or cto['snap_gap_m']>30:
                continue
            site=(cto['cto']['lat'],cto['cto']['lng'])
            proposal=self.proposal('existing',site,cto['route'],{'points':[list(site)],'length_m':0,'streets':[]},target,cid,max_drop,slack,costs,request_id,cto['free_ports'],graph,cto['id'])
            proposals.append(proposal)
        proposals.sort(key=lambda p:((-p['additional_by_ports'],p['cable_with_slack_m']) if priority=='cluster' else (p['cable_with_slack_m'],-p['additional_by_ports'])))
        proposals=proposals[:2]
        # New-box sites are existing street graph vertices within the adopted drop bound.
        net_search=self.network_search[cid]
        candidates=[node for node,d in search[0].items() if d+target['gap_m']<=max_drop and node in net_search[0]]
        candidates.sort(key=lambda node:(search[0][node],net_search[0][node],node))
        spaced=[]
        for node in candidates:
            if all(math.dist(graph.xy(node),graph.xy(other))>=45 for other in spaced):spaced.append(node)
            if len(spaced)==24:break
        expansions=[]
        for node in spaced:
            snap=graph.snap(node)
            drop=graph.route_to_snap(snap,target,search)
            trunk=graph.route_to_network(node,net_search)
            if not drop or trunk is None:continue
            expansions.append(self.proposal('new_cto',node,drop,trunk,target,cid,max_drop,slack,costs,request_id,16,graph,None))
        expansions.sort(key=lambda p:(-p['additional_by_ports'],p['estimated_cost'] if p['estimated_cost'] is not None else p['cable_with_slack_m'],p['drop_cable_m'],p['id']))
        for expansion in expansions:
            if all(math.dist(graph.xy(expansion['site']),graph.xy(other['site']))>=75 for other in proposals if other['kind']=='new_cto'):
                proposals.append(expansion)
            if sum(p['kind']=='new_cto' for p in proposals)>=2:break
        use_cost=all(value is not None for value in costs.values())
        ranking_metric=lambda proposal:proposal['estimated_cost'] if use_cost else proposal['cable_with_slack_m']
        if priority=='cluster':
            proposals.sort(key=lambda p:(-p['additional_by_ports'],ranking_metric(p),p['kind']!='existing',p['id']))
        else:
            proposals.sort(key=lambda p:(p['kind']!='existing',ranking_metric(p),-p['additional_by_ports'],p['id']))
        local_incidents=[c['id'] for c in near_ctos if c['status']!='operational' and c['cable_distance_m']<=max_drop]
        reason='Estudar atendimento em CTO existente dentro do limite adotado.' if proposals and proposals[0]['kind']=='existing' else ('Estudar ampliação, condicionada à validação da derivação e da capacidade óptica.' if proposals else 'Sem rota conectada à infraestrutura no grafo disponível; não foi inventada uma ligação em linha reta.')
        if local_incidents and not any(p['kind']=='existing' for p in proposals):
            reason='Investigue primeiro a ocorrência em '+', '.join(local_incidents)+'. As alternativas de ampliação abaixo não comprovam solução da falha.'
        if self.knowledge:
            for proposal in proposals:
                proposal['real_territory']=self.knowledge.nearby(cid,proposal['site'],max_drop)
                proposal['regulatory']=self.knowledge.assess(cid,context,proposal['kind'])
        return {'regulatory':self.knowledge.assess(cid,context) if self.knowledge else None,'local_incidents':local_incidents,'status':'study' if proposals else 'no_route','recommendation':reason,'target':{'lat':lat,'lng':lng,'request_id':request_id,'street':target['edge']['name'],'street_projection':list(target['point']),'access_gap_m':round(target['gap_m'],1)},'city_id':cid,'parameters':{'max_drop_m':max_drop,'slack_pct':slack,'priority':priority,**costs},'nearest_ctos':[{k:v for k,v in c.items() if k not in ['route','cto']} for c in near_ctos[:5]],'proposals':proposals,'metadata':{'inventory':'synthetic','requests':'synthetic','street_source':'OpenStreetMap / ODbL','routing':'undirected street graph, approximate local metric projection; no road driving directions','satellite':'real historical screening, 2024/2025; not future customer count','site_search':'up to 24 spaced street vertices within drop radius; heuristic, not global optimum','ranking_metric':'declared_cost' if use_cost else 'cable_meters','source_snapshot':self.inventory['meta']['as_of'],'limitations':['O grafo usa coordenadas compartilhadas e não modela sentidos viários, níveis de viadutos ou passagem de cabos. Rota geométrica pelas vias; não comprova postes, dutos, travessias, permissões, reserva de fibras ou orçamento óptico.','Nova CTO usa hipótese de 16 portas e derivação em um ponto do traçado cadastrado; ambos exigem validação técnica.','O acesso entre o ponto marcado e a rua é um segmento indicativo separado, incluído na estimativa de cabo e não validado como percurso físico.','Pedidos próximos não são vendas e sinais de satélite não são contagem de futuros clientes.','Custos são referências informadas no formulário. Sem todos os custos necessários, o orçamento fica pendente. Não inclui postes, licenças, travessias, equipamentos ativos, deslocamentos, impostos ou contingências.','Não há reserva de portas, alteração de cadastro ou aprovação automática de instalação.']}}

    def proposal(self,kind,site,drop,trunk,target,cid,max_drop,slack,costs,request_id,ports,graph,cto_id):
        site_snap=graph.snap(site)
        site_search=graph.search_from_snap(site_snap)
        compatible=[]
        for request in self.inventory['requests']:
            if request['city_id']!=cid or request['id']==request_id:continue
            snap=self.request_snaps[request['id']]
            if snap['gap_m']>150:continue
            route=graph.route_to_snap(snap,site_snap,site_search)
            if route is not None and route['length_m']+snap['gap_m']+site_snap['gap_m']<=max_drop:
                compatible.append(request['id'])
        compatible=sorted(set(compatible))
        nearby_signals=[]
        for city in self.radar['cities']:
            if city['id']==cid:
                nearby_signals=[r['id'] for r in city['regions'] if math.dist(graph.xy(site),graph.xy((r['lat'],r['lng'])))<=500]
        drop_m=drop['length_m']+target['gap_m']+site_snap['gap_m']
        fiber_m=trunk['length_m']
        factor=1+slack/100
        required=['drop_per_m'] if kind=='existing' else ['drop_per_m','fiber_per_m','new_cto_cost']
        estimated=None
        if all(costs[k] is not None for k in required):
            estimated=drop_m*factor*costs['drop_per_m']
            if kind=='new_cto':estimated+=fiber_m*factor*costs['fiber_per_m']+costs['new_cto_cost']
            estimated=round(estimated,2)
        root=trunk['points'][0] if trunk['points'] else list(site)
        return {'id':f"{kind}-{cto_id or str(round(site[0],7))+'-'+str(round(site[1],7))}",'kind':kind,'cto_id':cto_id,'site':list(site),'network_origin':root,'drop_route':drop,'fiber_route':trunk,'access_guide':[list(target['point']),list(target['original'])],'drop_cable_m':round(drop_m,1),'fiber_extension_m':round(fiber_m,1),'cable_with_slack_m':round((drop_m+fiber_m)*factor,1),'free_ports_before':ports,'ports_after_current':ports-1,'compatible_request_ids':compatible,'additional_by_ports':min(len(compatible),max(0,ports-1)),'historical_signal_ids':nearby_signals,'estimated_cost':estimated,'engineering_status':'pending','reason':('CTO operacional com porta livre e rota dentro do limite de drop adotado.' if kind=='existing' else 'Local candidato a nova CTO com pedido atual dentro do limite de drop; conexão ao traçado cadastrado depende de verificar derivação e fibra livre.')}
