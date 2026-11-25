"""Small image layers work with the teaching cluster's registry cache."""
import hashlib
from pathlib import Path
import shutil

source=Path('model/weights-qwen3')
target=Path('model/packed')
blob='sha256-7f4030143c1c477224c5434f8272c662a8b042079a0a584f0a27a1684fe2e1fa'
if hashlib.file_digest((source/'blobs'/blob).open('rb'),'sha256').hexdigest()!=blob[7:]:
    raise ValueError('Weights checksum mismatch')
shutil.copytree(source/'manifests',target/'metadata/manifests',dirs_exist_ok=True)
(target/'metadata/blobs').mkdir(parents=True,exist_ok=True)
for path in (source/'blobs').iterdir():
    if path.name!=blob:
        shutil.copyfile(path,target/'metadata/blobs'/path.name)
(target/'parts').mkdir(parents=True,exist_ok=True)
with (source/'blobs'/blob).open('rb') as weights:
    for index in range(16):
        part=weights.read(32*1024*1024)
        if not part:
            raise ValueError('Unexpected model size')
        (target/'parts'/f'part{index:02d}').write_bytes(part)
    if weights.read(1):
        raise ValueError('Model exceeds pinned package size')
print('Packed verified Qwen weights: 16 parts, max 32 MiB')
