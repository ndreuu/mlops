# Лабораторная работа №2. Runbook Search CI/CD

## Проверка запуска — 25.11.2026

Lab 3 остановлена (`replicas=0`); staging и production Lab 2 оставлены запущенными.

```bash
kubectl --context=itmo-student-13 -n itmo-student-13 get deploy -l app.kubernetes.io/name=mlops-search
```

```text
NAME                                      READY   UP-TO-DATE   AVAILABLE
oleinikov-search-prod-mlops-search         1/1     1            1
oleinikov-search-staging-mlops-search      1/1     1            1
```

[Команды проверки](evidence/recheck-2026-11-25/commands.txt) · [Staging smoke](evidence/recheck-2026-11-25/staging-smoke.json) · [Production smoke](evidence/recheck-2026-11-25/production-smoke.json) · [Состояние и квота](evidence/recheck-2026-11-25/cluster.txt).

В обоих окружениях: `/readyz` → `ready`, `actual_top=doc-rollback`, `ranking_mode=normal`, `passed=true`.

Повторный [pipeline 25.11](https://github.com/ndreuu/mlops/actions/runs/45608006169): quality и build — `success`; staging — `failure` из-за `ImagePullBackOff` (таймаут прокси registry). Helm `--atomic` восстановил прежний образ. [Статусы jobs](evidence/recheck-2026-11-25/rerun.json) · [Лог ошибки](evidence/recheck-2026-11-25/rerun-failure.txt). Ниже — артефакты полного успешного pipeline 22.11.

## 1. Репозиторий и pipeline

- [Публичный репозиторий](https://github.com/ndreuu/mlops).
- [Успешный pipeline](https://github.com/ndreuu/mlops/actions/runs/45033904297) — `success`.

## 2. Image

- Repository: `docker.io/ndreuu/oleinikov-iris`.
- Tag: `search-bb5aab86a1479b3acac1034cbf2385655db6bc58`.
- Digest: `sha256:f1f7db764524e5419376dd23e3c7b696ae838711040675a54d55fb8b355063c0`.

## 3. Quality report и отрицательный контроль

[Quality report](evidence/ci-artifacts/model-quality/quality.json) · [Reverse report](evidence/ci-artifacts/model-quality/quality-reverse.json) · [Лог отказа](evidence/ci-artifacts/model-quality/quality-reverse.log).

Фрагменты вывода команд из `lab2/`:

```bash
.venv/bin/python scripts/evaluate.py --artifact-dir artifacts
```

```text
  "ranking_mode": "normal",
  "mrr": 0.9375,
  "recall_at_3": 1.0,
```

```bash
.venv/bin/python scripts/evaluate.py --artifact-dir artifacts --ranking-mode reverse
```

```text
  "ranking_mode": "reverse",
  "mrr": 0.0,
  "recall_at_3": 0.0,
quality gate failed
```

`exit_code=1` — кандидат заблокирован.

## 4. `/meta` из staging и production

Staging — [полный smoke report](evidence/ci-artifacts/staging-delivery/staging-normal/smoke.json):

```json
{
  "service": "runbook-search-api",
  "service_version": "1.2.0",
  "build_revision": "bb5aab86a1479b3acac1034cbf2385655db6bc58",
  "image_digest": "sha256:f1f7db764524e5419376dd23e3c7b696ae838711040675a54d55fb8b355063c0",
  "environment": "staging",
  "ranking_mode": "normal",
  "index_version": "58431e4d09c7",
  "model_type": "tfidf-word-char-cosine",
  "documents": 12
}
```

Production после rollback — [полный smoke report](evidence/ci-artifacts/production-delivery/production-reverse/smoke-restored.json):

```json
{
  "service": "runbook-search-api",
  "service_version": "1.2.0",
  "build_revision": "bb5aab86a1479b3acac1034cbf2385655db6bc58",
  "image_digest": "sha256:f1f7db764524e5419376dd23e3c7b696ae838711040675a54d55fb8b355063c0",
  "environment": "production",
  "ranking_mode": "normal",
  "index_version": "58431e4d09c7",
  "model_type": "tfidf-word-char-cosine",
  "documents": 12
}
```

## 5. Deployment image: один digest

```bash
kubectl --context=itmo-student-13 -n itmo-student-13 --request-timeout=20s get deploy oleinikov-search-staging-mlops-search oleinikov-search-prod-mlops-search -o 'jsonpath={range .items[*]}{.metadata.name}{"\n"}{.spec.template.spec.containers[0].image}{"\n"}{end}'
```

```text
oleinikov-search-staging-mlops-search
docker.io/ndreuu/oleinikov-iris@sha256:f1f7db764524e5419376dd23e3c7b696ae838711040675a54d55fb8b355063c0
oleinikov-search-prod-mlops-search
docker.io/ndreuu/oleinikov-iris@sha256:f1f7db764524e5419376dd23e3c7b696ae838711040675a54d55fb8b355063c0
```

## 6. `helm history` до и после плохого release

До — [вывод `helm history -o json` из CI](evidence/ci-artifacts/production-delivery/production-reverse/history-before.json):

```json
[{"revision":1,"updated":"2026-11-22T14:44:01.849399948Z","status":"deployed","chart":"mlops-search-0.1.0","app_version":"1.2.0","description":"Install complete"}]
```

После:

```bash
env HELM_DRIVER=configmap helm history oleinikov-search-prod --kube-context itmo-student-13 -n itmo-student-13
```

```text
REVISION	UPDATED                 	STATUS    	CHART             	APP VERSION	DESCRIPTION
1       	Sun Nov 22 14:44:01 2026	superseded	mlops-search-0.1.0	1.2.0      	Install complete
2       	Sun Nov 22 14:44:40 2026	superseded	mlops-search-0.1.0	1.2.0      	Upgrade complete
3       	Sun Nov 22 14:45:04 2026	deployed  	mlops-search-0.1.0	1.2.0      	Rollback to 1
```

## 7. Failed semantic smoke → rollback → повторная проверка

[Failed smoke](evidence/ci-artifacts/production-delivery/production-reverse/smoke.json) · [Rollback](evidence/ci-artifacts/production-delivery/production-reverse/rollback.log) · [Успешный smoke](evidence/ci-artifacts/production-delivery/production-reverse/smoke-restored.json).

Команда CI и фрагмент вывода:

```bash
bash scripts/deploy.sh oleinikov-search-prod production "$IMAGE_REPOSITORY" "$IMAGE_DIGEST" "$GITHUB_SHA" reverse
```

```text
semantic smoke failed
Rolling back oleinikov-search-prod to good revision 1
Rollback was a success! Happy Helming!
Reverse candidate failed semantic smoke; rollback restored rankingMode=normal
```

Повторный smoke: `actual_top=doc-rollback`, `ranking_mode=normal`, `passed=true`.

## 8. Почему readiness недостаточно

При `rankingMode=reverse` `/readyz` остаётся `ready`, но поиск возвращает неверный top result. Semantic smoke проверяет правильность результата.
