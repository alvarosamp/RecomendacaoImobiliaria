"""Checks for the real ANATEL market data: integrity, provenance and isolation
from the fictional SerraLink scenario."""
import json
import unittest
from pathlib import Path

from collect_market import CITIES, build, load_rows

ROOT = Path(__file__).resolve().parent


class MarketDataTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rows = load_rows()
        cls.data = build(cls.rows)

    def test_marked_as_real_not_synthetic(self):
        self.assertFalse(self.data['meta']['synthetic'])

    def test_all_six_cities_present_with_expected_scope(self):
        found = {c['id']: c['scope'] for c in self.data['cities']}
        self.assertEqual(len(found), 6)
        for name, meta in CITIES.items():
            self.assertIn(meta['id'], found)
            self.assertEqual(found[meta['id']], meta['scope'])

    def test_network_scope_matches_fictional_scenario_cities(self):
        network_ids = {c['id'] for c in self.data['cities'] if c['scope'] == 'network'}
        self.assertEqual(network_ids, {'pouso-alegre', 'itajuba', 'santa-rita'})

    def test_ranking_shares_sum_close_to_one_and_are_sorted_descending(self):
        for city in self.data['cities']:
            shares = [r['share'] for r in city['ranking']]
            self.assertAlmostEqual(sum(shares), 1.0, places=2)
            self.assertEqual(shares, sorted(shares, reverse=True))
            self.assertEqual(sum(r['accesses'] for r in city['ranking']), city['total_accesses'])

    def test_monthly_series_is_sorted_and_has_no_duplicate_months(self):
        for city in self.data['cities']:
            months = [m['month'] for m in city['monthly_total_accesses']]
            self.assertEqual(months, sorted(months))
            self.assertEqual(len(months), len(set(months)))
            self.assertGreaterEqual(len(months), 12)

    def test_reference_month_is_the_latest_available_month(self):
        for city in self.data['cities']:
            self.assertEqual(city['reference_month'], city['monthly_total_accesses'][-1]['month'])
            self.assertEqual(city['total_accesses'], city['monthly_total_accesses'][-1]['accesses'])

    def test_no_individual_subscriber_or_address_fields(self):
        forbidden_keys = {'cpf', 'endereco', 'rua', 'lat', 'lng', 'cliente', 'assinante'}
        for city in self.data['cities']:
            self.assertTrue(forbidden_keys.isdisjoint(city.keys()))
            for entry in city['ranking'] + city['monthly_total_accesses']:
                self.assertTrue(forbidden_keys.isdisjoint(entry.keys()))

    def test_output_file_matches_rebuilt_data(self):
        output = json.loads((ROOT / 'data' / 'market.json').read_text(encoding='utf-8'))
        self.assertEqual(output, self.data)


if __name__ == '__main__':
    unittest.main()
