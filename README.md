# Лабораторные по MLOps

Первая лабораторная: обучение модели Iris, API, Docker-образ и развёртывание в Kubernetes.

- [Инструкция по лабораторной №1](lab1/README.md).
- [Выполненные шаги и оставшиеся задачи](lab1/STATUS.md).
- Исходники сервиса: `lab1/ml-service/`.
- Манифест Kubernetes: `lab1/ml-service/k8s/app.yaml`.

Для ресурсов выбран префикс `oleinikov-iris`. Персональный kubeconfig подключён на Mac; назначенный контекст и namespace — `itmo-student-13`. Манифест использует этот namespace. Перед развёртыванием нужно указать опубликованный образ своего registry.
