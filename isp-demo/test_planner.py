import copy
import json
import math
import unittest
from pathlib import Path

from planner import Planner, RoadGraph, PlanningError


def fixture():
    a,b,c,d=(0,0),(0,.001),(.001,.001),(.001,0)
    roads={'cities':[{'id':'test','name':'Teste','center':[0,0],'roads':[{'name':'Rua em U','points':[a,b,c,d]},{'name':'Rua isolada','points':[(.005,.005),(.005,.006)]}]}]}
    inventory={'meta':{'as_of':'2026-10-18'},'ctos':[{'id':'A','city_id':'test','lat':a[0],'lng':a[1],'status':'operational','capacity':16},{'id':'B','city_id':'test','lat':b[0],'lng':b[1],'status':'operational','capacity':16},{'id':'FULL','city_id':'test','lat':d[0],'lng':d[1],'status':'operational','capacity':16}], 'clients':[{'id':f'C{i}','cto_id':'FULL','status':'active'} for i in range(16)],'requests':[{'id':'CURRENT','city_id':'test','lat':d[0],'lng':d[1]},{'id':'NEXT','city_id':'test','lat':c[0],'lng':c[1]}], 'links':[{'id':'F','city_id':'test','status':'operational','points':[a,b]}]}
    radar={'cities':[{'id':'test','regions':[{'id':'SPECTRAL','lat':d[0],'lng':d[1]}]}]}
    return inventory,roads,radar


class RoutingTests(unittest.TestCase):
    def setUp(self):
        self.inventory,self.roads,self.radar=fixture()
        self.planner=Planner(self.inventory,self.roads,self.radar)
        self.payload={'city_id':'test','lat':.001,'lng':0,'request_id':'CURRENT','max_drop_m':250}

    def test_route_follows_u_shape_instead_of_straight_line(self):
        graph=self.planner.graphs['test']
        source,target=graph.snap((0,0)),graph.snap((.001,0))
        route=graph.route_to_snap(source,target,graph.search_from_snap(target))
        direct=math.dist(graph.xy((0,0)),graph.xy((.001,0)))
        self.assertAlmostEqual(route['length_m'],direct*3,delta=.2)
        result=self.planner.plan(self.payload)
        self.assertFalse(any(p['cto_id']=='A' for p in result['proposals']))
        self.assertTrue(any(p['cto_id']=='B' for p in result['proposals']))

    def test_full_suspended_and_offline_capacity_is_respected(self):
        self.inventory['clients'][0]['status']='suspended'
        self.inventory['ctos'][1]['status']='offline'
        planner=Planner(self.inventory,self.roads,self.radar)
        result=planner.plan(self.payload)
        self.assertFalse(any(p['kind']=='existing' for p in result['proposals']))
        self.assertIn('B',result['local_incidents'])
        self.assertIn('Investigue primeiro',result['recommendation'])
        self.assertEqual(next(c for c in result['nearest_ctos'] if c['id']=='FULL')['free_ports'],0)

    def test_no_fabricated_connection_between_disconnected_streets(self):
        result=self.planner.plan({'city_id':'test','lat':.005,'lng':.0055})
        self.assertEqual(result['status'],'no_route')
        self.assertFalse(result['proposals'])

    def test_same_edge_projection_keeps_short_exact_path(self):
        graph=self.planner.graphs['test']
        a,b=graph.snap((0,.0002)),graph.snap((0,.0008))
        route=graph.route_to_snap(a,b,graph.search_from_snap(b))
        self.assertAlmostEqual(route['length_m'],66.7,delta=.2)
        self.assertEqual(len(route['points']),2)

    def test_missing_costs_are_unknown_and_cost_formulas_include_reserve(self):
        result=self.planner.plan(self.payload)
        self.assertTrue(all(p['estimated_cost'] is None for p in result['proposals']))
        result=self.planner.plan({**self.payload,'slack_pct':20,'drop_per_m':2,'fiber_per_m':8,'new_cto_cost':600})
        for p in result['proposals']:
            expected=p['drop_cable_m']*1.2*2+(p['fiber_extension_m']*1.2*8+600 if p['kind']=='new_cto' else 0)
            self.assertAlmostEqual(p['estimated_cost'],expected,delta=.3)
        partial=self.planner.plan({**self.payload,'priority':'cluster','drop_per_m':100})
        self.assertEqual(partial['metadata']['ranking_metric'],'cable_meters')

    def test_current_request_is_excluded_and_signals_do_not_inflate_clients(self):
        result=self.planner.plan({**self.payload,'priority':'cluster'})
        for p in result['proposals']:
            self.assertNotIn('CURRENT',p['compatible_request_ids'])
            self.assertEqual(p['additional_by_ports'],min(len(p['compatible_request_ids']),p['ports_after_current']))
            self.assertIn('SPECTRAL',p['historical_signal_ids'])
            self.assertEqual(p['engineering_status'],'pending')

    def test_validation_rejects_invalid_points_parameters_and_request_mismatch(self):
        for change in [{'lat':float('nan')},{'lat':True},{'city_id':[]},{'lat':.5,'request_id':None},{'max_drop_m':0},{'slack_pct':-1},{'request_id':'FAKE'},{'lat':.002}]:
            with self.assertRaises(PlanningError):self.planner.plan({**self.payload,**change})

    def test_read_only_planning_and_repeatability(self):
        original=copy.deepcopy(self.inventory)
        one=self.planner.plan(self.payload);two=self.planner.plan(self.payload)
        self.assertEqual(one,two)
        self.assertEqual(self.inventory,original)


class ActualFixtureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.planner=Planner.from_directory(Path(__file__).resolve().parent/'data')

    def test_three_cities_have_continuous_routes_and_port_limits(self):
        for city in self.planner.cities:
            request=next(r for r in self.planner.inventory['requests'] if r['city_id']==city)
            result=self.planner.plan({'city_id':city,'lat':request['lat'],'lng':request['lng'],'request_id':request['id']})
            self.assertTrue(result['proposals'])
            for p in result['proposals']:
                self.assertLessEqual(p['drop_cable_m'],250.2)
                self.assertGreaterEqual(p['ports_after_current'],0)
                for route in [p['drop_route'],p['fiber_route']]:
                    for a,b in zip(route['points'],route['points'][1:]):
                        # Every segment must lie on an actual stored street segment.
                        middle=((a[0]+b[0])/2,(a[1]+b[1])/2)
                        self.assertLess(self.planner.graphs[city].snap(middle)['gap_m'],.1)


if __name__=='__main__':unittest.main()
