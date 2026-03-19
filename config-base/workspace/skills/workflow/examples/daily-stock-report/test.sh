#!/bin/bash
# 测试脚本 - 强制运行完整流程（忽略交易日检查）

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORKSPACE_DIR="$(dirname "$(dirname "$(dirname "$SCRIPT_DIR")")")"
OUTPUT_DIR="$WORKSPACE_DIR/output/reports"
LOG_DIR="$WORKSPACE_DIR/output/logs"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

mkdir -p "$OUTPUT_DIR" "$LOG_DIR"

echo "=========================================="
echo "工作流测试（强制模式）"
echo "=========================================="

# 模拟交易日
echo "[测试] 模拟交易日检查通过..."

# 模拟选股
echo "[测试] 生成模拟选股结果..."
cat > "$OUTPUT_DIR/selected_stocks_test_$TIMESTAMP.json" << EOF
{
  "date": "$(date +%Y-%m-%d)",
  "strategy": "technical",
  "stocks": [
    {"code": "000001.SZ", "name": "平安银行", "reason": "动量因子"},
    {"code": "600519.SH", "name": "贵州茅台", "reason": "趋势因子"},
    {"code": "300750.SZ", "name": "宁德时代", "reason": "成交量因子"}
  ],
  "total": 3
}
EOF

# 生成测试报告
echo "[测试] 生成测试报告..."
cat > "$OUTPUT_DIR/daily_report_test_$(date +%Y%m%d).md" << EOF
# 每日选股报告（测试） - $(date +%Y-%m-%d)

## 执行摘要
- **选股数量**: 3 只
- **策略**: 技术面选股

## 选股列表
| 代码 | 名称 | 选股理由 |
|------|------|----------|
| 000001.SZ | 平安银行 | 动量因子 |
| 600519.SH | 贵州茅台 | 趋势因子 |
| 300750.SZ | 宁德时代 | 成交量因子 |

*测试报告*
EOF

# 生成结果
echo "[测试] 生成测试结果..."
cat > "$OUTPUT_DIR/workflow_result_test_$TIMESTAMP.json" << EOF
{
  "status": "success",
  "test_mode": true,
  "timestamp": "$TIMESTAMP",
  "stocks_selected": 3
}
EOF

echo "=========================================="
echo "✓ 测试完成"
echo "报告：$OUTPUT_DIR/daily_report_test_$(date +%Y%m%d).md"
echo "结果：$OUTPUT_DIR/workflow_result_test_$TIMESTAMP.json"
echo "=========================================="

# 显示报告内容
echo ""
echo "报告预览:"
cat "$OUTPUT_DIR/daily_report_test_$(date +%Y%m%d).md"
