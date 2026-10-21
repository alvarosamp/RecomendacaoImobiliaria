import collections,hashlib,json,math,zipfile
from pathlib import Path
REPO=Path(__file__).resolve().parent
import argparse
from urllib.request import urlopen, Request
parser=argparse.ArgumentParser(description='Aggregate original-coordinate IBGE CNEFE addresses in 200 m cells.')
parser.add_argument('--cache',type=Path,default=REPO/'data/territory-cache')
parser.add_argument('--output',type=Path,default=REPO/'data/territory.json')
parser.add_argument('--download',action='store_true',help='Download missing official archives; not called by the web build.')
args=parser.parse_args();ROOT=args.cache;ROOT.mkdir(parents=True,exist_ok=True)
roads=json.loads((REPO/'data/roads.json').read_text())
city_defs=[('pouso-alegre','3152501','Pouso Alegre'),('santa-rita','3159605','Santa Rita do Sapucaí'),('itajuba','3132404','Itajubá')]
cities=[]
for cid,code,name in city_defs:
 # Match the established inventory IDs, independently of the download filename.
 city=next(c for c in roads['cities'] if c['name']==name);cid=city['id'];center=city['center'];c0,c1=center
 p=ROOT/f'qg_810_endereco_Munic{code}.json.zip'
 if not p.exists():
  if not args.download:raise FileNotFoundError(f'{p}: use --download to obtain the official archive.')
  url='https://ftp.ibge.gov.br/Cadastro_Nacional_de_Enderecos_para_Fins_Estatisticos/Censo_Demografico_2022/Arquivos_CNEFE/GeoJSON/Municipio_20240910/'+p.name
  partial=p.with_suffix('.partial')
  with urlopen(Request(url,headers={'User-Agent':'UrbiaISP public-data collection'}),timeout=90) as response, partial.open('wb') as out:
   while chunk:=response.read(1024*1024):out.write(chunk)
  partial.replace(p)
 with zipfile.ZipFile(p) as z:
  data=json.loads(z.read(next(n for n in z.namelist() if n.endswith('.json'))))
 features=data['features'];unique={};quality=collections.Counter();invalid=0
 for f in features:
  props=f['properties'];key=str(props['COD_UNICO_ENDERECO']);kind=int(props['COD_ESPECIE']);q=int(props['NV_GEO_COORD']);coords=f.get('geometry',{}).get('coordinates')
  if str(props['COD_MUNICIPIO'])!=code:raise ValueError('Municipality mismatch')
  if not coords or len(coords)<2:invalid+=1;continue
  lng,lat=coords[:2]
  if not all(isinstance(n,(int,float)) and math.isfinite(n) for n in (lat,lng)) or not(-24<lat<-14 and -52<lng<-39):invalid+=1;continue
  if key not in unique:unique[key]={'lat':lat,'lng':lng,'quality':q,'residential':kind==1}
  else:
   u=unique[key];u['residential']=u['residential'] or kind==1
   if q<u['quality']:u.update(lat=lat,lng=lng,quality=q)
 cells={};excluded=0
 for u in unique.values():
  quality[str(u['quality'])]+=1
  # Use only original census coordinates, not street/locality centroids (levels 2+).
  if u['quality']!=1:excluded+=1;continue
  x=math.radians(u['lng']-c1)*6371000*math.cos(math.radians(c0));y=math.radians(u['lat']-c0)*6371000
  ix,iy=math.floor(x/200),math.floor(y/200);key=(ix,iy)
  cell=cells.setdefault(key,{'total':0,'residential':0});cell['total']+=1;cell['residential']+=int(u['residential'])
 def ll(x,y):return [round(c0+math.degrees(y/6371000),7),round(c1+math.degrees(x/(6371000*math.cos(math.radians(c0)))),7)]
 out=[]
 for (ix,iy),cell in sorted(cells.items()):
  out.append({'id':f'{cid}:{ix}:{iy}','lat':ll((ix+.5)*200,(iy+.5)*200)[0],'lng':ll((ix+.5)*200,(iy+.5)*200)[1],'bounds':[ll(ix*200,iy*200),ll((ix+1)*200,(iy+1)*200)],**cell})
 url='https://ftp.ibge.gov.br/Cadastro_Nacional_de_Enderecos_para_Fins_Estatisticos/Censo_Demografico_2022/Arquivos_CNEFE/GeoJSON/Municipio_20240910/'+p.name
 cities.append({'id':cid,'ibge_code':code,'name':name,'center':center,'source_url':url,'source_sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'raw_records':len(features),'unique_address_ids':len(unique),'duplicate_records':len(features)-len(unique)-invalid,'invalid_records':invalid,'excluded_non_original_coordinates':excluded,'coordinate_quality_counts':dict(quality),'mapped_addresses':sum(c['total'] for c in out),'mapped_residential_addresses':sum(c['residential'] for c in out),'cells':out})
result={'meta':{'source':'IBGE / CNEFE / Censo Demográfico 2022','reference_year':2022,'edition':'GeoJSON municipal 2024-09-10','retrieved_at':'2026-10-20','synthetic':False,'grid_m':200,'coordinate_selection':'NV_GEO_COORD=1 (coordenada original do Censo); demais níveis excluídos','deduplication':'COD_UNICO_ENDERECO; residencial se alguma finalidade COD_ESPECIE=1; uma coordenada por ID','dictionary_url':'https://ftp.ibge.gov.br/Cadastro_Nacional_de_Enderecos_para_Fins_Estatisticos/Censo_Demografico_2022/Arquivos_CNEFE/GeoJSON/Dicionario_CNEFE_Censo_2022_GeoJSON.xls','methodology_url':'https://www.ibge.gov.br/biblioteca/visualizacao/livros/liv102063.pdf','limitations':['Endereços históricos de domicílios particulares, não assinantes, pessoas, imóveis vagos ou ocupação atual.','Contagem deduplicada por código de endereço; apartamentos com IDs distintos podem compartilhar coordenadas.','Células de 200 m em projeção métrica local aproximada; agregação não identifica imóvel ou poste.','Contagem no entorno usa distância em linha reta ao centro da célula, não percurso de cabo, cobertura ou viabilidade.','As coordenadas de nível diferente de 1 foram excluídas; os totais mapeados não representam todo o cadastro municipal.','Dados originais públicos do IBGE; não foram publicados logradouros, números, nomes de estabelecimentos ou códigos individuais.']},'cities':cities}
args.output.write_text(json.dumps(result,ensure_ascii=False,separators=(',',':')))
for c in cities:print(c['id'],{k:c[k] for k in ['raw_records','unique_address_ids','mapped_addresses','mapped_residential_addresses','excluded_non_original_coordinates']},'cells',len(c['cells']))
print('bytes',args.output.stat().st_size)
