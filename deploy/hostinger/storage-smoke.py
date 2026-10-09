import os, hashlib, hmac, datetime, requests
from mlflow.tracking import MlflowClient
from pathlib import Path

def request(method, path, body=b''):
    now=datetime.datetime.now(datetime.timezone.utc)
    stamp=now.strftime('%Y%m%dT%H%M%SZ'); day=now.strftime('%Y%m%d')
    digest=hashlib.sha256(body).hexdigest()
    canonical_headers=f'host:minio:9000\nx-amz-content-sha256:{digest}\nx-amz-date:{stamp}\n'
    signed='host;x-amz-content-sha256;x-amz-date'
    canonical='\n'.join([method,path,'',canonical_headers,signed,digest])
    scope=f'{day}/us-east-1/s3/aws4_request'
    tosign='\n'.join(['AWS4-HMAC-SHA256',stamp,scope,hashlib.sha256(canonical.encode()).hexdigest()])
    key=('AWS4'+os.environ['MINIO_ROOT_PASSWORD']).encode()
    for part in [day,'us-east-1','s3','aws4_request']:
        key=hmac.new(key,part.encode(),hashlib.sha256).digest()
    signature=hmac.new(key,tosign.encode(),hashlib.sha256).hexdigest()
    headers={'Host':'minio:9000','x-amz-date':stamp,'x-amz-content-sha256':digest,'Authorization':f"AWS4-HMAC-SHA256 Credential={os.environ['MINIO_ROOT_USER']}/{scope}, SignedHeaders={signed}, Signature={signature}"}
    return requests.request(method,'http://minio:9000'+path,headers=headers,data=body,timeout=30)

bucket='/ri-hostinger-validation-a10dda'
assert request('PUT',bucket).status_code in (200,409)
assert request('PUT',bucket+'/synthetic.txt',b'isolated validation only').status_code==200
assert request('GET',bucket+'/synthetic.txt').content==b'isolated validation only'
client=MlflowClient(tracking_uri='http://mlflow:5000')
experiment=client.get_experiment_by_name('hostinger-validation-a10dda')
eid=experiment.experiment_id if experiment else client.create_experiment('hostinger-validation-a10dda')
run=client.create_run(eid)
client.log_metric(run.info.run_id,'validation',1.0)
client.set_terminated(run.info.run_id)
assert client.get_run(run.info.run_id).data.metrics['validation']==1.0
print('MinIO authenticated put/get and MLflow create/log/read passed')
