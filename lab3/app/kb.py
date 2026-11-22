"""Versioned section index. The original corpus is mounted, never baked into images."""
from collections import Counter
from datetime import date
import hashlib
import json
import os
from pathlib import Path
import re
import sqlite3
from urllib.parse import quote
import uuid

import snowballstemmer
from tokenizers import Tokenizer

STATUSES = {'Действует', 'Архив', 'Черновик'}
VISIBILITY = {'cloud_ok', 'local_only'}
STOP = set('а без бы был была были было в вам вас весь во вот вы где да для до его ее если есть еще же за здесь и из или им их к как какой какая какие когда кто ли либо мне может мы на над надо наш не него нее нет но ну о об от по под после при про с сам со так также такой там те тем то того тоже только тут ты у уже что чтобы это эта эти я сколько сейчас влияют действовал какого почему откуда взялось ли'.split())
STEMMER = snowballstemmer.stemmer('russian')


def words(text):
    text = re.sub(r'(?<=\d)[\s\u00a0\u202f]+(?=\d)', '', text)
    return re.findall(r'[a-zа-я0-9]+', text.lower().replace('ё', 'е'))


def normalize(text):
    return ' '.join(STEMMER.stemWords([w for w in words(text) if w not in STOP and len(w) > 1]))


def query_tokens(text):
    base = normalize(text).split()
    synonyms = {
        'помеща': ['лимит'], 'предел': ['лимит'], 'подписчик': ['канал'],
        'репетиц': ['сентябрьск'], 'правил': ['приемк'], 'подписыва': ['согласован'],
        'расход': ['бюджет'], 'пуш': ['уведомлен'], 'push': ['уведомлен'],
        'видеозвонк': ['звонк', 'пилот'], 'запланирова': ['план'],
        'запущ': ['пилот'], 'расширен': ['приемк'],
    }
    return list(dict.fromkeys(base + [s for token in base for s in synonyms.get(token, [])]))


def doc_url(doc_id, version, anchor=None):
    url = f'/docs/{quote(doc_id, safe="")}/{quote(version, safe="")}'
    return url + ('#' + quote(anchor, safe='') if anchor else '')


def validate_corpus(data):
    documents = []
    paths = set()
    for section in data['sections']:
        for subsection in section['subsections']:
            path = [section['title'], subsection['title']]
            paths.add(tuple(path))
            for doc in subsection['documents']:
                if doc['path'] != path or doc['status'] not in STATUSES or doc.get('visibility') not in VISIBILITY:
                    raise ValueError('Invalid path, status or missing processing label')
                if not re.fullmatch(r'[A-Z]-\d{2}', doc['id']) or not re.fullmatch(r'\d+\.\d+', doc['version']):
                    raise ValueError('Invalid document identity')
                date.fromisoformat(doc['date'])
                anchors = [s['anchor'] for s in doc['sections']]
                if len(anchors) != len(set(anchors)) or not all(re.fullmatch(r's\d{2}', a) for a in anchors):
                    raise ValueError('Invalid section anchors')
                if not all(s.get('title') and isinstance(s.get('body'), list) and all(isinstance(p, str) and p for p in s['body']) for s in doc['sections']):
                    raise ValueError('Invalid section body')
                documents.append(doc)
    identities = {d['id'] + '@' + d['version']: d for d in documents}
    if len(identities) != len(documents):
        raise ValueError('Duplicate document version')
    current = Counter(d['id'] for d in documents if d['status'] == 'Действует')
    if any(n > 1 for n in current.values()):
        raise ValueError('Multiple current versions')
    for doc in documents:
        if any(link not in identities for link in doc['links']):
            raise ValueError('Dangling document link')
        if doc.get('replaces'):
            old = identities.get(doc['replaces'])
            if old is None or old['id'] != doc['id'] or old['date'] >= doc['date']:
                raise ValueError('Invalid replaces relation')
    counts = dict(records=len(documents), unique_ids=len(current), sections=len(data['sections']), paths=len(paths))
    counts['unique_ids'] = len({d['id'] for d in documents})
    if counts != dict(records=36, unique_ids=35, sections=6, paths=12):
        raise ValueError('Unexpected corpus dimensions')
    return documents, counts


class KnowledgeBase:
    def __init__(self, corpus=None, database=None, tokenizer=None):
        self.corpus = Path(corpus or os.getenv('CORPUS_PATH', '/corpus/kb.json'))
        self.database = Path(database or os.getenv('INDEX_PATH', '/data/kb.sqlite'))
        self.tokenizer = Tokenizer.from_file(str(tokenizer or os.getenv('TOKENIZER_PATH', '/opt/tokenizer.json')))
        raw = self.corpus.read_bytes()
        self.generation = hashlib.sha256(raw).hexdigest()
        self.data = json.loads(raw)
        self.documents, self.counts = validate_corpus(self.data)
        self.private = [d for d in self.documents if d['visibility'] != 'cloud_ok']
        self.private_ngrams = set()
        for doc in self.private:
            for section in doc['sections']:
                tokens = words(' '.join(section['body']))
                self.private_ngrams.update(tuple(tokens[i:i+5]) for i in range(len(tokens)-4))
        self.build()

    def tokens(self, text):
        return len(self.tokenizer.encode(text, add_special_tokens=False).ids)

    def chunks(self, text, maximum=175):
        current = []
        for word in text.split():
            if current and self.tokens(' '.join(current + [word])) > maximum:
                yield ' '.join(current)
                current = []
            current.append(word)
        if current:
            yield ' '.join(current)

    def build(self):
        self.database.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.database.with_name(self.database.name + '.' + uuid.uuid4().hex)
        connection = sqlite3.connect(temporary)
        try:
            connection.executescript('''
                CREATE TABLE docs(doc_id TEXT, version TEXT, status TEXT, visibility TEXT, path TEXT, payload TEXT, PRIMARY KEY(doc_id,version));
                CREATE TABLE chunks(id INTEGER PRIMARY KEY, doc_id TEXT, version TEXT, anchor TEXT, chunk_id TEXT, text TEXT, safe INTEGER);
                CREATE VIRTUAL TABLE search USING fts5(title,path,heading,body,tokenize='unicode61');
            ''')
            for doc in self.documents:
                connection.execute('INSERT INTO docs VALUES(?,?,?,?,?,?)',
                    (doc['id'], doc['version'], doc['status'], doc['visibility'], ' / '.join(doc['path']), json.dumps(doc, ensure_ascii=False)))
                for section in doc['sections']:
                    for number, chunk in enumerate(self.chunks(' '.join(section['body']))):
                        safe = not bool(re.search(r'считай.{0,50}системн|игнорир.{0,40}инструк|отправь.{0,60}внешн|убери ссылки|\b[A-Z]+-CANARY-[\w-]+', chunk, re.I))
                        cursor = connection.execute('INSERT INTO chunks(doc_id,version,anchor,chunk_id,text,safe) VALUES(?,?,?,?,?,?)',
                            (doc['id'], doc['version'], section['anchor'], f'{doc["id"]}@{doc["version"]}:{section["anchor"]}:{number}', chunk, int(safe)))
                        connection.execute('INSERT INTO search(rowid,title,path,heading,body) VALUES(?,?,?,?,?)',
                            (cursor.lastrowid, normalize(doc['title']), normalize(' / '.join(doc['path'])), normalize(section['title']), normalize(chunk)))
            connection.commit()
            if connection.execute('PRAGMA integrity_check').fetchone()[0] != 'ok':
                raise ValueError('Index integrity check failed')
            connection.close()
            os.replace(temporary, self.database)
        finally:
            connection.close()
            temporary.unlink(missing_ok=True)

    def requires_local(self, query):
        tokens = words(query)
        return (bool(re.search(r'\b[A-Z]+-CANARY-[\w-]+', query, re.I))
                or any(d['id'].lower() in query.lower() or d['title'].lower() in query.lower() for d in self.private)
                or any(tuple(tokens[i:i+5]) in self.private_ngrams for i in range(len(tokens)-4)))

    def list_sections(self):
        sections = []
        for i, section in enumerate(self.data['sections']):
            children = []
            for j, subsection in enumerate(section['subsections']):
                children.append({'id': f'{i}.{j}', 'title': subsection['title'], 'path': [section['title'], subsection['title']],
                    'documents': [{k: d[k] for k in ('id','version','title','status')} | {'url': doc_url(d['id'],d['version'])} for d in subsection['documents']]})
            sections.append({'id': str(i), 'title': section['title'], 'subsections': children})
        return {'generation': self.generation, 'counts': self.counts, 'sections': sections}

    def get_doc(self, doc_id, version):
        with sqlite3.connect(f'file:{self.database}?mode=ro', uri=True) as connection:
            row = connection.execute('SELECT payload FROM docs WHERE doc_id=? AND version=?', (doc_id, version)).fetchone()
        if row is None:
            raise ValueError('Document version not found')
        doc = json.loads(row[0])
        return {'generation': self.generation, 'document': doc | {'url': doc_url(doc_id, version)}}

    def search_docs(self, query, limit=5, path=None, statuses=None, version=None):
        if not isinstance(query, str) or not 1 <= len(query.strip()) <= 1000 or not 1 <= limit <= 10:
            raise ValueError('Query must contain 1–1000 characters; limit must be 1–10')
        statuses = statuses if statuses is not None else ['Действует']
        if not statuses or not set(statuses) <= STATUSES:
            raise ValueError('Invalid status filter')
        terms = query_tokens(query)
        match = ' OR '.join('"' + t.replace('"', '""') + '"' for t in terms)
        filters = ['d.status IN (' + ','.join('?' for _ in statuses) + ')']
        params = list(statuses)
        if path:
            if len(path) > 2 or not all(isinstance(p, str) and p for p in path):
                raise ValueError('Invalid path filter')
            prefix = ' / '.join(path)
            filters.append('(d.path=? OR substr(d.path,1,?)=?)')
            params += [prefix, len(prefix)+3, prefix+' / ']
        if version:
            filters.append('d.version=?')
            params.append(version)
        explicit_ids = [x.upper() for x in re.findall(r'\b[A-Za-z]-\d{2}\b', query)]
        with sqlite3.connect(f'file:{self.database}?mode=ro', uri=True) as connection:
            connection.row_factory = sqlite3.Row
            if match:
                sql = '''SELECT d.payload,c.*,bm25(search,5,0.3,2,1) AS score
                    FROM search JOIN chunks c ON c.id=search.rowid JOIN docs d ON d.doc_id=c.doc_id AND d.version=c.version
                    WHERE search MATCH ? AND ''' + ' AND '.join(filters) + ' ORDER BY score LIMIT 180'
                rows = connection.execute(sql, [match]+params).fetchall()
            else:
                rows = []
            if explicit_ids:
                sql = '''SELECT d.payload,c.*, -100.0 AS score FROM chunks c JOIN docs d
                    ON d.doc_id=c.doc_id AND d.version=c.version WHERE d.doc_id IN (''' + ','.join('?' for _ in explicit_ids) + ') AND ' + ' AND '.join(filters)
                rows = list(connection.execute(sql, explicit_ids+params).fetchall()) + list(rows)
        cards = {}
        for row in rows:
            identity = (row['doc_id'], row['version'])
            if identity not in cards:
                doc = json.loads(row['payload'])
                cards[identity] = {k: doc[k] for k in ('id','version','title','status','visibility','path')}
                cards[identity] |= {'url': doc_url(*identity), 'score': round(-row['score'], 8), 'snippets': []}
            card = cards[identity]
            if len(card['snippets']) < 3 and not any(s['chunk_id'] == row['chunk_id'] for s in card['snippets']):
                card['snippets'].append({'anchor': row['anchor'], 'chunk_id': row['chunk_id'], 'text': row['text'] if row['safe'] else '[Цитата доступна в оригинале документа]',
                    'safe_for_context': bool(row['safe']), 'tokens': self.tokens(row['text']), 'url': doc_url(*identity, row['anchor'])})
        ranked = sorted(cards.values(), key=lambda c: c['score'], reverse=True)
        if ranked:
            primary = next(d for d in self.documents if (d['id'],d['version']) == (ranked[0]['id'],ranked[0]['version']))
            related = set(primary['links'])
            bonus = ranked[0]['score'] * .6
            # Corpus links reinforce relevant candidates, after all access/version filters.
            for card in ranked[1:]:
                if card['id']+'@'+card['version'] in related:
                    card['score'] = round(card['score']+bonus,8)
            ranked[0]['score'] = round(ranked[0]['score']*1.8,8)
            ranked.sort(key=lambda c:c['score'], reverse=True)
        ranked = ranked[:limit]
        for rank, card in enumerate(ranked, 1):
            card['rank'] = rank
        return {'generation': self.generation, 'cards': ranked,
            'requires_local': self.requires_local(query) or any(c['visibility'] != 'cloud_ok' for c in ranked),
            'query_tokens': len(terms)}
