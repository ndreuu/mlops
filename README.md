# Лабораторные по MLOps

Первая лабораторная: обучение модели Iris, API, Docker-образ и развёртывание в Kubernetes.

- [Отчёт по лабораторной №1: команды и фактические выводы](lab1/README.md).
- [Итоговый чеклист](lab1/STATUS.md).
- [Инструкция по повторному запуску](lab1/RUNBOOK.md).
- Исходники сервиса: `lab1/ml-service/`.
- Манифест Kubernetes: `lab1/ml-service/k8s/app.yaml`.

Для ресурсов выбран префикс `oleinikov-iris`. Персональный kubeconfig подключён на Mac; назначенный контекст и namespace — `itmo-student-13`. Манифест использует этот namespace. Образ [ndreuu/oleinikov-iris:v1](https://hub.docker.com/r/ndreuu/oleinikov-iris) опубликован; Deployment готов `1/1`, проверки API через Kubernetes прошли.
