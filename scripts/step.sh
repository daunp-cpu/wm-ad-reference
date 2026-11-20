#!/bin/zsh
# 복각 작업 중 진행 문구를 사이트 카드에 표시: zsh <사이트>/scripts/step.sh <job> "리뷰어 검수 1바퀴 — 레퍼런스와 비교 중"
R=$(cd "$(dirname "$0")/.." && pwd); cd $R; J=$1; T=${2//\"/\'}
T0=$(cat data/claude_work/$J/t0 2>/dev/null || date +%s)
node scripts/blob.mjs status "{\"state\":\"working\",\"job\":\"$J\",\"ids\":[],\"step\":\"$T\",\"all\":1,\"t0\":$T0,\"exp\":2400}" >/dev/null 2>&1 && echo "표시: $T"
