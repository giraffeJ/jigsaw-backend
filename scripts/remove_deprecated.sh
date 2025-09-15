#!/usr/bin/env bash
# 삭제 준비 스크립트 — 실행 전 반드시 검토 필요
#
# 목적:
# - docs/deletion_candidates.md 기반의 "삭제 후보" 파일 목록을 한 곳에 모아
#   승인(또는 --apply 플래그) 이후 원클릭으로 삭제할 수 있게 준비합니다.
#
# 안전장치 / 사용법:
# 1) 기본 동작은 "dry-run" 입니다. 스크립트를 실행하면 삭제 대상 목록과
#    각 파일에 대한 `git diff` 를 출력합니다. 실제 삭제는 일어나지 않습니다.
# 2) 실제로 파일을 제거하려면 아래 중 하나를 사용하십시오:
#      bash scripts/remove_deprecated.sh --apply
#    또는 (확인 없이 바로 실행)
#      bash scripts/remove_deprecated.sh --apply --yes
# 3) 실행 전 반드시 다음을 권장합니다:
#    - git status / git diff 확인
#    - 전체 테스트 실행(pytest)
#    - 스테이징에서 런타임 검증
#
# 경고: 이 스크립트를 실행하면 파일이 즉시 삭제됩니다. 되돌리려면 git을 사용해 복구하거나 백업을 준비해 두십시오.

set -euo pipefail

# 삭제 후보 목록 (docs/deletion_candidates.md 기반)
REMOVALS=(
  "app/models/template_response.py"
  "app/models/user_request.py"
  "app/models/user_response.py"
  "app/models/history_request.py"
  "app/models/history_response.py"
  "app/models/match_response.py"
  "app/models/template_request.py"
  "scripts/import_presentations.py"
  "scripts/import_excel.py"
  "scripts/migrate_user_schema.py"
)

# helper: print list
print_list() {
  echo "삭제 후보 파일 목록 (${#REMOVALS[@]})"
  echo "---------------------------------"
  for f in "${REMOVALS[@]}"; do
    if [ -e "$f" ]; then
      echo "  - $f"
    else
      echo "  - $f (없음)"
    fi
  done
  echo
}

# Show git diff for the candidates (if repo)
show_git_diffs() {
  # only run git diff if inside a git repo
  if git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    echo "=== 각 파일에 대한 git diff (작업 디렉터리 기준) ==="
    for f in "${REMOVALS[@]}"; do
      if [ -e "$f" ]; then
        echo
        echo "---- diff: $f ----"
        git --no-pager diff -- "$f" || true
      else
        echo
        echo "---- 파일 없음: $f ----"
      fi
    done
    echo "=== git diff 출력 끝 ==="
  else
    echo "경고: 현재 디렉터리가 git 레포가 아닙니다. git diff를 건너뜁니다."
  fi
}

# Dry-run output
if [ "${1:-}" != "--apply" ]; then
  echo "DRY RUN: 실제 삭제는 이루어지지 않습니다."
  echo
  print_list
  show_git_diffs
  echo
  echo "실제로 삭제하려면:"
  echo "  bash scripts/remove_deprecated.sh --apply"
  echo "또는 확인 없이 바로 실행하려면:"
  echo "  bash scripts/remove_deprecated.sh --apply --yes"
  exit 0
fi

# --apply branch: confirm before deleting unless --yes supplied
if [ "${2:-}" != "--yes" ]; then
  echo "주의: 실제 파일 삭제를 진행합니다. 되돌리려면 git 또는 백업을 준비하세요."
  read -p "계속 진행합니까? (yes/NO): " yn
  if [ "$yn" != "yes" ]; then
    echo "취소됨."
    exit 1
  fi
fi

# Perform deletions
echo "삭제 진행 중..."
for f in "${REMOVALS[@]}"; do
  if [ -e "$f" ]; then
    rm -v -- "$f"
  else
    echo "건너뜀(파일 없음): $f"
  fi
done

echo "삭제 완료. 변경 사항을 커밋하려면 다음을 실행하세요:"
echo "  git add -A && git commit -m \"chore: remove deprecated files (from deletion_candidates)\""
