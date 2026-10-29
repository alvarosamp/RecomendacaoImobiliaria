"""Anatel market snapshot and collector tests. The real archive (about 1 GB) is not needed."""
import json
import tempfile
import unittest
import zipfile
from pathlib import Path
from collect_market import collect

ROOT = Path(__file__).resolve().parent
HEADER = 'Ano;Mês;Grupo Econômico;Empresa;CNPJ;Porte da Prestadora;UF;Município;Código IBGE Município;Faixa de Velocidade;Velocidade;Tecnologia;Meio de Acesso;Tipo de Pessoa;Tipo de Produto;Acessos'


def row(year, month, cnpj, empresa, code, value, grupo='OUTROS', tech='FTTH', pessoa='Pessoa Física'):
    return f'{year};{month};{grupo};{empresa};{cnpj};Pequeno Porte;MG;X;{code};>34Mbps;100;{tech};Fibra;{pessoa};Internet;{value}'


class CollectorTests(unittest.TestCase):
    def build(self, rows_by_year):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        path = Path(folder.name) / 'acessos.zip'
        with zipfile.ZipFile(path, 'w') as z:
            for year in (2024, 2025, 2026):
                # Anatel publishes Latin-1; the collector must read accents correctly.
                z.writestr(f'Acessos_Banda_Larga_Fixa_{year}.csv', '\n'.join([HEADER] + rows_by_year.get(year, [])).encode('latin-1'))
        return path

    def test_aggregates_by_cnpj_month_and_city_and_ignores_other_municipalities(self):
        path = self.build({
            2025: [row(2025, 8, '1', 'Alfa', '3152501', 10), row(2025, 8, '2', 'Beta', '3152501', 30)],
            2026: [row(2026, 8, '1', 'Alfa Telecom', '3152501', 40), row(2026, 8, '1', 'Alfa Telecom', '3152501', 20, tech='FWA', pessoa='Pessoa Jurídica'),
                   row(2026, 8, '2', 'Beta', '3152501', 40), row(2026, 8, '3', 'Gama', '9999999', 500), row(2026, 8, '4', 'Itá', '3132404', 7)],
        })
        result = collect(path, '2026-10-28', '2026-10-08')
        self.assertEqual(result['meta']['reference_month'], '2026-08')
        self.assertEqual(result['meta']['comparison_month'], '2025-08')
        pouso = next(c for c in result['cities'] if c['id'] == 'pouso-alegre')
        self.assertEqual(pouso['total'], 100)
        self.assertEqual(pouso['total_12m_antes'], 40)
        alfa = pouso['providers'][0]
        self.assertEqual((alfa['empresa'], alfa['acessos'], alfa['share_pct'], alfa['variacao_12m']), ('Alfa Telecom', 60, 60.0, 50))
        self.assertEqual(pouso['tecnologia'], {'FTTH': 80, 'FWA': 20})
        self.assertEqual(pouso['tipo_pessoa'], {'Pessoa Física': 80, 'Pessoa Jurídica': 20})
        self.assertEqual(pouso['hhi_grupos'], 60 ** 2 + 40 ** 2)
        self.assertNotIn('Gama', json.dumps(result))
        self.assertEqual(next(c for c in result['cities'] if c['id'] == 'itajuba')['providers'][0]['empresa'], 'Itá')

    def test_providers_missing_in_the_reference_month_are_listed_apart(self):
        path = self.build({2026: [row(2026, 6, '1', 'Sumiu', '3152501', 400), row(2026, 7, '1', 'Sumiu', '3152501', 380), row(2026, 7, '2', 'Fica', '3152501', 100),
                                  row(2026, 8, '2', 'Fica', '3152501', 110), row(2026, 7, '3', 'Pequena', '3152501', 10)]})
        pouso = next(c for c in collect(path, 'x')['cities'] if c['id'] == 'pouso-alegre')
        self.assertEqual([p['empresa'] for p in pouso['providers']], ['Fica'])
        self.assertEqual(pouso['absent_in_reference'], [{'cnpj': '1', 'empresa': 'Sumiu', 'grupo': 'OUTROS', 'porte': 'Pequeno Porte', 'ultimo_mes': '2026-07', 'ultimos_acessos': 380}])

    def test_companies_group_branches_by_cnpj_root_and_follow_them_across_minas_gerais(self):
        path = self.build({2026: [
            row(2026, 8, '11111111000101', 'Indep', '3152501', 60), row(2026, 8, '11111111000282', 'Indep filial', '3100104', 40),
            row(2026, 8, '22222222000101', 'Vivo', '3152501', 30, grupo='TELEFONICA'), row(2026, 8, '33333333000101', 'Vivo 2', '3152501', 10, grupo='TELEFONICA'),
            row(2026, 8, '44444444000101', 'Outra cidade só', '3100104', 500),
        ]})
        from collect_market import collect_companies
        data = collect_companies(path, collect(path, 'x'))
        ids = {c['id']: c for c in data['companies']}
        self.assertEqual(set(ids), {'CNPJ-11111111', 'TELEFONICA'})  # only companies present in a study city
        indep = ids['CNPJ-11111111']
        self.assertEqual(indep['name'], 'Indep')
        self.assertEqual(sorted(r[0] for r in indep['footprint']), ['3100104', '3152501'])
        self.assertEqual(sum(r[-1] for r in ids['TELEFONICA']['footprint']), 40)
        self.assertEqual(data['municipalities']['3100104']['total'][-1], 540)
        self.assertEqual(indep['speed']['MG'], [0, 100, 0, 0, 0, 0])  # 100 Mbps falls in 100–299

    def test_economic_groups_are_merged_for_concentration(self):
        path = self.build({2026: [row(2026, 8, '1', 'A1', '3159605', 50, grupo='GRUPO X'), row(2026, 8, '2', 'A2', '3159605', 50, grupo='GRUPO X')]})
        santa = next(c for c in collect(path, 'x')['cities'] if c['id'] == 'santa-rita')
        self.assertEqual(santa['hhi_grupos'], 10000)
        self.assertEqual(santa['providers_count'], 2)


class SnapshotTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.market = json.loads((ROOT / 'data' / 'market.json').read_text(encoding='utf-8'))

    def test_snapshot_is_real_sourced_and_internally_consistent(self):
        meta = self.market['meta']
        self.assertIs(meta['synthetic'], False)
        self.assertTrue(meta['url'].startswith('https://www.anatel.gov.br/'))
        self.assertEqual(len(meta['source_sha256']), 64)
        self.assertEqual(len(meta['series_months']), 13)
        self.assertEqual(meta['series_months'][-1], meta['reference_month'])
        self.assertEqual({c['ibge_code'] for c in self.market['cities']}, {'3152501', '3159605', '3132404'})
        for city in self.market['cities']:
            with self.subTest(city=city['id']):
                self.assertEqual(sum(p['acessos'] for p in city['providers']), city['total'])
                self.assertEqual(sum(city['tecnologia'].values()), city['total'])
                self.assertEqual(sum(city['tipo_pessoa'].values()), city['total'])
                self.assertAlmostEqual(sum(p['share_pct'] for p in city['providers']), 100, delta=0.5)
                self.assertEqual(city['series'][-1]['total'], city['total'])
                self.assertEqual(len({p['cnpj'] for p in city['providers']}), len(city['providers']))
                for p in city['providers']:
                    self.assertEqual(p['series'][-1], p['acessos'])
                    self.assertEqual(p['variacao_12m'], p['acessos'] - p['acessos_12m_antes'])

    def test_snapshot_fits_static_hosting(self):
        self.assertLess((ROOT / 'data' / 'market.json').stat().st_size, 200_000)


if __name__ == '__main__':
    unittest.main()
