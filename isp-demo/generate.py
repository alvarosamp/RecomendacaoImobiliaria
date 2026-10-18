"""Deterministic, relational ISP simulation. All subscriber and network data is fictional."""
import csv
import heapq
import json
import math
import random
from collections import defaultdict
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SEED = 3152501
AS_OF = date(2026, 10, 18)
START = date(2025, 10, 1)
SOURCES = [
    {"name": "OpenStreetMap / Overpass", "url": "https://www.openstreetmap.org/copyright", "role": "Geometria e nomes de vias reais; ODbL. Não contém a rede do provedor.", "kind": "geography"},
    {"name": "IBGE — Pouso Alegre", "url": "https://www.ibge.gov.br/cidades-e-estados/mg/pouso-alegre.html", "role": "Referência municipal; não foi usado para estimar clientes ou participação de mercado.", "kind": "context"},
    {"name": "Anatel — coleta de acessos", "url": "https://www.gov.br/anatel/pt-br/regulado/universalizacao/coletas-de-dados-de-acessos", "role": "Referência para separar acessos e municípios. Nenhum acesso de operadora real foi importado.", "kind": "context"},
    {"name": "Furukawa / Lightera — FK-CTO-16MC", "url": "https://www.furukawalatam.com/pt-br/versao-et-pdf/caixa-de-terminacao-optica-fk-cto-16mc", "role": "Referência técnica de caixa com até 16 posições; o cenário adota 16 portas por CTO.", "kind": "technical"},
    {"name": "Rede Brasil — planos em Pouso Alegre", "url": "https://redebrasil.net.br/", "role": "Referência comercial consultada em 18/10/2026: 250 Mbps a R$ 79,90 e 500 Mbps a R$ 99,90. Condições comerciais próprias; não demonstra cobertura em cada rua.", "kind": "commercial"},
    {"name": "Alares — ofertas em Pouso Alegre", "url": "https://www.alaresinternet.com.br/mg/pouso-alegre/planos-de-internet/1250", "role": "Referência consultada em 18/10/2026: oferta de 800 Mbps a R$ 109,99 com fatura digital em dia. Não representa preço médio nem disponibilidade no endereço.", "kind": "commercial"},
]


def distance(a, b):
    lat1, lat2 = math.radians(a[0]), math.radians(b[0])
    dlat, dlon = lat2 - lat1, math.radians(b[1] - a[1])
    h = math.sin(dlat / 2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2)**2
    return 6371000 * 2 * math.atan2(math.sqrt(h), math.sqrt(1 - h))


def occupied(client, at):
    return client['installed_at'] <= at and (not client['cancelled_at'] or client['cancelled_at'] > at)


def generate():
    rng = random.Random(SEED)
    raw = json.loads((ROOT / 'data/roads.json').read_text())
    result = {"meta": {"synthetic": True, "seed": SEED, "as_of": AS_OF.isoformat(), "provider": "SerraLink • provedor fictício", "generated_from": "Ruas OSM + hipóteses explícitas; sem dados privados de provedores", "road_retrieved_at": raw['retrieved_at'], "sources": SOURCES, "assumptions": ["CTOs com 16 portas, um cliente por porta; suspensão reserva a porta e cancelamento a libera.", "Planos fictícios de 250/500/800 Mbps por R$ 79,90/99,90/109,99 usam valores de ofertas públicas como referência; mix, contratos e participação são simulados, sem média de mercado.", "Clientes e equipamentos posicionados junto às vias OSM, sem cadastro real de imóveis, postes ou cabeamento.", "Enlaces seguem caminhos no grafo viário. Não são projeto executivo nem inventário de uma operadora.", "Sinal óptico, incidentes e pedidos são simulados; não há monitoramento ao vivo.", "Proximidade de 350 m serve apenas para triagem de pedidos. Atendimento exige vistoria e validação técnica.", "Setores Norte/Sul/Leste/Oeste são divisões artificiais em relação ao POP, não bairros oficiais.", "Preços de referência não reproduzem todas as condições, promoções ou pacotes das operadoras. Não constituem oferta comercial."]}, "cities": [], "pops": [], "ctos": [], "links": [], "clients": [], "requests": []}
    for city in raw['cities']:
        cid = city['id']
        graph = defaultdict(dict)
        street = {}
        for road in city['roads']:
            for a, b in zip(road['points'], road['points'][1:]):
                a, b = tuple(a), tuple(b)
                if a == b:
                    continue
                weight = distance(a, b)
                graph[a][b] = weight
                graph[b][a] = weight
                street[a] = street[b] = road['name']
        # Largest connected component avoids fake bridges between disconnected roads.
        unseen, components = set(graph), []
        while unseen:
            start = min(unseen)
            component, stack = set(), [start]
            while stack:
                node = stack.pop()
                if node in component:
                    continue
                component.add(node)
                stack.extend(n for n in graph[node] if n not in component)
            unseen.difference_update(component)
            components.append(component)
        nodes = max(components, key=len)
        pop_point = min(nodes, key=lambda p: distance(p, city['center']))
        pop_id = 'POP-' + cid.upper()
        result['cities'].append({k: city[k] for k in ('id', 'name', 'ibge', 'center')})
        result['pops'].append({"id": pop_id, "city_id": cid, "name": 'POP ' + city['name'], "lat": pop_point[0], "lng": pop_point[1], "status": "operational", "commissioned_at": START.isoformat()})
        dist, parent, queue = {pop_point: 0}, {}, [(0, pop_point)]
        while queue:
            cost, node = heapq.heappop(queue)
            if cost != dist[node]:
                continue
            for neighbor, length in graph[node].items():
                new = cost + length
                if new < dist.get(neighbor, float('inf')):
                    dist[neighbor], parent[neighbor] = new, node
                    heapq.heappush(queue, (new, neighbor))
        candidates = sorted(p for p in nodes if 180 < distance(p, pop_point) < 2400)
        rng.shuffle(candidates)
        selected = []
        for point in candidates:
            if all(distance(point, old) > 155 for old in selected):
                selected.append(point)
                if len(selected) == city['ctos']:
                    break
        assert len(selected) == city['ctos'], (cid, len(selected))
        used_edges = defaultdict(set)
        for index, point in enumerate(selected):
            cto_id = f"CTO-{cid[:3].upper()}-{index + 1:03d}"
            sector = ('Norte' if point[0] >= pop_point[0] else 'Sul') if abs(point[0] - pop_point[0]) > abs(point[1] - pop_point[1]) else ('Leste' if point[1] >= pop_point[1] else 'Oeste')
            status = 'offline' if index == 3 and cid == 'pouso-alegre' else ('maintenance' if index == 8 else 'operational')
            cto = {"id": cto_id, "city_id": cid, "pop_id": pop_id, "sector": sector, "street": street[point], "lat": point[0], "lng": point[1], "capacity": 16, "status": status, "commissioned_at": START.isoformat(), "incident": "Rompimento fictício: equipe em deslocamento" if status == 'offline' else ('Manutenção preventiva fictícia' if status == 'maintenance' else None)}
            result['ctos'].append(cto)
            node = point
            while node in parent:
                prev = parent[node]
                used_edges[tuple(sorted((node, prev)))].add(cto_id)
                node = prev
            occupancy = [16, 15, 13, 11, 8, 10, 14, 6, 12][index % 9]
            for port in range(1, 17):
                current = port <= occupancy
                installed = START + timedelta(days=rng.randint(5, 374))
                # Some occupied ports had a previous customer, always cancelled before reuse.
                if current and port % 5 == 0:
                    installed = START + timedelta(days=rng.randint(180, 374))
                    predecessor_end = installed - timedelta(days=rng.randint(7, 50))
                    add_client(result, rng, cid, cto, point, graph, street, port, START + timedelta(days=rng.randint(1, 60)), predecessor_end, False)
                if current:
                    add_client(result, rng, cid, cto, point, graph, street, port, installed, None, rng.random() < .06)
                elif port % 2 == 0:
                    add_client(result, rng, cid, cto, point, graph, street, port, START + timedelta(days=rng.randint(1, 90)), START + timedelta(days=rng.randint(150, 350)), False)
        for a, b in sorted(used_edges):
            result['links'].append({"id": f"FIB-{len(result['links']) + 1:05d}", "city_id": cid, "pop_id": pop_id, "cto_ids": sorted(used_edges[(a, b)]), "points": [list(a), list(b)], "length_m": round(distance(a, b), 2), "status": "operational", "commissioned_at": START.isoformat()})
        city_ctos = [c for c in result['ctos'] if c['city_id'] == cid]
        for i in range(36):
            point = candidates[(i * 71) % len(candidates)]
            nearest = min(city_ctos, key=lambda c: distance(point, (c['lat'], c['lng'])))
            d = distance(point, (nearest['lat'], nearest['lng']))
            active = sum(occupied(c, AS_OF.isoformat()) for c in result['clients'] if c['cto_id'] == nearest['id'])
            triage = 'outside' if d > 350 else ('capacity' if active == 16 else ('incident' if nearest['status'] != 'operational' else 'survey'))
            result['requests'].append({"id": f"PED-{len(result['requests'])+1:04d}", "city_id": cid, "sector": nearest['sector'], "street": street[point], "lat": point[0], "lng": point[1], "created_at": (AS_OF - timedelta(days=rng.randint(0, 45))).isoformat(), "nearest_cto": nearest['id'], "distance_m": round(d), "triage": triage, "monthly_price": 99.9, "synthetic": True})
    result['history'] = []
    for month in range(13):
        year, m = divmod(2025 * 12 + 9 + month, 12)
        cutoff = min(date(year + (m == 11), (m + 1) % 12 + 1, 1) - timedelta(days=1), AS_OF)
        for city in result['cities']:
            city_clients = [c for c in result['clients'] if c['city_id'] == city['id']]
            result['history'].append({"month": cutoff.isoformat(), "city_id": city['id'], "installed": sum(c['installed_at'][:7] == cutoff.isoformat()[:7] and c['installed_at'] <= cutoff.isoformat() for c in city_clients), "cancelled": sum(bool(c['cancelled_at']) and c['cancelled_at'][:7] == cutoff.isoformat()[:7] and c['cancelled_at'] <= cutoff.isoformat() for c in city_clients), "connected": sum(occupied(c, cutoff.isoformat()) for c in city_clients)})
    (ROOT / 'data/simulation.json').write_text(json.dumps(result, ensure_ascii=False, separators=(',', ':')), encoding='utf-8')
    for entity in ('clients', 'ctos', 'pops', 'requests'):
        rows = result[entity]
        with (ROOT / f'data/{entity}.csv').open('w', newline='', encoding='utf-8') as stream:
            writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)
    print(json.dumps({k: len(result[k]) for k in ('cities', 'pops', 'ctos', 'links', 'clients', 'requests')}, ensure_ascii=False))
    return result


def add_client(result, rng, cid, cto, point, graph, street, port, installed, cancelled, suspended):
    neighbor = rng.choice(sorted(graph[point]))
    fraction = min(rng.uniform(.08, .85), 100 / max(distance(point, neighbor), 1))
    lat = point[0] + (neighbor[0] - point[0]) * fraction + rng.uniform(-.00003, .00003)
    lng = point[1] + (neighbor[1] - point[1]) * fraction + rng.uniform(-.00003, .00003)
    speed, price = rng.choices([(250, 79.9), (500, 99.9), (800, 109.99)], weights=[25, 55, 20])[0]
    identifier = f"SIM-{len(result['clients'])+1:05d}"
    result['clients'].append({"id": identifier, "label": f"Instalação demonstrativa {identifier}", "city_id": cid, "sector": cto['sector'], "street": street[point], "lat": round(lat, 7), "lng": round(lng, 7), "cto_id": cto['id'], "port": port, "status": 'cancelled' if cancelled else ('suspended' if suspended else 'active'), "installed_at": installed.isoformat(), "cancelled_at": cancelled.isoformat() if cancelled else None, "suspended_at": max(installed, AS_OF - timedelta(days=rng.randint(5, 25))).isoformat() if suspended else None, "speed_mbps": speed, "monthly_price": price, "optical_dbm": None if cancelled or cto['status'] == 'offline' else round(rng.uniform(-26, -17), 1), "synthetic": True})


if __name__ == '__main__':
    generate()
