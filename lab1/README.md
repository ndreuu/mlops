# Лабораторная №1: Iris ML-сервис

Лабораторная выполнена: образ `docker.io/ndreuu/oleinikov-iris:v1` опубликован, сервис работает в namespace `itmo-student-13`. Проверены `/live`, `/health`, предсказания setosa и virginica через port-forward. Итоговый чеклист и результаты: [STATUS.md](STATUS.md), [verification.json](verification.json). Ниже — команды для воспроизведения.

## Рабочие каталоги

В командах ниже `MLOPS_DIR` — корень этого репозитория. В новом терминале на Mac задайте:

```bash
export MLOPS_DIR="/Users/andrew/Documents/Codex/2026-11-21/ssh-mlops-x20/projects/mlops"
```

Исходники также скопированы на учебную ВМ. Для Docker-команд подключитесь к ней и задайте путь там:

```bash
ssh mlops
export MLOPS_DIR="$HOME/projects/mlops"
cd "$MLOPS_DIR/lab1/ml-service"
```

На Mac Docker не установлен; сборка образа выполнена на ВМ. Git-репозиторий и окончательный Kubernetes-манифест находятся на Mac. Команды `kubectl` ниже выполняются на Mac.

## 1. Подключение Kubernetes

Kubeconfig из выданного архива `itmo-student-13.zip` импортирован через `kubecm` в `~/.kube/config` на Mac. Исходный конфиг хранится в `~/.kube/itmo-student-13.kubeconfig`. Права каталога — `700`, файлов — `600`.

Проверить контекст и namespace:

```bash
kubecm list
kubecm switch itmo-student-13
kubectl config current-context
kubectl config view --minify -o jsonpath='{.contexts[0].context.namespace}{"\n"}'
kubectl -n itmo-student-13 get pods
```

API учебного кластера: `https://37.18.117.109:6443`. Контекст и назначенный namespace: `itmo-student-13`. Проверка TLS включена, сертификат CA находится в kubeconfig. Namespace взят из персонального доступа; он заменяет общий namespace из первоначальной методички.

При повторной настройке на другой машине сохраните файл вне репозитория. Для первого подключения, когда `~/.kube/config` ещё отсутствует:

```bash
export COURSE_KUBECONFIG="$HOME/Downloads/itmo-student-13.kubeconfig"
mkdir -p "$HOME/.kube"
chmod 700 "$HOME/.kube"
install -m 600 "$COURSE_KUBECONFIG" "$HOME/.kube/config"
kubecm switch itmo-student-13
```

Если на другой машине уже есть конфигурация с другими контекстами, сначала сохраните её резервную копию, затем объедините конфиги через `kubecm add --cover -f "$COURSE_KUBECONFIG"`. В установленной версии `kubecm add` требует существования `~/.kube/config`; одного флага `--create` оказалось недостаточно.

Права на нужные ресурсы уже проверены:

```bash
kubectl auth can-i create deployments -n itmo-student-13
kubectl auth can-i create services -n itmo-student-13
kubectl auth can-i create configmaps -n itmo-student-13
```

Для всех трёх команд получено `yes`. Квота namespace: requests и limits по `2600m` CPU и `4G` памяти. Service использует разрешённый тип `ClusterIP`.

Kubeconfig содержит индивидуальный ServiceAccount token. Храните его вне git.

## 2. Локальное обучение и API

Этот этап уже выполнен. Команды для повторного запуска после изменения сервиса, на Mac:

```bash
cd "$MLOPS_DIR/lab1/ml-service"
source .venv/bin/activate
python train.py
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

При подготовке нового окружения сначала выполните в каталоге сервиса:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

В другом терминале:

```bash
curl -fsS http://127.0.0.1:8000/live
curl -fsS http://127.0.0.1:8000/health
curl -fsS -X POST http://127.0.0.1:8000/predict \
  -H 'content-type: application/json' \
  -d '{"features":[5.1,3.5,1.4,0.2]}'
curl -fsS -X POST http://127.0.0.1:8000/predict \
  -H 'content-type: application/json' \
  -d '{"features":[6.3,3.3,6.0,2.5]}'
```

Ожидаются `alive`, `ready` и классы `0` (setosa), `2` (virginica), версия модели `iris-v1`. Остановить API: `Ctrl+C`.

## 3. Публикация готового образа

Выполняйте на учебной ВМ, где уже есть образ `oleinikov-iris:v1`. Docker использует helper `docker-credential-pass`; `pass` инициализирован отдельным GPG-ключом по методичке. Авторизация аккаунта `ndreuu` на ВМ выполнена через браузер; Docker сохраняет учётные данные через `pass`.

Docker Hub аккаунт: `ndreuu`. Для публикации:

```bash
export DOCKERHUB_USER=ndreuu
export IMAGE="docker.io/${DOCKERHUB_USER}/oleinikov-iris:v1"
docker image inspect oleinikov-iris:v1 --format '{{.Id}} {{.Os}}/{{.Architecture}}'
docker tag oleinikov-iris:v1 "$IMAGE"
docker login -u "$DOCKERHUB_USER"
docker push "$IMAGE"
```

При повторном входе `docker login` без аргументов использует подтверждение через браузер. При `docker login -u "$DOCKERHUB_USER"` вводите access token в интерактивном запросе. Для скачивания кластером используйте публичный репозиторий Docker Hub либо предоставленный курсом способ доступа к приватному registry.

При изменениях кода сначала обновите его копию на ВМ. Для новой версии используйте новый тег, например `v2`, и укажите его в поле `image` манифеста:

```bash
cd "$MLOPS_DIR/lab1/ml-service"
export IMAGE="docker.io/ndreuu/oleinikov-iris:v2"
docker build -t "$IMAGE" .
docker push "$IMAGE"
```

Новый тег в манифесте запускает обновление Deployment и исключает использование прежнего образа из кеша под тем же тегом.

## 4. Развёртывание

В `ml-service/k8s/app.yaml` уже указан образ `docker.io/ndreuu/oleinikov-iris:v1` и namespace `itmo-student-13`. Применяйте манифест после успешной публикации образа. Перед применением убедитесь, что выбран учебный контекст.

```bash
cd "$MLOPS_DIR/lab1"
kubectl config current-context
kubectl -n itmo-student-13 get deploy,svc,cm \
  -l app.kubernetes.io/instance=oleinikov-iris
kubectl apply --dry-run=client -f ml-service/k8s/app.yaml
kubectl apply --dry-run=server -f ml-service/k8s/app.yaml
kubectl apply -f ml-service/k8s/app.yaml
kubectl -n itmo-student-13 rollout status deploy/oleinikov-iris --timeout=180s
kubectl -n itmo-student-13 get deploy,svc,pods \
  -l app.kubernetes.io/instance=oleinikov-iris
kubectl -n itmo-student-13 port-forward svc/oleinikov-iris 8000:80
```

Обе проверки `kubectl apply --dry-run` выполняйте после подключения kubeconfig. Если ресурсы с этим именем уже существуют, сначала выясните их принадлежность.

Оставив `port-forward` работающим, повторите запросы из раздела 2 в другом терминале. Локальный `uvicorn` к этому моменту должен быть остановлен, чтобы порт 8000 был свободен.

Если под не готов:

```bash
kubectl -n itmo-student-13 describe pod \
  -l app.kubernetes.io/instance=oleinikov-iris
kubectl -n itmo-student-13 logs deploy/oleinikov-iris --tail=100
```

Результаты выполненной проверки сохранены в [STATUS.md](STATUS.md) и [verification.json](verification.json).
