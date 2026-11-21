# Лабораторная №1: Iris ML-сервис

Текущее состояние записано в [STATUS.md](STATUS.md). Модель и API уже проверены локально, Docker-образ собран и проверен на учебной ВМ. Следующие шаги: подключение kubeconfig, вход в registry, публикация и развёртывание.

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

## 1. Подключение Kubernetes, когда выдадут kubeconfig

На Mac установлены `kubectl` и `kubecm`. Сохраните выданный преподавателем конфиг вне репозитория. Укажите фактический путь к файлу:

```bash
export COURSE_KUBECONFIG="$HOME/Downloads/ВАШ_ФАЙЛ_KUBECONFIG"
mkdir -p "$HOME/.kube"
chmod 700 "$HOME/.kube"
chmod 600 "$COURSE_KUBECONFIG"
kubecm --create add -f "$COURSE_KUBECONFIG"
chmod 600 "$HOME/.kube/config"
kubecm list
kubecm switch
kubectl config current-context
kubectl config view --minify -o jsonpath='{.contexts[0].context.namespace}{"\n"}'
```

В `kubecm switch` выберите контекст учебного кластера. Если namespace пуст, уточните назначенный namespace у преподавателя; методичка указывает `mlops-students`. Если выдан другой namespace, исправьте все три поля `metadata.namespace` в `ml-service/k8s/app.yaml` и namespace в дальнейших командах.

Проверьте доступ к назначенному namespace:

```bash
kubectl -n mlops-students get pods
kubectl auth can-i create deployments -n mlops-students
kubectl auth can-i create services -n mlops-students
kubectl auth can-i create configmaps -n mlops-students
```

Kubeconfig может содержать сертификаты и токены доступа. Храните его вне git.

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

Выполняйте на учебной ВМ, где уже есть образ `oleinikov-iris:v1`. Docker использует helper `docker-credential-pass`; `pass` инициализирован отдельным GPG-ключом по методичке. Учётные данные registry ещё не добавлены.

Замените `YOUR_DOCKERHUB_USER` своим логином Docker Hub:

```bash
export DOCKERHUB_USER=YOUR_DOCKERHUB_USER
export IMAGE="docker.io/${DOCKERHUB_USER}/oleinikov-iris:v1"
docker image inspect oleinikov-iris:v1 --format '{{.Id}} {{.Os}}/{{.Architecture}}'
docker tag oleinikov-iris:v1 "$IMAGE"
docker login -u "$DOCKERHUB_USER"
docker push "$IMAGE"
```

Вводите access token в интерактивном запросе `docker login`. Для скачивания кластером используйте публичный репозиторий Docker Hub либо предоставленный курсом способ доступа к приватному registry.

Если исходники изменились, перед публикацией пересоберите образ в каталоге сервиса на ВМ:

```bash
cd "$MLOPS_DIR/lab1/ml-service"
docker build -t oleinikov-iris:v1 .
```

После пересборки повторите `docker tag` и `docker push`. При изменениях кода сначала обновите его копию на ВМ.

## 4. Развёртывание

На Mac откройте `ml-service/k8s/app.yaml`, замените `REPLACE_WITH_DOCKERHUB_USER` на логин, использованный при публикации, и сверьте namespace. Перед применением убедитесь, что выбран учебный контекст.

```bash
cd "$MLOPS_DIR/lab1"
kubectl config current-context
kubectl -n mlops-students get deploy,svc,cm \
  -l app.kubernetes.io/instance=oleinikov-iris
kubectl apply --dry-run=client -f ml-service/k8s/app.yaml
kubectl apply --dry-run=server -f ml-service/k8s/app.yaml
kubectl apply -f ml-service/k8s/app.yaml
kubectl -n mlops-students rollout status deploy/oleinikov-iris --timeout=180s
kubectl -n mlops-students get deploy,svc,pods \
  -l app.kubernetes.io/instance=oleinikov-iris
kubectl -n mlops-students port-forward svc/oleinikov-iris 8000:80
```

Обе проверки `kubectl apply --dry-run` выполняйте после подключения kubeconfig. Если ресурсы с этим именем уже существуют, сначала выясните их принадлежность.

Оставив `port-forward` работающим, повторите запросы из раздела 2 в другом терминале. Локальный `uvicorn` к этому моменту должен быть остановлен, чтобы порт 8000 был свободен.

Если под не готов:

```bash
kubectl -n mlops-students describe pod \
  -l app.kubernetes.io/instance=oleinikov-iris
kubectl -n mlops-students logs deploy/oleinikov-iris --tail=100
```

После успешной проверки отметьте оставшиеся пункты в [STATUS.md](STATUS.md).
