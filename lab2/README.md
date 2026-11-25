# Лабораторная работа №2. Runbook Search CI/CD

## 1. Репозиторий и pipeline

- [Публичный репозиторий](https://github.com/ndreuu/mlops).
- [Успешный pipeline](https://github.com/ndreuu/mlops/actions/runs/45608006169/attempts/2) — `success`.

## 2. Image

- Repository: `docker.io/ndreuu/oleinikov-iris`.
- Tag: `search-2e56ca6914514e5c4a3648a7f20c2a39e970b1ea`.
- Digest: `sha256:d1da5b43a93bc61501770856f4dba24f619046d0bf4cdf8a9e608b8634807095`.

## 3. Quality report и лог заблокированного reverse-кандидата

[Quality report](evidence/ci-2026-11-25/model-quality/quality.json) · [Reverse report](evidence/ci-2026-11-25/model-quality/quality-reverse.json) · [Лог отказа](evidence/ci-2026-11-25/model-quality/quality-reverse.log).

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

Staging — [полный smoke report](evidence/ci-2026-11-25/staging-delivery/staging-normal/smoke.json):

```json
{
  "service": "runbook-search-api",
  "service_version": "1.2.0",
  "build_revision": "2e56ca6914514e5c4a3648a7f20c2a39e970b1ea",
  "image_digest": "sha256:d1da5b43a93bc61501770856f4dba24f619046d0bf4cdf8a9e608b8634807095",
  "environment": "staging",
  "ranking_mode": "normal",
  "index_version": "58431e4d09c7",
  "model_type": "tfidf-word-char-cosine",
  "documents": 12
}
```

Production после rollback — [полный smoke report](evidence/ci-2026-11-25/production-delivery/production-reverse/smoke-restored.json):

```json
{
  "service": "runbook-search-api",
  "service_version": "1.2.0",
  "build_revision": "2e56ca6914514e5c4a3648a7f20c2a39e970b1ea",
  "image_digest": "sha256:d1da5b43a93bc61501770856f4dba24f619046d0bf4cdf8a9e608b8634807095",
  "environment": "production",
  "ranking_mode": "normal",
  "index_version": "58431e4d09c7",
  "model_type": "tfidf-word-char-cosine",
  "documents": 12
}
```

## 5. Deployment image двух окружений с одним digest

```bash
kubectl --context=itmo-student-13 -n itmo-student-13 --request-timeout=20s get deploy oleinikov-search-staging-mlops-search oleinikov-search-prod-mlops-search -o 'jsonpath={range .items[*]}{.metadata.name}{"\n"}{.spec.template.spec.containers[0].image}{"\n"}{end}'
```

```text
oleinikov-search-staging-mlops-search
docker.io/ndreuu/oleinikov-iris@sha256:d1da5b43a93bc61501770856f4dba24f619046d0bf4cdf8a9e608b8634807095
oleinikov-search-prod-mlops-search
docker.io/ndreuu/oleinikov-iris@sha256:d1da5b43a93bc61501770856f4dba24f619046d0bf4cdf8a9e608b8634807095
```

## 6. `helm history` до и после плохого release

```bash
HELM_DRIVER=configmap helm history oleinikov-search-prod -n itmo-student-13 -o json
```

[До плохого release](evidence/ci-2026-11-25/production-delivery/production-reverse/history-before.json) → [после rollback](evidence/ci-2026-11-25/production-delivery/production-reverse/history-after.json).

Последние ревизии из вывода (revision, status, description):

```text
До:
4  deployed    Upgrade complete
После:
4  superseded  Upgrade complete
5  superseded  Upgrade complete
6  deployed    Rollback to 4
```

## 7. Failed semantic smoke → rollback → повторная проверка

[Failed smoke](evidence/ci-2026-11-25/production-delivery/production-reverse/smoke.json) · [Rollback](evidence/ci-2026-11-25/production-delivery/production-reverse/rollback.log) · [Успешный smoke](evidence/ci-2026-11-25/production-delivery/production-reverse/smoke-restored.json).

```bash
bash scripts/deploy.sh oleinikov-search-prod production "$IMAGE_REPOSITORY" "$IMAGE_DIGEST" "$GITHUB_SHA" reverse
```

```text
semantic smoke failed
Rolling back oleinikov-search-prod to good revision 4
Rollback was a success! Happy Helming!
Reverse candidate failed semantic smoke; rollback restored rankingMode=normal
```

Reverse: `/readyz=ready`, `actual_top=doc-security`, `passed=false`.

После rollback: `actual_top=doc-rollback`, `ranking_mode=normal`, `passed=true`. [Лог CI](evidence/ci-2026-11-25/acceptance.log).

## 8. Почему readiness недостаточно

При `rankingMode=reverse` `/readyz` остаётся `ready`, но поиск возвращает неверный top result. Semantic smoke проверяет правильность результата.
