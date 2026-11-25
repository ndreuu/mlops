import hashlib
from pathlib import Path
import urllib.request

revision='c1899de289a04d12100db370d81485cdf75e47ca'
url=f'https://huggingface.co/Qwen/Qwen3-0.6B/resolve/{revision}/tokenizer.json'
target=Path('assets/tokenizer.json')
target.parent.mkdir(parents=True,exist_ok=True)
if not target.exists():
    with urllib.request.urlopen(url,timeout=60) as response:
        target.write_bytes(response.read())
checksum=hashlib.sha256(target.read_bytes()).hexdigest()
if checksum!='aeb13307a71acd8fe81861d94ad54ab689df773318809eed3cbe794b4492dae4':
    raise ValueError('Tokenizer checksum mismatch')
print('tokenizer_sha256='+checksum)
