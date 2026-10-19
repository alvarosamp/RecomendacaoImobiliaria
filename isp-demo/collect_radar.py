"""Real Sentinel-2 temporal screening + explicitly synthetic ISP inventory.

Run separately from the serving container. Downloads small COG windows only.
Dependencies: numpy, rasterio, requests, pyproj, shapely, Pillow.
"""
import json
import math
import os
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import requests
import rasterio
from PIL import Image
from pyproj import Transformer
from rasterio.enums import Resampling
from rasterio.transform import from_origin, from_bounds
from rasterio.warp import reproject, transform_bounds
from rasterio.windows import from_bounds as window_from_bounds
from shapely.geometry import shape, box

ROOT = Path(__file__).resolve().parent
STAC = 'https://earth-search.aws.element84.com/v1'
COLLECTION = 'sentinel-2-c1-l2a'
SIZE, RESOLUTION, CELL = 320, 20, 10
PERIODS = {'before': '2024-07-01T00:00:00Z/2024-09-30T23:59:59Z', 'after': '2025-07-01T00:00:00Z/2025-09-30T23:59:59Z'}
TO_UTM = Transformer.from_crs(4326, 32723, always_xy=True)
TO_LL = Transformer.from_crs(32723, 4326, always_xy=True)
TO_MERC = Transformer.from_crs(32723, 3857, always_xy=True)
LL_MERC = Transformer.from_crs(4326, 3857, always_xy=True)


def spectral_screen(before, after):
    """Require valid SCL in all 4 scenes and matching change in both later scenes."""
    def indices(scene):
        red, nir, swir = (scene[k] for k in ('red', 'nir', 'swir16'))
        ndvi = np.divide(nir-red, nir+red, out=np.full_like(nir, np.nan), where=(nir+red)>0.02)
        ndbi = np.divide(swir-nir, swir+nir, out=np.full_like(nir, np.nan), where=(swir+nir)>0.02)
        valid = np.isin(scene['scl'], [4, 5]) & np.isfinite(ndvi) & np.isfinite(ndbi)
        return ndvi, ndbi, valid
    bi = [indices(s) for s in before]
    ai = [indices(s) for s in after]
    valid = np.logical_and.reduce([s[2] for s in bi+ai])
    b_ndvi, b_ndbi = (np.median(np.stack([s[i] for s in bi]), axis=0) for i in (0, 1))
    a_ndvi, a_ndbi = (np.median(np.stack([s[i] for s in ai]), axis=0) for i in (0, 1))
    persistent = valid & np.logical_and.reduce([(s[1]-b_ndbi >= .10) & (s[0]-b_ndvi <= -.12) for s in ai])
    return {'valid': valid, 'changed': persistent, 'before_ndvi':b_ndvi, 'before_ndbi':b_ndbi, 'after_ndvi':a_ndvi, 'after_ndbi':a_ndbi}


def search_scenes(bounds, period):
    payload = {'collections':[COLLECTION], 'bbox':list(bounds), 'datetime':PERIODS[period], 'query':{'eo:cloud_cover':{'lt':20}}, 'limit':60, 'sortby':[{'field':'properties.eo:cloud_cover','direction':'asc'}]}
    response = requests.post(STAC+'/search', json=payload, timeout=90)
    response.raise_for_status()
    candidates = response.json()['features']
    candidates = [s for s in candidates if shape(s['geometry']).covers(box(*bounds))]
    chosen=[]
    for scene in candidates:
        stamp=scene['properties']['datetime'][:10]
        if all(abs((datetime.fromisoformat(stamp)-datetime.fromisoformat(s['properties']['datetime'][:10])).days)>=10 for s in chosen):
            chosen.append(scene)
        if len(chosen)==2:break
    if len(chosen)<2:raise RuntimeError(f'Two scenes covering the AOI not available: {period}')
    return sorted(chosen,key=lambda s:s['properties']['datetime'])


def read_scene(scene, bounds):
    if scene.get('collection')!=COLLECTION:
        raise ValueError('Only Collection 1 radiometry is accepted; legacy metadata may apply offset twice')
    data={}
    for band in ['scl','red','green','blue','nir','swir16']:
        asset=scene['assets'][band]
        with rasterio.Env(GDAL_DISABLE_READDIR_ON_OPEN='EMPTY_DIR', CPL_VSIL_CURL_ALLOWED_EXTENSIONS='.tif', GDAL_HTTP_TIMEOUT='45', GDAL_HTTP_MAX_RETRY='2'):
            with rasterio.open(asset['href']) as source:
                if source.crs.to_epsg()!=32723:raise RuntimeError('Unexpected CRS')
                window=window_from_bounds(*bounds,source.transform)
                raw=source.read(1,window=window,out_shape=(SIZE,SIZE),resampling=Resampling.nearest if band=='scl' else Resampling.average)
        if raw.shape!=(SIZE,SIZE):raise RuntimeError('Incomplete image window')
        if band=='scl':data[band]=raw
        else:
            spec=asset.get('raster:bands',[{}])[0]
            data[band]=raw.astype('float32')*spec.get('scale',.0001)+spec.get('offset',0)
            data[band][raw==0]=np.nan
    usable=np.isin(data['scl'],[4,5])
    if np.any(usable) and np.mean(data['red'][usable] < -.01) > .05:
        raise RuntimeError('Radiometric QC failed: unexpectedly negative red reflectance')
    return data


def scene_info(scene, data):
    return {'id':scene['id'],'datetime':scene['properties']['datetime'],'scene_cloud_pct':scene['properties'].get('eo:cloud_cover'), 'local_usable_pct':round(float(np.isin(data['scl'],[4,5]).mean()*100),2), 'stac_url':f"{STAC}/collections/{COLLECTION}/items/{scene['id']}", 'assets':{band:scene['assets'][band]['href'] for band in ['red','green','blue','nir','swir16','scl']}, 'scale_offset':{band:scene['assets'][band].get('raster:bands') for band in ['red','nir','swir16']}}


def write_composite(scenes, source_transform, merc_bounds, target):
    rgb=np.stack([np.nanmedian(np.stack([s[b] for s in scenes]),axis=0) for b in ['red','green','blue']])
    # Fixed reflectance stretch for both periods, never separate histogram equalisation.
    rgb=np.nan_to_num(np.clip((rgb-.015)/.30,0,1))**(1/1.15)
    output=np.zeros((3,SIZE,SIZE),dtype='uint8')
    dest_transform=from_bounds(*merc_bounds,SIZE,SIZE)
    for i in range(3):
        reproject((rgb[i]*255).astype('uint8'),output[i],src_transform=source_transform,src_crs='EPSG:32723',dst_transform=dest_transform,dst_crs='EPSG:3857',resampling=Resampling.bilinear)
    Image.fromarray(output.transpose(1,2,0)).save(target)


def point_segment_distance(p,a,b):
    dx,dy=b[0]-a[0],b[1]-a[1]
    t=max(0,min(1,((p[0]-a[0])*dx+(p[1]-a[1])*dy)/(dx*dx+dy*dy))) if dx or dy else 0
    return math.hypot(p[0]-a[0]-t*dx,p[1]-a[1]-t*dy)


def build_city(city, inventory, cached=False):
    print('Collecting',city['name'],flush=True)
    cx,cy=TO_UTM.transform(city['center'][1],city['center'][0])
    xmin,ymax=math.floor((cx-SIZE*RESOLUTION/2)/20)*20,math.ceil((cy+SIZE*RESOLUTION/2)/20)*20
    bounds=(xmin,ymax-SIZE*RESOLUTION,xmin+SIZE*RESOLUTION,ymax)
    ll_bounds=transform_bounds(32723,4326,*bounds)
    merc_bounds=transform_bounds(32723,3857,*bounds)
    transform=from_origin(xmin,ymax,RESOLUTION,RESOLUTION)
    def display_point(x,y):
        mx,my=TO_MERC.transform(x,y)
        return [round((mx-merc_bounds[0])/(merc_bounds[2]-merc_bounds[0])*SIZE,3),round((merc_bounds[3]-my)/(merc_bounds[3]-merc_bounds[1])*SIZE,3)]
    city_dir=ROOT/'data'/'radar-cache-c1'/city['id'];city_dir.mkdir(parents=True,exist_ok=True)
    arrays={};sources={}
    for period in PERIODS:
        cache_metadata=city_dir/f'{period}.json'
        if cached:
            sources[period]=json.loads(cache_metadata.read_text())
            if any('/collections/'+COLLECTION+'/' not in source['stac_url'] for source in sources[period]):
                raise ValueError('Cached scenes do not belong to the expected Collection 1')
            arrays[period]=[dict(np.load(city_dir/f'{period}-{i}.npz')) for i in range(2)]
        else:
            scenes=search_scenes(ll_bounds,period)
            arrays[period]=[];sources[period]=[]
            for i,scene in enumerate(scenes):
                print('Reading',scene['id'],flush=True)
                data=read_scene(scene,bounds);arrays[period].append(data);sources[period].append(scene_info(scene,data))
                np.savez_compressed(city_dir/f'{period}-{i}.npz',**data)
            cache_metadata.write_text(json.dumps(sources[period],ensure_ascii=False,indent=2))
        write_composite(arrays[period],transform,merc_bounds,ROOT/'web'/'radar-assets'/f"{city['id']}-{period}.png")
    screen=spectral_screen(arrays['before'],arrays['after'])
    ctos=[c for c in inventory['ctos'] if c['city_id']==city['id']]
    requests_in_city=[r for r in inventory['requests'] if r['city_id']==city['id']]
    clients=inventory['clients']
    def xy(record):return TO_UTM.transform(record['lng'],record['lat'])
    fiber=[(xy({'lat':l['points'][0][0],'lng':l['points'][0][1]}),xy({'lat':l['points'][1][0],'lng':l['points'][1][1]})) for l in inventory['links'] if l['city_id']==city['id']]
    candidates=[];eligible_count=0
    for row in range(0,SIZE,CELL):
        for col in range(0,SIZE,CELL):
            sl=(slice(row,row+CELL),slice(col,col+CELL))
            valid=screen['valid'][sl];changed=screen['changed'][sl]
            if valid.mean()<.8:continue
            eligible_count+=1
            count=int(changed.sum())
            if count<12:continue
            px,py=xmin+(col+CELL/2)*RESOLUTION,ymax-(row+CELL/2)*RESOLUTION
            nearest=min(ctos,key=lambda c:math.dist((px,py),xy(c)))
            connected=[c for c in clients if c['cto_id']==nearest['id'] and c['status']!='cancelled']
            free=nearest['capacity']-len(connected)
            nearby=[r['id'] for r in requests_in_city if math.dist((px,py),xy(r))<=500]
            distance=math.dist((px,py),xy(nearest))
            net_distance=min(point_segment_distance((px,py),a,b) for a,b in fiber)
            lon,lat=TO_LL.transform(px,py)
            corners=[(px-100,py+100),(px+100,py+100),(px+100,py-100),(px-100,py-100)]
            action='Priorizar visita' if net_distance<=500 and distance<=500 and free>0 and nearest['status']=='operational' and nearby else ('Investigar capacidade' if distance<=500 and free==0 else 'Investigar território')
            candidates.append({'id':f"RAD-{city['id']}-{row//CELL:02d}-{col//CELL:02d}", 'city_id':city['id'],'sector':nearest['sector'], 'lat':round(lat,7),'lng':round(lon,7),'polygon':[[*reversed(TO_LL.transform(x,y))] for x,y in corners], 'display_polygon':[display_point(x,y) for x,y in corners], 'screened_area_ha':4,'changed_area_ha':round(count*.04,2),'valid_pct':round(float(valid.mean()*100),1),'changed_pct':round(count,1),'ndvi_before':round(float(np.nanmean(screen['before_ndvi'][sl][valid])),3),'ndvi_after':round(float(np.nanmean(screen['after_ndvi'][sl][valid])),3),'ndbi_before':round(float(np.nanmean(screen['before_ndbi'][sl][valid])),3),'ndbi_after':round(float(np.nanmean(screen['after_ndbi'][sl][valid])),3),'nearest_cto':nearest['id'],'cto_distance_m':round(distance),'network_distance_m':round(net_distance),'free_ports':free,'cto_status':nearest['status'],'nearby_request_ids':nearby,'action':action,'field_validation':'pending','satellite_data':'real','commercial_data':'synthetic'})
    candidates.sort(key=lambda r:(r['action']!='Priorizar visita',not bool(r['nearby_request_ids']),r['network_distance_m']>500,r['network_distance_m'],-r['changed_area_ha']))
    # Keep the full candidate list; presentation can page/filter it without hiding absence of signals.
    return {'id':city['id'],'name':city['name'],'image_bounds':transform_bounds(3857,4326,*merc_bounds),'image_size':SIZE,'images':{p:f"/radar-assets/{city['id']}-{p}.png" for p in PERIODS}, 'sources':sources,'valid_area_pct':round(float(screen['valid'].mean()*100),1),'eligible_cells':eligible_count,'screened_cells':(SIZE//CELL)**2,'candidate_count':len(candidates),'regions':candidates,'ctos':[{**c,'display_point':display_point(*xy(c))} for c in ctos], 'fiber':[[display_point(*a),display_point(*b)] for a,b in fiber]}


def main():
    import argparse
    parser=argparse.ArgumentParser();parser.add_argument('--cached',action='store_true');args=parser.parse_args()
    inventory=json.loads((ROOT/'data/simulation.json').read_text())
    (ROOT/'web/radar-assets').mkdir(parents=True,exist_ok=True)
    output={'meta':{'satellite_data':'real','commercial_data':'synthetic','generated_at':datetime.now(timezone.utc).isoformat(),'catalog':STAC,'collection':COLLECTION,'license':'Copernicus Sentinel data (2024–2025), processed with Earth Search / Element 84.','periods':PERIODS,'analysis_resolution_m':20,'cell_size_m':200,'algorithm':'spectral-screen-v1','thresholds':{'ndbi_increase':.10,'ndvi_decrease':-.12,'min_valid_cell_pct':80,'min_changed_pixels':12,'later_observations':2,'request_radius_m':500},'limitations':['Triagem espectral exploratória, sem validação de classificação urbana. Não mede construções, domicílios, moradores, demanda ou renda.','Solo exposto, agricultura, sazonalidade e diferenças entre cenas podem produzir sinais semelhantes.','A comparação usa julho–setembro de 2024 e 2025; não representa mudanças em 2026. A rede e os pedidos são fictícios, no retrato de 18/10/2026.','SCL permite apenas vegetação e solo/superfície não vegetada; pixels inválidos em qualquer cena são excluídos. Células com menos de 80% de pixels utilizáveis não geram candidatos.','NDVI/NDBI usam refletância com escala e offset do STAC. As bandas são agregadas a uma grade comum de 20 m, respeitando SWIR de 20 m.','O sinal deve aparecer nas duas observações posteriores em relação à mediana das duas anteriores. Isso não elimina falsos positivos.','Área sinalizada é a soma de pixels que passam na regra; não é área construída comprovada.','Distâncias são geométricas, sem rota de drop ou viabilidade óptica. Portas são consultadas somente na CTO mais próxima; não são somadas para evitar dupla contagem.']},'cities':[]}
    for city in inventory['cities']:
        output['cities'].append(build_city(city,inventory,args.cached))
        print(city['name'],output['cities'][-1]['candidate_count'],'candidatos',flush=True)
        (ROOT/'data/radar.json').write_text(json.dumps(output,ensure_ascii=False,allow_nan=False),encoding='utf-8')


if __name__=='__main__':main()
