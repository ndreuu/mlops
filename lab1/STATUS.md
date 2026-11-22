# Состояние лабораторной №1

Лабораторная выполнена и проверена 22 ноября 2026 года.

## Чеклист сдачи

- [x] Модель Iris обучена, локальные `train.py` и API работают.
- [x] Образ собран на учебной ВМ и опубликован: `docker.io/ndreuu/oleinikov-iris:v1`.
- [x] `pass` инициализирован; `docker login` на ВМ завершён успешно через браузер.
- [x] В Docker задан `credsStore: pass`, установлен helper `docker-credential-pass`.
- [x] Персональный kubeconfig импортирован через `kubecm` в `~/.kube/config` на Mac.
- [x] Проверены контекст, namespace `itmo-student-13` и права на ресурсы лабораторной.
- [x] Манифест исправлен: уникальные имена, labels, selectors, ConfigMap, probes и порты.
- [x] Client и server dry-run прошли; server dry-run повторён с окончательным образом.
- [x] ConfigMap, Deployment и Service созданы в назначенном namespace.
- [x] Deployment готов: `1/1`; под `Running`, на момент проверки — `0` перезапусков.
- [x] Через `kubectl port-forward` проверены `/live`, `/health` и два предсказания.
- [x] Digest образа в поде совпадает с digest опубликованного образа.

Namespace `itmo-student-13` указан в персональном kubeconfig и заменяет общий namespace из первоначальной методички.

## Ресурсы

| Ресурс | Имя |
|---|---|
| Контекст / namespace | `itmo-student-13` |
| ConfigMap | `oleinikov-iris-config` |
| Deployment | `oleinikov-iris` |
| Service | `oleinikov-iris`, `ClusterIP`, `80 → 8000` |
| Образ | `docker.io/ndreuu/oleinikov-iris:v1`, `linux/amd64` |
| Версия модели | `iris-v1` |

Публичный образ: [Docker Hub](https://hub.docker.com/r/ndreuu/oleinikov-iris).

Digest в registry и в запущенном поде:

```text
sha256:0fc611434bda688cb9c68877e84f52b469add3a953e9b3546aaf6aeaae2cab7b
```

Локальный image ID на учебной ВМ:

```text
sha256:3576c5eb3ed11a7c0a2d2451775c1bfb7cb58d43ffbfa4c095400b9196d311ae
```

Image ID обозначает конфигурацию образа, а registry digest — его manifest; это разные идентификаторы.

## Проверка API в Kubernetes

Через `kubectl port-forward svc/oleinikov-iris 8000:80` получены HTTP 200 и ответы:

```json
{"status":"alive"}
{"status":"ready","model_version":"iris-v1"}
{"class_id":0,"model_version":"iris-v1"}
{"class_id":2,"model_version":"iris-v1"}
```

Полные результаты с запросами и именем проверенного пода: [verification.json](verification.json).

Временный port-forward остановлен после проверки. Сервис работает в Kubernetes. Для повторной проверки на Mac:

```bash
kubectl --context=itmo-student-13 -n itmo-student-13 port-forward svc/oleinikov-iris 8000:80
```

В другом терминале:

```bash
curl -fsS http://127.0.0.1:8000/health
curl -fsS -X POST http://127.0.0.1:8000/predict \
  -H 'content-type: application/json' \
  -d '{"features":[5.1,3.5,1.4,0.2]}'
curl -fsS -X POST http://127.0.0.1:8000/predict \
  -H 'content-type: application/json' \
  -d '{"features":[6.3,3.3,6.0,2.5]}'
```

## Хранение доступа

Kubeconfig хранится на Mac вне репозитория; на ВМ он не копировался. Учётные данные Docker хранятся на ВМ через `pass`. Для учебного хранилища создан отдельный GPG-ключ без passphrase, как разрешено методичкой.

Примеры `hello.yaml` и `postgres.yaml` из архива доступа не применялись. Сообщения в чат курса не отправлялись.

Порядок воспроизведения: [README.md](README.md).
