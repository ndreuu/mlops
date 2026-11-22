#!/usr/bin/env bash
set -Eeuo pipefail

release=${1:?release}
environment=${2:?environment}
repository=${3:?repository}
digest=${4:?digest}
revision=${5:?build revision}
mode=${6:-normal}
namespace=${KUBE_NAMESPACE:-itmo-student-13}
export HELM_DRIVER=${HELM_DRIVER:-configmap}
report_dir="reports/${environment}-${mode}"
mkdir -p "$report_dir"

[[ "$release" == oleinikov-search-* ]]
[[ "$mode" == normal || "$mode" == reverse ]]
[[ "$digest" =~ ^sha256:[0-9a-f]{64}$ ]]
good_revision=""
if helm status "$release" -n "$namespace" >/dev/null 2>&1; then
  helm history "$release" -n "$namespace" -o json | tee "$report_dir/history-before.json"
  good_revision=$(python -c 'import json,sys; h=json.load(sys.stdin); print([r["revision"] for r in h if r["status"]=="deployed"][-1])' < "$report_dir/history-before.json")
  helm get values "$release" -n "$namespace" -o json > "$report_dir/previous-values.json"
else
  printf '[]\n' > "$report_dir/history-before.json"
fi
if [[ "$mode" == reverse && -z "$good_revision" ]]; then
  echo 'Rollback demo requires an existing good production revision' >&2
  exit 1
fi

helm upgrade --install "$release" helm/mlops-search -n "$namespace" \
  --atomic --wait --timeout 240s --history-max 20 \
  --set-string "image.repository=$repository" \
  --set-string "image.digest=$digest" \
  --set-string "environment=$environment" \
  --set-string "buildRevision=$revision" \
  --set-string "rankingMode=$mode" | tee "$report_dir/upgrade.log"

candidate_passed=true
if ! helm test "$release" -n "$namespace" --timeout 120s > "$report_dir/helm-test.log" 2>&1; then
  candidate_passed=false
fi
cat "$report_dir/helm-test.log"
if ! python scripts/verify_release.py --release "$release" --namespace "$namespace" \
  --expected-digest "$digest" --expected-revision "$revision" \
  --expected-environment "$environment" --expected-ranking "$mode" \
  --output "$report_dir/smoke.json"; then
  candidate_passed=false
fi

if [[ "$candidate_passed" == true && "$mode" == normal ]]; then
  helm history "$release" -n "$namespace" -o json | tee "$report_dir/history-after.json"
  exit 0
fi

if [[ -z "$good_revision" ]]; then
  echo 'No previous good revision exists; candidate failed' >&2
  exit 1
fi
echo "Rolling back $release to good revision $good_revision"
helm rollback "$release" "$good_revision" -n "$namespace" --wait --timeout 240s | tee "$report_dir/rollback.log"
helm get values "$release" -n "$namespace" -o json > "$report_dir/restored-values.json"
readarray -t previous < <(python -c 'import json,sys; v=json.load(sys.stdin); print(v["image"]["digest"]); print(v["buildRevision"]); print(v["rankingMode"])' < "$report_dir/previous-values.json")
[[ "${previous[2]}" == normal ]]
python scripts/verify_release.py --release "$release" --namespace "$namespace" \
  --expected-digest "${previous[0]}" --expected-revision "${previous[1]}" \
  --expected-environment "$environment" --expected-ranking normal \
  --output "$report_dir/smoke-restored.json"
helm history "$release" -n "$namespace" -o json | tee "$report_dir/history-after.json"

if [[ "$mode" == reverse ]]; then
  python - "$report_dir" <<'PY'
import json,sys
from pathlib import Path
p=Path(sys.argv[1])
failed=json.loads((p/'smoke.json').read_text())
restored=json.loads((p/'restored-values.json').read_text())
assert failed['ready']['status']=='ready'
assert failed['meta']['ranking_mode']=='reverse'
assert failed['checks']['top_result'] is False
assert all(v for k,v in failed['checks'].items() if k!='top_result')
assert restored['rankingMode']=='normal'
print('Reverse candidate failed semantic smoke; rollback restored rankingMode=normal')
PY
else
  echo 'Candidate rejected; previous good release restored' >&2
  exit 1
fi
