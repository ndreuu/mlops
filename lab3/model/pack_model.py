"""Small image layers work with the teaching cluster's registry cache."""
import hashlib
from pathlib import Path
import shutil

source=Path('model/weights-qwen')
target=Path('model/packed')
blob='sha256-c5396e06af294bd101b30dce59131a76d2b773e76950acc870eda801d3ab0515'
if hashlib.file_digest((source/'blobs'/blob).open('rb'),'sha256').hexdigest()!=blob[7:]:
    raise ValueError('Weights checksum mismatch')
shutil.copytree(source/'manifests',target/'metadata/manifests',dirs_exist_ok=True)
(target/'metadata/blobs').mkdir(parents=True,exist_ok=True)
for path in (source/'blobs').iterdir():
    if path.name!=blob:
        shutil.copyfile(path,target/'metadata/blobs'/path.name)
(target/'parts').mkdir(parents=True,exist_ok=True)
with (source/'blobs'/blob).open('rb') as weights:
    for index in range(12):
        part=weights.read(32*1024*1024)
        if not part:
            raise ValueError('Unexpected model size')
        (target/'parts'/f'part{index:02d}').write_bytes(part)
    if weights.read(1):
        raise ValueError('Model exceeds pinned package size')
print('Packed verified Qwen weights: 12 parts, max 32 MiB')
