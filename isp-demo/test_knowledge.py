"""Public-data integrity and source-aware screening; never infer approval or demand."""
import copy
import json
import unittest
from pathlib import Path
from knowledge import Knowledge, validate_context
from planner_errors import PlanningError
from server import PLANNER

DATA=Path(__file__).resolve().parent/'data'

class KnowledgeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.k=Knowledge.from_directory(DATA)

    def test_context_rejects_unknown_fields_and_non_enum_values(self):
        for value in ([],True,'cemig',{'approved':True},{'crossing':False},{'support_owner':'Cemig'},{'installation':None}):
            with self.subTest(value=value),self.assertRaises(PlanningError):validate_context(value)
        self.assertEqual(validate_context(None)['support_owner'],'unknown')

    def test_deduplicated_snapshot_totals_and_privacy(self):
        self.assertFalse(self.k.territory['meta']['synthetic'])
        self.assertEqual(sum(c['mapped_addresses'] for c in self.k.cities.values()),136269)
        self.assertEqual(sum(c['mapped_residential_addresses'] for c in self.k.cities.values()),112356)
        for city in self.k.cities.values():
            self.assertEqual(sum(c['total'] for c in city['cells']),city['mapped_addresses'])
            self.assertEqual(sum(c['residential'] for c in city['cells']),city['mapped_residential_addresses'])
            self.assertEqual(city['unique_address_ids'],city['mapped_addresses']+city['excluded_non_original_coordinates'])
            self.assertEqual(city['raw_records'],city['unique_address_ids']+city['duplicate_records']+city['invalid_records'])
            for cell in city['cells']:
                self.assertEqual(set(cell),{'id','lat','lng','bounds','total','residential'})
                self.assertLessEqual(cell['residential'],cell['total'])

    def test_nearby_geometric_bounds_and_omitted_far_cells(self):
        territory={'meta':{'grid_m':200},'cities':[{'id':'x','source_url':'https://example.org','cells':[
            {'id':'inside','lat':0,'lng':0,'residential':2},
            {'id':'boundary','lat':0,'lng':.002,'residential':3},
            {'id':'outside','lat':0,'lng':.1,'residential':9}]}]}
        k=Knowledge(territory,{'references':[]})
        result=k.nearby('x',(0,0),250)
        self.assertEqual((result['cell_boundary_min'],result['residential_addresses'],result['cell_boundary_max']),(2,5,5))
        self.assertEqual(result['cell_ids'],['inside','boundary'])
        self.assertFalse(result['affects_ranking'])

    def test_sources_have_provenance_and_correct_municipality(self):
        refs=self.k.references
        self.assertEqual(len(refs),12)
        self.assertEqual({r['city_id'] for r in refs.values() if r.get('city_id')},set(self.k.cities))
        for ref in refs.values():
            self.assertTrue(ref['url'].startswith('https://'))
            self.assertEqual(ref['checked_on'],'2026-10-20')
            self.assertTrue(ref['review_note'])
        for city,source in [('pouso-alegre','municipal-pouso'),('santa-rita','municipal-santa'),('itajuba','municipal-itajuba')]:
            check=next(c for c in self.k.assess(city,None)['checks'] if c['id']=='municipal')
            self.assertEqual(check['references'][0]['id'],source)
        self.assertIn('5.406',refs['municipal-santa']['title'])

    def test_cemig_applies_only_when_declared_and_extra_equipment_check(self):
        for owner in ('unknown','other','cemig'):
            assessment=self.k.assess('pouso-alegre',{'support_owner':owner},'new_cto')
            ids={r['id'] for c in assessment['checks'] for r in c['references']}
            self.assertEqual('cemig' in ids,owner=='cemig')
            self.assertEqual(any(c['id']=='equipment' for c in assessment['checks']),owner=='cemig')

    def test_declarations_never_approve_and_underground_does_not_imply_public_land(self):
        for mode in ('aerial','underground'):
            assessment=self.k.assess('itajuba',{'installation':mode,'public_works':'no','crossing':'no','protected_area':'no'})
            self.assertEqual(assessment['status'],'pending_review')
            self.assertFalse(assessment['approved'])
            self.assertFalse(assessment['geometry_checked'])
            self.assertFalse(assessment['documents_verified'])
            checks={c['id']:c for c in assessment['checks']}
            self.assertEqual(checks['public_works']['status'],'declared_absent')
            self.assertEqual('ducts' in checks,mode=='underground')
            self.assertGreaterEqual(assessment['pending_count'],4)

    def test_real_context_does_not_change_route_ranking_or_inflate_requests(self):
        request=PLANNER.inventory['requests'][2]
        payload={k:request[k] for k in ('city_id','lat','lng')}
        payload['request_id']=request['id']
        first=PLANNER.plan(payload)
        second=PLANNER.plan({**payload,'regulatory_context':{'support_owner':'cemig','crossing':'yes'}})
        self.assertTrue(first['proposals'])
        for a,b in zip(first['proposals'],second['proposals']):
            self.assertFalse(b['regulatory']['approved'])
            self.assertFalse(b['real_territory']['affects_ranking'])
            self.assertLessEqual(b['real_territory']['cell_boundary_min'],b['real_territory']['residential_addresses'])
            self.assertLessEqual(b['real_territory']['residential_addresses'],b['real_territory']['cell_boundary_max'])
            a,b=copy.deepcopy(a),copy.deepcopy(b)
            a.pop('regulatory');b.pop('regulatory')
            self.assertEqual(a,b)
        with self.assertRaises(PlanningError):PLANNER.plan({**payload,'regulatory_context':{'crossing':True}})

if __name__=='__main__':unittest.main()
