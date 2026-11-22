# Лабораторная работа №3. Ollama + RAG через MCP

**Реальный llm7.io не проверен:** кабинет требует пополнения для выдачи ключа. Переключение проверено отдельным облачным имитатором и реальной CPU-моделью.

Команды для повторения — из каталога `lab3`. [Все результаты](evidence/summary.txt), [образы и digest](evidence/images.json), [лог push](evidence/registry.txt).

## 1. CPU-инференс в Kubernetes

Ollama `0.40.17`, [Qwen3 0.6B Q4_K_M](https://ollama.com/library/qwen3:0.6b), один поток, `num_gpu=0`, контекст 2048. Лимит: 850m CPU / 1728Mi RAM.

```bash
kubectl --context=itmo-student-13 -n itmo-student-13 get deploy -l lab=oleinikov-lab3
```

```text
NAME                        READY   UP-TO-DATE   AVAILABLE   AGE
oleinikov-lab3-cloud-mock   1/1     1            1           3h16m
oleinikov-lab3-kb-mcp       1/1     1            1           3h16m
oleinikov-lab3-ollama       1/1     1            1           3h16m
oleinikov-lab3-portal       1/1     1            1           3h16m
```

```bash
kubectl --context=itmo-student-13 -n itmo-student-13 port-forward svc/oleinikov-lab3-ollama 18086:11434 18087:11435
# В другом терминале:
python scripts/check_model.py --output evidence/cpu-after-restart.json
```

Вывод, фрагмент: `status=ready`, `compute=cpu`, `size_vram=0`, ответ `готово`, `1.1 с`.
[Полный вывод](evidence/cpu-after-restart.json), [нагрузка во время запросов](evidence/load-metrics.json).

```bash
kubectl --context=itmo-student-13 -n itmo-student-13 rollout restart deployment/oleinikov-lab3-ollama
kubectl --context=itmo-student-13 -n itmo-student-13 rollout status deployment/oleinikov-lab3-ollama
```

```text
deployment "oleinikov-lab3-ollama" successfully rolled out
Restart: new Pod=True, same image=True, same weights=True
```

[UID до/после и SHA-256 весов](evidence/restart.json). Веса входят в образ; при запуске собираются из 16 слоёв до 32 MiB с проверкой хеша.

## 2. База знаний и MCP

SQLite FTS5 / BM25, русские словоформы, фильтры статуса, пути и версии до ранжирования. Корпус загружается отдельным ConfigMap.

```bash
kubectl --context=itmo-student-13 -n itmo-student-13 port-forward svc/oleinikov-lab3-kb-mcp 18084:8000
# В другом терминале, независимый SDK-клиент:
python scripts/check_mcp.py --from-kubernetes --output evidence/mcp.json
```

```text
MCP: list_sections, search_docs, get_doc
Corpus: 36 records / 35 IDs / 6 sections / 12 paths
MCP auth: no token=401, bad Origin=403
```

[initialize, схемы, tools/call, обе версии M-05 и ошибка отсутствующей версии](evidence/mcp.json).
[Валидация корпуса, защита от инъекций, Retry-After и один half-open probe](evidence/corpus.json).

## 3. Облачный маршрут и CPU-резерв

`llm7.io → Ollama CPU → search_only`. Один поиск и снимок контекста на запрос. CPU выбирает номера источников через JSON Schema; сервер возвращает точные цитаты с проверенными ссылками.

```bash
kubectl --context=itmo-student-13 -n itmo-student-13 port-forward svc/oleinikov-lab3-cloud-mock 18085:8000
# Портал должен быть доступен на 18083:
python scripts/check_routes.py --corpus /path/to/knowledge-base.json --output evidence/routes.json
```

```text
Routes: 21/21 passed (cloud mock + real CPU)
Privacy: 3 checks, cloud requests=0
```

[Лог сценариев](evidence/routes.json): успех, 429, quota, 503, timeout, неверные ссылки, восстановление, отказ обеих моделей, `local_only`, приватный режим, скопированный закрытый вопрос, очередь и отмена.
В имитаторе пауза 1 с и фиктивный ключ; реальный ключ в него не отправляется. Исходный JSON, закрытые фрагменты и секреты в Git и образы не входят.

## 4. Поисковый портал

```bash
kubectl --context=itmo-student-13 -n itmo-student-13 port-forward svc/oleinikov-lab3-portal 18083:8000
```

Открыть [127.0.0.1:18083](http://127.0.0.1:18083). Есть поиск, дерево редакций, фильтры, ответ с источниками, маршрут и число вызовов. Для К02 включить архив, для К03 — черновики. [Скриншот](evidence/portal.jpg).

## 5. Контрольные вопросы

```bash
python scripts/check_questions.py --output evidence/questions.json
python scripts/summary.py --evidence evidence
```

```text
Questions: retrieval=9/9, facts=9/9, model-selected quotes=9/9, free-form outputs=0
```

[Вопросы К01–К08 + К01 с фильтром](checks/questions.json), [ответы, источники, вызовы и время](evidence/questions.json).
Режим извлечения выбран после [предварительного прогона свободного пересказа: 1/9](evidence/free-text-baseline.json).

<details>
<summary>Повторить сборку и развёртывание</summary>

Python 3.12, Docker с `linux/amd64`, доступный контекст `itmo-student-13`.

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python scripts/fetch_tokenizer.py
MODEL_ROOT=model/weights-qwen3 python model/fetch_model.py
python model/pack_model.py
docker build --platform linux/amd64 -f model/Dockerfile -t oleinikov-ollama:lab3 .
docker build --platform linux/amd64 -t oleinikov-rag:lab3 .
python scripts/deploy.py \
  --app-image docker.io/ndreuu/oleinikov-iris@sha256:a08221f670de53bd0a04c17ceae42dc917c89cd3f2ed5fad6b6e685bf8334c1a \
  --model-image docker.io/ndreuu/oleinikov-iris@sha256:2b7440bdd4adbdf78c51e302f89c172fcec0ffa2528cb57513ad3c0fafab0845 \
  --corpus /path/to/knowledge-base.json
```

Когда появится llm7.io-ключ, добавить к `deploy.py` аргумент `--cloud-key-file /private/path/to/key.txt`: ключ попадёт в Kubernetes Secret, портал перезапустится. Реальный облачный запрос нужно проверить отдельно.

</details>
