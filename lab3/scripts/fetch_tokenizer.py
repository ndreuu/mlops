import hashlib
from pathlib import Path
import urllib.request

revision='7ae557604adf67be50417f59c2c2f167def9a775'
url=f'https://huggingface.co/Qwen/Qwen2.5-0.5B-Instruct/resolve/{revision}/tokenizer.json'
target=Path('assets/tokenizer.json')
target.parent.mkdir(parents=True,exist_ok=True)
if not target.exists():
    with urllib.request.urlopen(url,timeout=60) as response:
        target.write_bytes(response.read())
checksum=hashlib.sha256(target.read_bytes()).hexdigest()
if checksum!='c0382117ea329cdf097041132f6d735924b697924d6f6fc3945713e96ce87539':
    raise ValueError('Tokenizer checksum mismatch')
print('tokenizer_sha256='+checksum)
