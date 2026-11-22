# Лабораторная работа №1. Iris: от модели до Kubernetes

## 0. Что получилось

1. Локально работает API (`/health`, `/predict`).
  - [раздел 3](#local-api)
2. Образ в Docker Hub (или другом registry): `docker.io/ndreuu/oleinikov-iris:v1`.
  - [раздел 6](#registry)
3. В namespace `itmo-student-13` созданы **свои** ConfigMap, Deployment и Service с уникальным префиксом.
  - [раздел 9](#deployment)
4. Проверка через `kubectl port-forward` и `curl`.
  - [раздел 10](#port-forward)

### 0.1 Чеклист сдачи

- [x] `train.py` + локальный `uvicorn` работают — [команды, журнал и HTTP 200](#local-api).
- [x] Образ собран и запушен: `docker.io/ndreuu/oleinikov-iris:v1` — [build](#docker-build), [push, digest и публичность](#registry).
- [x] `pass` инициализирован, `docker login` успешен — [Password store initialized и Login Succeeded](#docker-auth).
- [x] Манифест с уникальными именами, без ошибок шаблона — [манифест и согласование полей](#manifest), [dry-run](#dry-run).
- [x] `kubectl apply --dry-run=server` без ошибок — [три объекта и код 0](#dry-run).
- [x] Объекты созданы в назначенном `itmo-student-13` — [ConfigMap, Deployment, Pod, Service](#deployment). Отличие от `mlops-students` обосновано [персональным контекстом и RBAC](#access).
- [x] Через `port-forward`: `/health` → `ready`, setosa → `0`, virginica → `2` — [команды curl и фактические ответы](#port-forward).

<a id="access"></a>

## 1. Доступ к кластеру: `.kube`, kubectl, kubecm

```bash
kubectl version --client=true
```

```text
Client Version: v1.37.2
Kustomize Version: v5.8.1
```


```bash
kubecm version
```

```text
Version: 0.36.0
GoOs: darwin
GoArch: arm64
```

```bash
kubecm list
```

```text
┌────────────┬────────────────────┬─────────────────┬────────────────────┬───────────────────────────────┬────────────────────┐
│   CURRENT  │        NAME        │     CLUSTER     │        USER        │             SERVER            │      Namespace     │
╞════════════╪════════════════════╪═════════════════╪════════════════════╪═══════════════════════════════╪════════════════════╡
│      *     │   itmo-student-13  │   stud-cluster  │   itmo-student-13  │   https://37.18.117.109:6443  │   itmo-student-13  │
└────────────┴────────────────────┴─────────────────┴────────────────────┴───────────────────────────────┴────────────────────┘

Cluster check succeeded!
Kubernetes version v1.36.4
Kubernetes master is running at https://37.18.117.109:6443
(Error reporting can be ignored and does not affect usage.)
```

```bash
stat -f '%Sp %N' /Users/andrew/.kube /Users/andrew/.kube/config /Users/andrew/.kube/itmo-student-13.kubeconfig
```

```text
drwx------ /Users/andrew/.kube
-rw------- /Users/andrew/.kube/config
-rw------- /Users/andrew/.kube/itmo-student-13.kubeconfig
```

```bash
kubectl config current-context
```

```text
itmo-student-13
```

```bash
kubectl config view --minify -o 'jsonpath={.contexts[0].context.namespace}{"\n"}'
```

```text
itmo-student-13
```

```bash
kubectl --context=itmo-student-13 -n itmo-student-13 auth can-i create deployments
```

```text
yes
```


```bash
kubectl --context=itmo-student-13 -n itmo-student-13 auth can-i create services
```

```text
yes
```


```bash
kubectl --context=itmo-student-13 -n itmo-student-13 auth can-i create configmaps
```

```text
yes
```

Проверка namespace из общей методички (ожидаемый отказ):

```bash
kubectl --context=itmo-student-13 -n mlops-students auth can-i create deployments
```

```text
no
```

<a id="python-env"></a>

## 2. Python-окружение

```bash
.venv/bin/python --version
```

```text
Python 3.12.16
```

```bash
.venv/bin/python -c 'from importlib.metadata import version; [print(f"{p}=={version(p)}") for p in ("fastapi","uvicorn","scikit-learn","joblib")]'
```

```text
fastapi==0.116.1
uvicorn==0.35.0
scikit-learn==1.7.1
joblib==1.5.1
```

<a id="local-api"></a>

## 3. Обучение и локальный Uvicorn

```bash
.venv/bin/python train.py
```

```bash
ls -lh model.joblib
```

```text
-rw-r--r--@ 1 andrew  staff    93K Nov 22 13:17 model.joblib
```

```bash
.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000
```

```text
INFO:     Started server process [52699]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
INFO:     127.0.0.1:50206 - "GET /live HTTP/1.1" 200 OK
INFO:     127.0.0.1:50207 - "GET /health HTTP/1.1" 200 OK
INFO:     127.0.0.1:50208 - "POST /predict HTTP/1.1" 200 OK
INFO:     127.0.0.1:50209 - "POST /predict HTTP/1.1" 200 OK
INFO:     127.0.0.1:50210 - "POST /predict HTTP/1.1" 200 OK
INFO:     Shutting down
INFO:     Waiting for application shutdown.
INFO:     Application shutdown complete.
INFO:     Finished server process [52699]
```

```bash
curl -fsS --max-time 15 -w '
HTTP %{http_code}
' http://127.0.0.1:8000/live
```

```text
{"status":"alive"}
HTTP 200
```

```bash
curl -fsS --max-time 15 -w '
HTTP %{http_code}
' http://127.0.0.1:8000/health
```

```text
{"status":"ready","model_version":"iris-v1"}
HTTP 200
```

```bash
curl -fsS --max-time 15 -w '
HTTP %{http_code}
' -X POST http://127.0.0.1:8000/predict -H 'content-type: application/json' -d '{"features":[5.1,3.5,1.4,0.2]}'
```

```text
{"class_id":0,"model_version":"iris-v1"}
HTTP 200
```

```bash
curl -fsS --max-time 15 -w '
HTTP %{http_code}
' -X POST http://127.0.0.1:8000/predict -H 'content-type: application/json' -d '{"features":[7.0,3.2,4.7,1.4]}'
```

```text
{"class_id":1,"model_version":"iris-v1"}
HTTP 200
```

```bash
curl -fsS --max-time 15 -w '
HTTP %{http_code}
' -X POST http://127.0.0.1:8000/predict -H 'content-type: application/json' -d '{"features":[6.3,3.3,6.0,2.5]}'
```

```text
{"class_id":2,"model_version":"iris-v1"}
HTTP 200
```

> Вывод: локальное обучение и API работают; `/health` => `ready`, `/predict` => `0`, `1`, `2` для setosa, versicolor и virginica.

<a id="docker-auth"></a>

## 4. `pass`, credential helper и Docker login

```bash
docker version --format 'Client={{.Client.Version}} Server={{.Server.Version}}'
```

```text
Client=29.9.3 Server=29.9.3
```

```bash
which docker-credential-pass
```

```text
/usr/local/bin/docker-credential-pass
```

```bash
python3 -c 'import json,pathlib; c=json.loads((pathlib.Path.home()/".docker/config.json").read_text()); print(json.dumps({"credsStore":c.get("credsStore")}))'
```

```text
{"credsStore": "pass"}
```

```bash
cat /home/oleinikov/.password-store/.gpg-id
```

```text
F2DA2108503EB840B93109E2DC0D45A1EF6B420D
```

```bash
pass init F2DA2108503EB840B93109E2DC0D45A1EF6B420D
```

```text
Password store initialized for F2DA2108503EB840B93109E2DC0D45A1EF6B420D
```

```bash
pass ls
```

```text
Password Store
└── docker-credential-helpers
    ├── aHR0cHM6Ly9pbmRleC5kb2NrZXIuaW8vdjEv
    │   └── ndreuu
    ├── aHR0cHM6Ly9pbmRleC5kb2NrZXIuaW8vdjEvYWNjZXNzLXRva2Vu
    │   └── ndreuu
    └── aHR0cHM6Ly9pbmRleC5kb2NrZXIuaW8vdjEvcmVmcmVzaC10b2tlbg==
        └── ndreuu
```

```bash
docker-credential-pass list
```

```text
{"https://index.docker.io/v1/":"ndreuu","https://index.docker.io/v1/access-token":"ndreuu","https://index.docker.io/v1/refresh-token":"ndreuu"}
```

```bash
docker login
```

```text
Authenticating with existing credentials... [Username: ndreuu]

 Info -> To login with a different account, run 'docker logout' followed by 'docker login'


Login Succeeded
```

<a id="docker-build"></a>

## 5. Docker build и проверка контейнера

```bash
docker build --pull=false --progress=plain -t oleinikov-iris:proof-v1 .
```

```text
#0 building with "default" instance using docker driver

#1 [internal] load build definition from Dockerfile
#1 transferring dockerfile: 696B done
#1 DONE 0.1s

#2 [internal] load metadata for docker.io/library/python:3.12-slim
#2 ...

#3 [auth] library/python:pull token for registry-1.docker.io
#3 DONE 0.0s

#2 [internal] load metadata for docker.io/library/python:3.12-slim
#2 DONE 1.1s

#4 [internal] load .dockerignore
#4 transferring context: 2B done
#4 DONE 0.1s

#5 [builder 1/4] FROM docker.io/library/python:3.12-slim@sha256:5e2bdb1b0d542d5039cffb8181c65930093949194a65c365dfb1b0fe13a4fa5b
#5 DONE 0.0s

#6 [internal] load build context
#6 transferring context: 531B done
#6 DONE 0.1s

#7 [stage-1 4/9] COPY --from=builder /wheels /wheels
#7 CACHED

#8 [stage-1 6/9] RUN pip install --no-cache-dir --no-index --find-links=/wheels -r requirements.txt     && rm -rf /wheels
#8 CACHED

#9 [stage-1 5/9] COPY requirements.txt .
#9 CACHED

#10 [stage-1 8/9] COPY --chown=app:app train.py .
#10 CACHED

#11 [builder 2/4] WORKDIR /build
#11 CACHED

#12 [stage-1 7/9] COPY --chown=app:app app ./app
#12 CACHED

#13 [stage-1 2/9] RUN addgroup --system app && adduser --system --ingroup app --uid 10001 app
#13 CACHED

#14 [stage-1 3/9] WORKDIR /app
#14 CACHED

#15 [builder 3/4] COPY requirements.txt .
#15 CACHED

#16 [builder 4/4] RUN pip wheel --no-cache-dir --wheel-dir /wheels -r requirements.txt
#16 CACHED

#17 [stage-1 9/9] RUN python train.py
#17 CACHED

#18 exporting to image
#18 exporting layers done
#18 writing image sha256:3576c5eb3ed11a7c0a2d2451775c1bfb7cb58d43ffbfa4c095400b9196d311ae 0.0s done
#18 naming to docker.io/library/oleinikov-iris:proof-v1 0.1s done
#18 DONE 0.1s
```

```bash
docker image inspect docker.io/ndreuu/oleinikov-iris:v1 --format 'Tags={{json .RepoTags}}
ID={{.Id}}
Platform={{.Os}}/{{.Architecture}}
User={{.Config.User}}'
```

```text
Tags=["oleinikov-iris:proof-v1","oleinikov-iris:v1","ndreuu/oleinikov-iris:v1"]
ID=sha256:3576c5eb3ed11a7c0a2d2451775c1bfb7cb58d43ffbfa4c095400b9196d311ae
Platform=linux/amd64
User=10001
```

```bash
docker tag oleinikov-iris:proof-v1 docker.io/ndreuu/oleinikov-iris:v1
```

Контейнер запущен на ВМ, порт доступен через loopback ВМ `127.0.0.1:18000`:

```bash
docker run --detach --rm --name oleinikov-iris-proof -p 127.0.0.1:18000:8000 docker.io/ndreuu/oleinikov-iris:v1
```

```text
7319b05916fcd01aca5446743ca7a55815153cdfb2295b8c8f4fbb97d46166d4
```

```bash
curl -fsS --retry 10 --retry-all-errors --retry-delay 1 --max-time 15 -w '
HTTP %{http_code}
' http://127.0.0.1:18000/health
```

```text
{"status":"ready","model_version":"iris-v1"}
HTTP 200
```

```bash
curl -fsS --max-time 15 -w '
HTTP %{http_code}
' -X POST http://127.0.0.1:18000/predict -H 'content-type: application/json' -d '{"features":[5.1,3.5,1.4,0.2]}'
```

```text
{"class_id":0,"model_version":"iris-v1"}
HTTP 200
```

```bash
curl -fsS --max-time 15 -w '
HTTP %{http_code}
' -X POST http://127.0.0.1:18000/predict -H 'content-type: application/json' -d '{"features":[6.3,3.3,6.0,2.5]}'
```

```text
{"class_id":2,"model_version":"iris-v1"}
HTTP 200
```

```bash
docker logs oleinikov-iris-proof
```

```text
INFO:     172.17.0.1:42574 - "GET /live HTTP/1.1" 200 OK
INFO:     172.17.0.1:42584 - "GET /health HTTP/1.1" 200 OK
INFO:     172.17.0.1:42588 - "POST /predict HTTP/1.1" 200 OK
INFO:     172.17.0.1:42602 - "POST /predict HTTP/1.1" 200 OK
INFO:     Started server process [1]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
```

```bash
docker stop oleinikov-iris-proof
```

```text
oleinikov-iris-proof
```

Контейнер ответил HTTP 200 с ожидаемыми классами; после проверки остановлен и автоматически удалён (`--rm`).

<a id="registry"></a>

## 6. Docker Hub: образ опубликован

```bash
docker push docker.io/ndreuu/oleinikov-iris:v1
```

```text
The push refers to repository [docker.io/ndreuu/oleinikov-iris]
0aa1e843fb2b: Preparing
93ac36d5a89b: Preparing
4df771ead53d: Preparing
d1982e544bd1: Preparing
e81b40755204: Preparing
8db54932ffaa: Preparing
5f6f6c2f50ed: Preparing
6a9352455443: Preparing
340931a1d986: Preparing
96a69f98ae07: Preparing
3dc3efdf0110: Preparing
dd57f90311a2: Preparing
8db54932ffaa: Waiting
5f6f6c2f50ed: Waiting
6a9352455443: Waiting
340931a1d986: Waiting
96a69f98ae07: Waiting
3dc3efdf0110: Waiting
dd57f90311a2: Waiting
e81b40755204: Layer already exists
d1982e544bd1: Layer already exists
0aa1e843fb2b: Layer already exists
93ac36d5a89b: Layer already exists
4df771ead53d: Layer already exists
8db54932ffaa: Layer already exists
5f6f6c2f50ed: Layer already exists
6a9352455443: Layer already exists
340931a1d986: Layer already exists
96a69f98ae07: Layer already exists
3dc3efdf0110: Layer already exists
dd57f90311a2: Layer already exists
v1: digest: sha256:0fc611434bda688cb9c68877e84f52b469add3a953e9b3546aaf6aeaae2cab7b size: 2828
```

```bash
docker image inspect docker.io/ndreuu/oleinikov-iris:v1 --format '{{json .RepoDigests}}'
```

```text
["ndreuu/oleinikov-iris@sha256:0fc611434bda688cb9c68877e84f52b469add3a953e9b3546aaf6aeaae2cab7b"]
```

Публичная доступность проверена

```bash
.venv/bin/python -c 'import json,urllib.request; d=json.load(urllib.request.urlopen("https://hub.docker.com/v2/repositories/ndreuu/oleinikov-iris/", timeout=20)); print(json.dumps({k:d[k] for k in ("namespace","name","is_private")}, indent=2))'
```

```text
{
  "namespace": "ndreuu",
  "name": "oleinikov-iris",
  "is_private": false
}
```

Репозиторий: [ndreuu/oleinikov-iris](https://hub.docker.com/r/ndreuu/oleinikov-iris), [тег v1](https://hub.docker.com/r/ndreuu/oleinikov-iris/tags?name=v1).

![Тег v1 в Docker Hub](evidence/dockerhub-image-v1.png)

<a id="manifest"></a>

## 7. Kubernetes-манифест

Итоговый файл: [ml-service/k8s/app.yaml](ml-service/k8s/app.yaml).

<a id="dry-run"></a>

## 8. Client и server dry-run

```bash
kubectl --context=itmo-student-13 -n itmo-student-13 apply --dry-run=client -f k8s/app.yaml
```

```text
configmap/oleinikov-iris-config unchanged (dry run)
deployment.apps/oleinikov-iris unchanged (dry run)
service/oleinikov-iris unchanged (dry run)
```

```bash
kubectl --context=itmo-student-13 -n itmo-student-13 apply --dry-run=server -f k8s/app.yaml
```

```text
configmap/oleinikov-iris-config unchanged (server dry run)
deployment.apps/oleinikov-iris unchanged (server dry run)
service/oleinikov-iris unchanged (server dry run)
```

<a id="deployment"></a>

## 9. Apply и созданные объекты

```bash
kubectl --context=itmo-student-13 -n itmo-student-13 apply -f k8s/app.yaml
```

```text
configmap/oleinikov-iris-config unchanged
deployment.apps/oleinikov-iris unchanged
service/oleinikov-iris unchanged
```

```bash
kubectl --context=itmo-student-13 -n itmo-student-13 rollout status deploy/oleinikov-iris --timeout=60s
```

```text
deployment "oleinikov-iris" successfully rolled out
```

```bash
kubectl --context=itmo-student-13 -n itmo-student-13 get cm,deploy,pods,svc -l app.kubernetes.io/instance=oleinikov-iris
```

```text
NAME                              DATA   AGE
configmap/oleinikov-iris-config   2      33m

NAME                             READY   UP-TO-DATE   AVAILABLE   AGE
deployment.apps/oleinikov-iris   1/1     1            1           33m

NAME                                 READY   STATUS    RESTARTS   AGE
pod/oleinikov-iris-f5658d7b8-t84vc   1/1     Running   0          33m

NAME                     TYPE        CLUSTER-IP       EXTERNAL-IP   PORT(S)   AGE
service/oleinikov-iris   ClusterIP   10.101.103.123   <none>        80/TCP    33m
```

```bash
kubectl --context=itmo-student-13 -n itmo-student-13 get cm oleinikov-iris-config -o 'jsonpath={.data}{"\n"}'
```

```text
{"MODEL_PATH":"/app/model.joblib","MODEL_VERSION":"iris-v1"}
```

```bash
kubectl --context=itmo-student-13 -n itmo-student-13 get endpointslices -l kubernetes.io/service-name=oleinikov-iris
```

```text
NAME                   ADDRESSTYPE   PORTS   ENDPOINTS   AGE
oleinikov-iris-42szt   IPv4          8000    10.1.0.58   33m
```

<a id="port-forward"></a>

## 10. Port-forward, curl и совпадение digest

```bash
kubectl --context=itmo-student-13 -n itmo-student-13 port-forward svc/oleinikov-iris --address=127.0.0.1 8000:80
```

```text
Forwarding from 127.0.0.1:8000 -> 8000
Handling connection for 8000
Handling connection for 8000
Handling connection for 8000
Handling connection for 8000
Handling connection for 8000
Handling connection for 8000
```

```bash
curl -fsS --max-time 15 -w '
HTTP %{http_code}
' http://127.0.0.1:8000/live
```

```text
{"status":"alive"}
HTTP 200
```

```bash
curl -fsS --max-time 15 -w '
HTTP %{http_code}
' http://127.0.0.1:8000/health
```

```text
{"status":"ready","model_version":"iris-v1"}
HTTP 200
```

```bash
curl -fsS --max-time 15 -w '
HTTP %{http_code}
' -X POST http://127.0.0.1:8000/predict -H 'content-type: application/json' -d '{"features":[5.1,3.5,1.4,0.2]}'
```

```text
{"class_id":0,"model_version":"iris-v1"}
HTTP 200
```


```bash
curl -fsS --max-time 15 -w '
HTTP %{http_code}
' -X POST http://127.0.0.1:8000/predict -H 'content-type: application/json' -d '{"features":[7.0,3.2,4.7,1.4]}'
```

```text
{"class_id":1,"model_version":"iris-v1"}
HTTP 200
```

```bash
curl -fsS --max-time 15 -w '
HTTP %{http_code}
' -X POST http://127.0.0.1:8000/predict -H 'content-type: application/json' -d '{"features":[6.3,3.3,6.0,2.5]}'
```

```text
{"class_id":2,"model_version":"iris-v1"}
HTTP 200
```

Образ, фактически запущенный в поде:

```bash
kubectl --context=itmo-student-13 -n itmo-student-13 get pods -l app.kubernetes.io/instance=oleinikov-iris -o 'jsonpath={range .items[*]}{.metadata.name}{"\n"}{.spec.containers[0].image}{"\n"}{.status.containerStatuses[0].imageID}{"\n"}{end}'
```

```text
oleinikov-iris-f5658d7b8-t84vc
docker.io/ndreuu/oleinikov-iris:v1
docker.io/ndreuu/oleinikov-iris@sha256:0fc611434bda688cb9c68877e84f52b469add3a953e9b3546aaf6aeaae2cab7b
```

Digest пода совпадает с digest из успешного `docker push` в [разделе 6](#registry):

```text
sha256:0fc611434bda688cb9c68877e84f52b469add3a953e9b3546aaf6aeaae2cab7b
```
