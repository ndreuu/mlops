# Состояние лабораторной №1

Обновлено: 22 ноября 2026 года.

## Выполнено

- [x] Создан локальный git-репозиторий; исходники взяты из выданного `ml-service.zip`.
- [x] На Mac установлены Python 3.12, `kubectl` и `kubecm`; создан каталог `~/.kube`.
- [x] Установлены зависимости и обучена модель Iris.
- [x] Проверено локальное API: `/health` возвращает `ready`, setosa → `0`, virginica → `2`.
- [x] Исправлен Kubernetes-манифест: имена и labels, ссылки на ConfigMap, selectors, probes и порты.
- [x] На учебной ВМ собран и проверен Docker-образ `oleinikov-iris:v1`.
- [x] На ВМ инициализирован `pass`; в Docker задан `credsStore: pass` и установлен helper.
- [x] Персональный kubeconfig импортирован через `kubecm` в `~/.kube/config` на Mac.
- [x] Выбран контекст `itmo-student-13`; проверено TLS-подключение к API кластера.
- [x] Назначенный namespace `itmo-student-13` указан во всех объектах манифеста.
- [x] Проверены права: создание Deployment, Service и ConfigMap разрешено.
- [x] Client и server dry-run прошли для ConfigMap, Deployment и Service в `itmo-student-13`.

Образ на ВМ: `linux/amd64`, пользователь контейнера `10001`.

```text
sha256:3576c5eb3ed11a7c0a2d2451775c1bfb7cb58d43ffbfa4c095400b9196d311ae
```

При проверке контейнера получены ответы:

```json
{"status":"ready","model_version":"iris-v1"}
{"class_id":0,"model_version":"iris-v1"}
{"class_id":2,"model_version":"iris-v1"}
```

Тестовый контейнер удалён после проверки. Образ остался на ВМ. Для учебного `pass` создан отдельный GPG-ключ без passphrase, как разрешено методичкой.

## Осталось

- [ ] Указать свой Docker Hub login, выполнить `docker login` и `docker push`.
- [ ] Подставить опубликованный образ в манифест; namespace уже подтверждён.
- [ ] После подстановки опубликованного образа повторить server dry-run и применить манифест.
- [ ] Дождаться готовности пода и проверить API через `port-forward`.

Kubeconfig установлен на Mac и хранится вне репозитория; на учебную ВМ он не копировался. Вход в registry не выполнен, образ в манифесте пока указан заглушкой. Dry-run не проверяет доступность образа в registry. В кластере ресурсы не создавались, сообщение о выполнении задания в чат курса не отправлено.

API кластера: `https://37.18.117.109:6443`, Kubernetes `v1.36.4`. Namespace `itmo-student-13` при подключении был пуст; доступная квота requests и limits — по `2600m` CPU и `4G` памяти. Примеры `hello.yaml` и `postgres.yaml` из архива доступа не применялись.

Порядок продолжения: [README.md](README.md).
