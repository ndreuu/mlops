# Лабораторная работа №2. Runbook Search CI/CD

## 0. Чеклист

- [x] Индекс собран, API и тесты работают — [1](#local).
- [x] MRR ≥ 0.85, Recall@3 ≥ 0.90; reverse-кандидат заблокирован — [2](#quality).
- [x] Индекс входит в image, runtime — non-root/read-only — [3](#container).
- [x] Helm отклоняет пустой и некорректный digest — [4](#helm).
- [x] CI собирает и публикует образ — [5](#ci).
- [x] Staging: Helm test и semantic smoke — [6](#staging).
- [x] Production после manual approval; digest совпадает со staging — [7](#production).
- [x] Reverse release → failed semantic smoke → rollback → normal — [8](#rollback).

[Pipeline](https://github.com/ndreuu/mlops/actions/runs/45033904297) · [Workflow](../.github/workflows/lab2.yml) · [Docker Hub](https://hub.docker.com/r/ndreuu/oleinikov-iris)

Namespace: `itmo-student-13` из персонального kubeconfig. `HELM_DRIVER=configmap`.
Python и kubectl — Mac; Docker Compose — учебная ВМ; deployment — GitHub Actions.
Команды приложения выполняются из `lab2/`, чтение CI artifacts — из `lab2/evidence/ci-artifacts/`.

Image: `docker.io/ndreuu/oleinikov-iris:search-bb5aab86a1479b3acac1034cbf2385655db6bc58`.
Digest: `sha256:f1f7db764524e5419376dd23e3c7b696ae838711040675a54d55fb8b355063c0`.

<a id="local"></a>

## 1. Локальный запуск

```bash
.venv/bin/python scripts/build_index.py --output artifacts
```

```text
{"artifact_schema": "runbook-search-index/v1", "model_name": "runbook-hybrid-tfidf", "model_type": "tfidf-word-char-cosine", "index_version": "58431e4d09c7", "corpus_sha256": "58431e4d09c73dff690feb751eea4d1d09f7d6a61d1461ad4b7f28e223686757", "documents": 12, "features": 4068}
```

Результат pytest (фрагмент):

```bash
.venv/bin/python -m pytest -q
```

```text
..                                                                       [100%]
2 passed, 1 warning in 2.91s
```

Полные логи: [local.txt](evidence/local.txt).

```bash
.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 18082
```

```text
INFO:     Started server process [58258]
INFO:     Waiting for application startup.
{"event": "service_ready", "service": "runbook-search-api", "index_version": "58431e4d09c7", "documents": 12}
INFO:     Application startup complete.
```

```bash
curl -fsS http://127.0.0.1:18082/readyz
```

```text
{"status":"ready","index_version":"58431e4d09c7","documents":12}
```

Запуск uvicorn, поиск, рекомендации и `/metrics`: [local.txt](evidence/local.txt).

<a id="quality"></a>

## 2. Quality gate

Выводы ниже — фрагменты; полные отчёты сохранены в [CI artifacts](evidence/ci-artifacts/).

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

`exit_code=1` — ожидаемый отказ.

<a id="container"></a>

## 3. Docker

В [Dockerfile](Dockerfile) добавлен `COPY --from=builder /build/artifacts artifacts` с владельцем `10001:app`.

```bash
docker compose -p oleinikov-lab2 up -d --build search
```

Полный вывод build и smoke: [container.txt](evidence/container.txt).

```bash
docker compose -p oleinikov-lab2 ps
```

```text
NAME                      IMAGE                    COMMAND                  SERVICE   CREATED         STATUS                   PORTS
oleinikov-lab2-search-1   oleinikov-search:local   "uvicorn app.main:ap…"   search    8 seconds ago   Up 6 seconds (healthy)   127.0.0.1:18080->8000/tcp
```

```bash
docker inspect oleinikov-lab2-search-1 --format 'User={{.Config.User}} ReadonlyRootfs={{.HostConfig.ReadonlyRootfs}} SecurityOpt={{json .HostConfig.SecurityOpt}}'
```

```text
User=10001 ReadonlyRootfs=true SecurityOpt=["no-new-privileges:true"]
```

```bash
curl -fsS http://127.0.0.1:18080/meta
```

```text
{"service":"runbook-search-api","service_version":"1.2.0-local","build_revision":"working-tree","image_digest":"local-build","environment":"local","ranking_mode":"normal","index_version":"58431e4d09c7","model_type":"tfidf-word-char-cosine","documents":12}
```

```bash
curl -fsS http://127.0.0.1:18080/metrics
```

```text
# HELP http_requests_total Total HTTP requests processed.
# TYPE http_requests_total counter
http_requests_total 4
# HELP search_requests_total Total retrieval requests processed.
# TYPE search_requests_total counter
search_requests_total 1
# HELP search_request_duration_seconds_sum Cumulative retrieval latency.
# TYPE search_request_duration_seconds_sum counter
search_request_duration_seconds_sum 0.004432
# HELP search_index_loaded Whether the search index is loaded.
# TYPE search_index_loaded gauge
search_index_loaded 1
```

```bash
docker compose -p oleinikov-lab2 down
```

```text
 Container oleinikov-lab2-search-1 Stopping
 Container oleinikov-lab2-search-1 Stopped
 Container oleinikov-lab2-search-1 Removing
 Container oleinikov-lab2-search-1 Removed
 Network oleinikov-lab2_default Removing
 Network oleinikov-lab2_default Removed
```

<a id="helm"></a>

## 4. Helm: digest обязателен

```bash
helm template invalid helm/mlops-search
```

```text
Error: execution error at (mlops-search/templates/deployment.yaml:24:28): image.digest is required

Use --debug flag to render out invalid YAML
```

`exit_code=1` — ожидаемый отказ.

```bash
helm template invalid helm/mlops-search --set image.digest=sha256:bad
```

```text
Error: execution error at (mlops-search/templates/deployment.yaml:24:28): image.digest must be sha256 followed by 64 lowercase hex characters

Use --debug flag to render out invalid YAML
```

`exit_code=1` — ожидаемый отказ.

```bash
helm lint helm/mlops-search --set-string image.digest=sha256:f1f7db764524e5419376dd23e3c7b696ae838711040675a54d55fb8b355063c0 --set-string image.repository=docker.io/ndreuu/oleinikov-iris --set-string environment=staging --set-string buildRevision=bb5aab86a1479b3acac1034cbf2385655db6bc58
```

```text
==> Linting helm/mlops-search
[INFO] Chart.yaml: icon is recommended

1 chart(s) linted, 0 chart(s) failed
```

Render с опубликованным digest (фрагмент):

```bash
helm template oleinikov-search-staging helm/mlops-search -n itmo-student-13 --set-string image.digest=sha256:f1f7db764524e5419376dd23e3c7b696ae838711040675a54d55fb8b355063c0 --set-string image.repository=docker.io/ndreuu/oleinikov-iris --set-string environment=staging --set-string buildRevision=bb5aab86a1479b3acac1034cbf2385655db6bc58
```

```text
kind: ConfigMap
kind: Service
  type: ClusterIP
kind: Deployment
        runAsNonRoot: true
          image: "docker.io/ndreuu/oleinikov-iris@sha256:f1f7db764524e5419376dd23e3c7b696ae838711040675a54d55fb8b355063c0"
          readinessProbe:
              path: /readyz
          livenessProbe:
              path: /livez
            readOnlyRootFilesystem: true
kind: Pod
    runAsNonRoot: true
      image: curlimages/curl:8.15.0
        readOnlyRootFilesystem: true
```

[Chart](helm/mlops-search/), Service `ClusterIP`, readiness `/readyz`, liveness `/livez`.

<a id="ci"></a>

## 5. CI/CD и registry

```bash
gh run view 45033904297 --repo ndreuu/mlops --json status,conclusion,headSha,jobs,url --jq '{status,conclusion,headSha,url,jobs:[.jobs[]|{name,conclusion}]}'
```

```text
{"conclusion":"success","headSha":"bb5aab86a1479b3acac1034cbf2385655db6bc58","jobs":[{"conclusion":"success","name":"test-quality"},{"conclusion":"success","name":"build"},{"conclusion":"success","name":"deploy-staging"},{"conclusion":"success","name":"promote-production"}],"status":"completed","url":"https://github.com/ndreuu/mlops/actions/runs/45033904297"}
```

```bash
gh api repos/ndreuu/mlops/environments/production --jq '{name,protection_rules:[.protection_rules[]|{type,reviewers:[.reviewers[]?.reviewer.login]}],deployment_branch_policy}'
```

```text
{"deployment_branch_policy":{"custom_branch_policies":true,"protected_branches":false},"name":"production","protection_rules":[{"reviewers":["ndreuu"],"type":"required_reviewers"},{"reviewers":[],"type":"branch_policy"}]}
```

```bash
gh api repos/ndreuu/mlops/actions/runs/45033904297/approvals --jq '[.[]|{state,user:.user.login,environments:[.environments[].name]}]'
```

```text
[{"environments":["production"],"state":"approved","user":"ndreuu"}]
```

```bash
gh secret list --repo ndreuu/mlops --env registry
```

```text
DOCKERHUB_TOKEN	2026-11-22T14:37:53Z
```

```bash
gh secret list --repo ndreuu/mlops --env staging
```

```text
KUBE_CONFIG_B64	2026-11-22T14:20:30Z
```

```bash
gh secret list --repo ndreuu/mlops --env production
```

```text
KUBE_CONFIG_B64	2026-11-22T14:20:30Z
```

```bash
.venv/bin/python -c 'import json,urllib.request; d=json.load(urllib.request.urlopen("https://hub.docker.com/v2/repositories/ndreuu/oleinikov-iris/tags/search-bb5aab86a1479b3acac1034cbf2385655db6bc58/",timeout=20)); print(json.dumps({k:d[k] for k in ("name","digest")},indent=2))'
```

```text
{
  "name": "search-bb5aab86a1479b3acac1034cbf2385655db6bc58",
  "digest": "sha256:f1f7db764524e5419376dd23e3c7b696ae838711040675a54d55fb8b355063c0"
}
```

```bash
.venv/bin/python scripts/check_registry.py docker.io/ndreuu/oleinikov-iris sha256:f1f7db764524e5419376dd23e3c7b696ae838711040675a54d55fb8b355063c0
```

```text
{"repository": "docker.io/ndreuu/oleinikov-iris", "digest": "sha256:f1f7db764524e5419376dd23e3c7b696ae838711040675a54d55fb8b355063c0", "anonymous_pull": true}
```

<a id="staging"></a>

## 6. Staging

```bash
kubectl --context=itmo-student-13 -n itmo-student-13 --request-timeout=20s get cm,deploy,pods,svc -l app.kubernetes.io/instance=oleinikov-search-staging
```

```text
NAME                                              DATA   AGE
configmap/oleinikov-search-staging-mlops-search   6      7m4s

NAME                                                    READY   UP-TO-DATE   AVAILABLE   AGE
deployment.apps/oleinikov-search-staging-mlops-search   1/1     1            1           7m4s

NAME                                                         READY   STATUS    RESTARTS   AGE
pod/oleinikov-search-staging-mlops-search-67995c65d7-44l8c   1/1     Running   0          7m4s

NAME                                            TYPE        CLUSTER-IP       EXTERNAL-IP   PORT(S)   AGE
service/oleinikov-search-staging-mlops-search   ClusterIP   10.102.198.208   <none>        80/TCP    7m4s
```

```bash
cat staging-delivery/staging-normal/helm-test.log
```

```text
NAME: oleinikov-search-staging
LAST DEPLOYED: Sun Nov 22 14:40:16 2026
NAMESPACE: itmo-student-13
STATUS: deployed
REVISION: 1
TEST SUITE:     oleinikov-search-staging-mlops-search-test
Last Started:   Sun Nov 22 14:40:58 2026
Last Completed: Sun Nov 22 14:41:08 2026
Phase:          Succeeded
NOTES:
Use port-forward to inspect the release:
  kubectl -n itmo-student-13 port-forward service/oleinikov-search-staging-mlops-search 8080:80
```

```bash
.venv/bin/python scripts/verify_release.py --release oleinikov-search-staging --namespace itmo-student-13 --expected-digest sha256:f1f7db764524e5419376dd23e3c7b696ae838711040675a54d55fb8b355063c0 --expected-revision bb5aab86a1479b3acac1034cbf2385655db6bc58 --expected-environment staging
```

```text
{
  "release": "oleinikov-search-staging",
  "ready": {
    "status": "ready",
    "index_version": "58431e4d09c7",
    "documents": 12
  },
  "meta": {
    "service": "runbook-search-api",
    "service_version": "1.2.0",
    "build_revision": "bb5aab86a1479b3acac1034cbf2385655db6bc58",
    "image_digest": "sha256:f1f7db764524e5419376dd23e3c7b696ae838711040675a54d55fb8b355063c0",
    "environment": "staging",
    "ranking_mode": "normal",
    "index_version": "58431e4d09c7",
    "model_type": "tfidf-word-char-cosine",
    "documents": 12
  },
  "expected_top": "doc-rollback",
  "actual_top": "doc-rollback",
  "checks": {
    "ready": true,
    "top_result": true,
    "image_digest": true,
    "build_revision": true,
    "environment": true,
    "ranking_mode": true,
    "index_version": true,
    "request_id": true
  },
  "passed": true
}
```

Helm test и deployment logs: [delivery.txt](evidence/delivery.txt), [CI artifacts](evidence/ci-artifacts/).

<a id="production"></a>

## 7. Production и один digest

```bash
kubectl --context=itmo-student-13 -n itmo-student-13 --request-timeout=20s get cm,deploy,pods,svc -l app.kubernetes.io/instance=oleinikov-search-prod
```

```text
NAME                                           DATA   AGE
configmap/oleinikov-search-prod-mlops-search   6      3m26s

NAME                                                 READY   UP-TO-DATE   AVAILABLE   AGE
deployment.apps/oleinikov-search-prod-mlops-search   1/1     1            1           3m25s

NAME                                                     READY   STATUS    RESTARTS   AGE
pod/oleinikov-search-prod-mlops-search-b5d97df76-bb4wg   1/1     Running   0          2m23s

NAME                                         TYPE        CLUSTER-IP      EXTERNAL-IP   PORT(S)   AGE
service/oleinikov-search-prod-mlops-search   ClusterIP   10.106.28.139   <none>        80/TCP    3m26s
```

```bash
cat production-delivery/production-normal/helm-test.log
```

```text
NAME: oleinikov-search-prod
LAST DEPLOYED: Sun Nov 22 14:44:01 2026
NAMESPACE: itmo-student-13
STATUS: deployed
REVISION: 1
TEST SUITE:     oleinikov-search-prod-mlops-search-test
Last Started:   Sun Nov 22 14:44:16 2026
Last Completed: Sun Nov 22 14:44:24 2026
Phase:          Succeeded
NOTES:
Use port-forward to inspect the release:
  kubectl -n itmo-student-13 port-forward service/oleinikov-search-prod-mlops-search 8080:80
```

```bash
.venv/bin/python scripts/verify_release.py --release oleinikov-search-prod --namespace itmo-student-13 --expected-digest sha256:f1f7db764524e5419376dd23e3c7b696ae838711040675a54d55fb8b355063c0 --expected-revision bb5aab86a1479b3acac1034cbf2385655db6bc58 --expected-environment production
```

```text
{
  "release": "oleinikov-search-prod",
  "ready": {
    "status": "ready",
    "index_version": "58431e4d09c7",
    "documents": 12
  },
  "meta": {
    "service": "runbook-search-api",
    "service_version": "1.2.0",
    "build_revision": "bb5aab86a1479b3acac1034cbf2385655db6bc58",
    "image_digest": "sha256:f1f7db764524e5419376dd23e3c7b696ae838711040675a54d55fb8b355063c0",
    "environment": "production",
    "ranking_mode": "normal",
    "index_version": "58431e4d09c7",
    "model_type": "tfidf-word-char-cosine",
    "documents": 12
  },
  "expected_top": "doc-rollback",
  "actual_top": "doc-rollback",
  "checks": {
    "ready": true,
    "top_result": true,
    "image_digest": true,
    "build_revision": true,
    "environment": true,
    "ranking_mode": true,
    "index_version": true,
    "request_id": true
  },
  "passed": true
}
```

```bash
kubectl --context=itmo-student-13 -n itmo-student-13 --request-timeout=20s get deploy oleinikov-search-staging-mlops-search oleinikov-search-prod-mlops-search -o 'jsonpath={range .items[*]}{.metadata.name}{"\n"}{.spec.template.spec.containers[0].image}{"\n"}{end}'
```

```text
oleinikov-search-staging-mlops-search
docker.io/ndreuu/oleinikov-iris@sha256:f1f7db764524e5419376dd23e3c7b696ae838711040675a54d55fb8b355063c0
oleinikov-search-prod-mlops-search
docker.io/ndreuu/oleinikov-iris@sha256:f1f7db764524e5419376dd23e3c7b696ae838711040675a54d55fb8b355063c0
```

```bash
kubectl --context=itmo-student-13 -n itmo-student-13 --request-timeout=20s get pods -l 'app.kubernetes.io/name=mlops-search,app.kubernetes.io/instance in (oleinikov-search-staging,oleinikov-search-prod)' -o 'jsonpath={range .items[*]}{.metadata.name}{"\n"}{.status.containerStatuses[0].imageID}{"\n"}{end}'
```

```text
oleinikov-search-prod-mlops-search-b5d97df76-bb4wg
docker.io/ndreuu/oleinikov-iris@sha256:f1f7db764524e5419376dd23e3c7b696ae838711040675a54d55fb8b355063c0
oleinikov-search-staging-mlops-search-67995c65d7-44l8c
docker.io/ndreuu/oleinikov-iris@sha256:f1f7db764524e5419376dd23e3c7b696ae838711040675a54d55fb8b355063c0
```

<a id="rollback"></a>

## 8. Проверка rollback

Выводы до и во время плохого релиза сохранены самим CI; `cat` читает скачанные artifacts.

Команда CI и фрагмент её вывода (`IMAGE_DIGEST`, `GITHUB_SHA` — из build этого pipeline):

```bash
bash scripts/deploy.sh oleinikov-search-prod production "$IMAGE_REPOSITORY" "$IMAGE_DIGEST" "$GITHUB_SHA" reverse
```

```text
semantic smoke failed
Rolling back oleinikov-search-prod to good revision 1
Rollback was a success! Happy Helming!
Reverse candidate failed semantic smoke; rollback restored rankingMode=normal
```

```bash
cat production-delivery/production-reverse/history-before.json
```

```text
[{"revision":1,"updated":"2026-11-22T14:44:01.849399948Z","status":"deployed","chart":"mlops-search-0.1.0","app_version":"1.2.0","description":"Install complete"}]
```

```bash
cat production-delivery/production-reverse/smoke.json
```

```text
{
  "release": "oleinikov-search-prod",
  "ready": {
    "status": "ready",
    "index_version": "58431e4d09c7",
    "documents": 12
  },
  "meta": {
    "service": "runbook-search-api",
    "service_version": "1.2.0",
    "build_revision": "bb5aab86a1479b3acac1034cbf2385655db6bc58",
    "image_digest": "sha256:f1f7db764524e5419376dd23e3c7b696ae838711040675a54d55fb8b355063c0",
    "environment": "production",
    "ranking_mode": "reverse",
    "index_version": "58431e4d09c7",
    "model_type": "tfidf-word-char-cosine",
    "documents": 12
  },
  "expected_top": "doc-rollback",
  "actual_top": "doc-security",
  "checks": {
    "ready": true,
    "top_result": false,
    "image_digest": true,
    "build_revision": true,
    "environment": true,
    "ranking_mode": true,
    "index_version": true,
    "request_id": true
  },
  "passed": false
}
```

```bash
cat production-delivery/production-reverse/rollback.log
```

```text
Rollback was a success! Happy Helming!
```

```bash
cat production-delivery/production-reverse/smoke-restored.json
```

```text
{
  "release": "oleinikov-search-prod",
  "ready": {
    "status": "ready",
    "index_version": "58431e4d09c7",
    "documents": 12
  },
  "meta": {
    "service": "runbook-search-api",
    "service_version": "1.2.0",
    "build_revision": "bb5aab86a1479b3acac1034cbf2385655db6bc58",
    "image_digest": "sha256:f1f7db764524e5419376dd23e3c7b696ae838711040675a54d55fb8b355063c0",
    "environment": "production",
    "ranking_mode": "normal",
    "index_version": "58431e4d09c7",
    "model_type": "tfidf-word-char-cosine",
    "documents": 12
  },
  "expected_top": "doc-rollback",
  "actual_top": "doc-rollback",
  "checks": {
    "ready": true,
    "top_result": true,
    "image_digest": true,
    "build_revision": true,
    "environment": true,
    "ranking_mode": true,
    "index_version": true,
    "request_id": true
  },
  "passed": true
}
```

```bash
env HELM_DRIVER=configmap helm history oleinikov-search-prod --kube-context itmo-student-13 -n itmo-student-13
```

```text
REVISION	UPDATED                 	STATUS    	CHART             	APP VERSION	DESCRIPTION
1       	Sun Nov 22 14:44:01 2026	superseded	mlops-search-0.1.0	1.2.0      	Install complete
2       	Sun Nov 22 14:44:40 2026	superseded	mlops-search-0.1.0	1.2.0      	Upgrade complete
3       	Sun Nov 22 14:45:04 2026	deployed  	mlops-search-0.1.0	1.2.0      	Rollback to 1
```

```bash
env HELM_DRIVER=configmap helm get values oleinikov-search-prod --kube-context itmo-student-13 -n itmo-student-13 -o json
```

```text
{"buildRevision":"bb5aab86a1479b3acac1034cbf2385655db6bc58","environment":"production","image":{"digest":"sha256:f1f7db764524e5419376dd23e3c7b696ae838711040675a54d55fb8b355063c0","repository":"docker.io/ndreuu/oleinikov-iris"},"rankingMode":"normal"}
```

## 9. Почему readiness недостаточно

При `rankingMode=reverse` индекс загружен и `/readyz` отвечает `ready`, но первый результат поиска неверный. Semantic smoke проверяет ожидаемый документ и запускает rollback.

Полные команды, время и коды завершения: [commands.json](evidence/commands.json). Полный [CI log](evidence/ci-artifacts/pipeline.log).
