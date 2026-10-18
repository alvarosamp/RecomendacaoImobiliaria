"""Meaningful consistency checks: temporal ports, counts, topology and provenance."""
import json
import hashlib
import unittest
from collections import defaultdict
from pathlib import Path

from generate import occupied, generate

ROOT = Path(__file__).resolve().parent


class SimulationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.db = json.loads((ROOT / 'data/simulation.json').read_text())

    def test_no_port_double_booking_in_history(self):
        by_port = defaultdict(list)
        for client in self.db['clients']:
            self.assertLessEqual(client['installed_at'], self.db['meta']['as_of'])
            if client['cancelled_at']:
                self.assertGreater(client['cancelled_at'], client['installed_at'])
                self.assertLessEqual(client['cancelled_at'], self.db['meta']['as_of'])
            by_port[(client['cto_id'], client['port'])].append(client)
        for port, clients in by_port.items():
            ordered = sorted(clients, key=lambda c: c['installed_at'])
            for earlier, later in zip(ordered, ordered[1:]):
                self.assertIsNotNone(earlier['cancelled_at'], port)
                self.assertLessEqual(earlier['cancelled_at'], later['installed_at'], port)

    def test_relations_capacity_and_status(self):
        ctos = {c['id']: c for c in self.db['ctos']}
        pops = {p['id']: p for p in self.db['pops']}
        ids = [c['id'] for c in self.db['clients']]
        self.assertEqual(len(ids), len(set(ids)))
        for client in self.db['clients']:
            cto = ctos[client['cto_id']]
            self.assertEqual(cto['city_id'], client['city_id'])
            self.assertTrue(1 <= client['port'] <= cto['capacity'])
            self.assertEqual(client['status'] == 'cancelled', client['cancelled_at'] is not None)
            if client['status'] == 'suspended':
                self.assertLessEqual(client['installed_at'], client['suspended_at'])
        for cto in ctos.values():
            self.assertEqual(cto['city_id'], pops[cto['pop_id']]['city_id'])
            for at in [h['month'] for h in self.db['history']]:
                occupied_count = sum(occupied(c, at) for c in self.db['clients'] if c['cto_id'] == cto['id'])
                self.assertLessEqual(occupied_count, cto['capacity'])

    def test_monthly_balance_and_snapshot(self):
        for city in self.db['cities']:
            balance = 0
            for row in [h for h in self.db['history'] if h['city_id'] == city['id']]:
                balance += row['installed'] - row['cancelled']
                self.assertEqual(balance, row['connected'])
            current = sum(c['status'] != 'cancelled' for c in self.db['clients'] if c['city_id'] == city['id'])
            self.assertEqual(balance, current)

    def test_network_paths_have_no_duplicate_edges_and_reach_pop(self):
        edges = set()
        adjacency = defaultdict(set)
        for link in self.db['links']:
            a, b = map(tuple, link['points'])
            key = (link['city_id'], tuple(sorted((a, b))))
            self.assertNotIn(key, edges)
            edges.add(key)
            adjacency[a].add(b)
            adjacency[b].add(a)
            self.assertGreater(link['length_m'], 0)
            self.assertTrue(link['cto_ids'])
        for pop in self.db['pops']:
            visited, stack = set(), [(pop['lat'], pop['lng'])]
            while stack:
                node = stack.pop()
                if node in visited:
                    continue
                visited.add(node)
                stack.extend(adjacency[node] - visited)
            for cto in self.db['ctos']:
                if cto['pop_id'] == pop['id']:
                    self.assertIn((cto['lat'], cto['lng']), visited)

    def test_request_triage_matches_nearest_box_snapshot(self):
        ctos = {c['id']: c for c in self.db['ctos']}
        for request in self.db['requests']:
            cto = ctos[request['nearest_cto']]
            used = sum(occupied(c, self.db['meta']['as_of']) for c in self.db['clients'] if c['cto_id'] == cto['id'])
            if request['triage'] == 'capacity':
                self.assertEqual(used, cto['capacity'])
            if request['triage'] == 'survey':
                self.assertLess(used, cto['capacity'])
                self.assertEqual(cto['status'], 'operational')
                self.assertLessEqual(request['distance_m'], 350)
            if request['triage'] == 'outside':
                self.assertGreaterEqual(request['distance_m'], 350)

    def test_demonstration_provenance_and_reproducibility(self):
        self.assertTrue(self.db['meta']['synthetic'])
        self.assertTrue(all(c['synthetic'] for c in self.db['clients']))
        self.assertTrue(all(c['synthetic'] for c in self.db['requests']))
        self.assertGreaterEqual(len(self.db['meta']['sources']), 4)
        digest = lambda obj: hashlib.sha256(json.dumps(obj, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
        self.assertEqual(digest(self.db), digest(generate()))


if __name__ == '__main__':
    unittest.main()
