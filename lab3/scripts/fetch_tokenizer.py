import hashlib
from pathlib import Path
import urllib.request

revision='ad9f0ae0864d7fbcd1cd905e3c6c5b069cc8b562'
url=f'https://huggingface.co/deepseek-ai/DeepSeek-R1-Distill-Qwen-1.5B/resolve/{revision}/tokenizer.json'
target=Path('assets/tokenizer.json')
target.parent.mkdir(parents=True,exist_ok=True)
if not target.exists():
    with urllib.request.urlopen(url,timeout=60) as response:
        target.write_bytes(response.read())
checksum=hashlib.sha256(target.read_bytes()).hexdigest()
if checksum!='88145e3c3249adc2546ede277e9819d6e405e19072456e4b521cbc724bd60773':
    raise ValueError('Tokenizer checksum mismatch')
print('tokenizer_sha256='+checksum)
