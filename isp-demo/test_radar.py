"""Checks for scientific screening, provenance and mixed real/synthetic joins."""
import json
import math
import unittest
from pathlib import Path

import numpy as np
from collect_radar import spectral_screen, TO_UTM, COLLECTION, read_scene

ROOT=Path(__file__).resolve().parent


def scene(red=.1,nir=.4,swir=.2,scl=4):
    return {k:np.full((10,10),value,dtype='float32') for k,value in [('red',red),('nir',nir),('swir16',swir),('scl',scl)]}


class ScreeningTests(unittest.TestCase):
    def test_stable_surface_never_generates_change(self):
        result=spectral_screen([scene(),scene()],[scene(),scene()])
        self.assertFalse(result['changed'].any())
        self.assertTrue(result['valid'].all())

    def test_signal_must_be_present_in_both_later_observations(self):
        change=scene(.2,.2,.4,5)
        repeated=spectral_screen([scene(),scene()],[change,change])
        temporary=spectral_screen([scene(),scene()],[change,scene()])
        self.assertEqual(int(repeated['changed'].sum()),100)
        self.assertFalse(temporary['changed'].any())

    def test_cloud_shadow_water_and_missing_values_cannot_create_candidates(self):
        for category in [0,1,2,3,6,7,8,9,10,11]:
            result=spectral_screen([scene(),scene()],[scene(.2,.2,.4,5),scene(.2,.2,.4,category)])
            self.assertFalse(result['changed'].any(),category)
        invalid=scene(0,0,0,4)
        self.assertFalse(spectral_screen([invalid,invalid],[invalid,invalid])['valid'].any())

    def test_legacy_collection_is_rejected_before_reading_remote_assets(self):
        with self.assertRaises(ValueError):
            read_scene({'collection':'sentinel-2-l2a'},(0,0,1,1))


class ActualDataTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.radar=json.loads((ROOT/'data/radar.json').read_text())
        cls.inventory=json.loads((ROOT/'data/simulation.json').read_text())

    def test_dates_collection_and_radiometric_quality_are_explicit(self):
        self.assertEqual(self.radar['meta']['collection'],COLLECTION)
        self.assertEqual(self.radar['meta']['satellite_data'],'real')
        self.assertEqual(self.radar['meta']['commercial_data'],'synthetic')
        self.assertEqual(len(self.radar['cities']),3)
        for city in self.radar['cities']:
            for period,year in [('before','2024'),('after','2025')]:
                self.assertEqual(len(city['sources'][period]),2)
                for i,source in enumerate(city['sources'][period]):
                    self.assertTrue(source['datetime'].startswith(year))
                    self.assertIn('/collections/'+COLLECTION+'/',source['stac_url'])
                    cache=np.load(ROOT/f"data/radar-cache-c1/{city['id']}/{period}-{i}.npz")
                    usable=np.isin(cache['scl'],[4,5])
                    self.assertLess(float(np.mean(cache['red'][usable]<-.01)),.05)
            self.assertLessEqual(city['eligible_cells'],city['screened_cells'])

    def test_candidate_area_and_quality_match_cached_observations(self):
        for city in self.radar['cities']:
            load=lambda p:[dict(np.load(ROOT/f"data/radar-cache-c1/{city['id']}/{p}-{i}.npz")) for i in range(2)]
            screen=spectral_screen(load('before'),load('after'))
            self.assertEqual(city['candidate_count'],len(city['regions']))
            for region in city['regions']:
                row,col=map(int,region['id'].rsplit('-',2)[-2:]);sl=(slice(row*10,(row+1)*10),slice(col*10,(col+1)*10))
                count=int(screen['changed'][sl].sum())
                self.assertGreaterEqual(count,12)
                self.assertGreaterEqual(float(screen['valid'][sl].mean()),.8)
                self.assertEqual(region['changed_area_ha'],round(count*.04,2))
                self.assertTrue(0<region['changed_area_ha']<=4)
                self.assertEqual(region['field_validation'],'pending')
                self.assertTrue(all(0<=x<=320 and 0<=y<=320 for x,y in region['display_polygon']))

    def test_capacity_and_request_joins_are_derived_from_inventory(self):
        ctos={c['id']:c for c in self.inventory['ctos']}
        for city in self.radar['cities']:
            for region in city['regions']:
                cto=ctos[region['nearest_cto']]
                occupied=sum(c['status']!='cancelled' for c in self.inventory['clients'] if c['cto_id']==cto['id'])
                self.assertEqual(region['free_ports'],cto['capacity']-occupied)
                p=TO_UTM.transform(region['lng'],region['lat'])
                expected={r['id'] for r in self.inventory['requests'] if r['city_id']==city['id'] and math.dist(p,TO_UTM.transform(r['lng'],r['lat']))<=500}
                self.assertEqual(set(region['nearby_request_ids']),expected)
                if region['action']=='Priorizar visita':
                    self.assertTrue(expected)
                    self.assertGreater(region['free_ports'],0)
                    self.assertEqual(region['cto_status'],'operational')
                    self.assertLessEqual(region['network_distance_m'],500)
                    self.assertLessEqual(region['cto_distance_m'],500)


if __name__=='__main__':unittest.main()
