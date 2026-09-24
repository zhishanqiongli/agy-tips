#!/usr/bin/env bash
#
# check-upstream.sh: 安全检查上游更新状态，并给出入库建议
#

set -euo pipefail

cd "$(git rev-parse --show-toplevel)"

echo "🔍 正在检查上游 (origin) 最新动态..."
git fetch origin --quiet

# 统计落后于 origin/main 的提交数
BEHIND_COUNT=$(git rev-list --count HEAD..origin/main || echo 0)

if [ "$BEHIND_COUNT" -eq 0 ]; then
    echo "✅ 上游暂无新更新，当前本地仓库已处于最新状态。"
    exit 0
fi

echo "⚠️  检测到上游有 $BEHIND_COUNT 个新提交待入库！"
echo ""
echo "=== 上游新提交记录 ==="
git log HEAD..origin/main --oneline
echo ""

echo "=== 变动文件清单 ==="
git diff --name-status HEAD..origin/main
echo ""

echo "💡 入库建议："
echo "1. 请勿直接执行 git pull 或 git merge origin/main。"
echo "2. 若有新增文件（如 tips/ 或 scripts/），请单独检出："
echo "   git checkout origin/main -- <文件路径>"
echo "3. 详细入库规范请参考文档: UPSTREAM_SYNC.md"
