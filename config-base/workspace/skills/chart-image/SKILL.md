---
name: chart-image
triggers: 
version: 2.5.1
status: enhanced
description: 增强版图表生成功能。支持8种图表类型（折线图、柱状图、饼图、散点图、面积图、热力图、箱线图、雷达图）和3种主题（默认、深色、商务）。基于 matplotlib + seaborn 实现。
provides: 
os: 
clawdbot: 
emoji: 📊
category: data
priority: high
updated: 2026-03-11
---

# 📊 chart-image（增强版）

✅ **状态**：增强版已上线，功能完整。

## 功能

### 支持的图表类型（8种）
1. **折线图** (line) - 时间序列数据
2. **柱状图** (bar) - 分类数据比较（支持水平/堆叠）
3. **饼图** (pie) - 比例分布
4. **散点图** (scatter) - 相关性分析
5. **面积图** (area) - 累积数据（支持堆叠）
6. **热力图** (heatmap) - 矩阵数据可视化
7. **箱线图** (box) - 数据分布统计
8. **雷达图** (radar) - 多维数据比较

### 主题样式（3种）
1. **默认主题** (default) - 白色网格，现代风格
2. **深色主题** (dark) - 深色背景，适合演示
3. **商务主题** (business) - 专业风格，适合报告

### 输出格式
- PNG 高清图片（300dpi）
- 保存到 `/Users/momo/.openclaw/output/charts/`

## 使用方法

### 通过技能调用
用户说"生成图表"或"数据可视化"时自动触发。

### 直接脚本调用
```bash
# 折线图
python3 scripts/chart.py --type line --data "1,3,2,5,4" --labels "Mon,Tue,Wed,Thu,Fri" --title "Weekly Sales"

# 柱状图（水平）
python3 scripts/chart.py --type bar --data "45,62,38,71" --labels "Product A,Product B,Product C,Product D" --horizontal

# 散点图
python3 scripts/chart.py --type scatter --x-data "1,2,3,4,5" --y-data "2,4,6,8,10" --title "Correlation"

# 热力图
python3 scripts/chart.py --type heatmap --data "[[1,2,3],[4,5,6],[7,8,9]]" --col-labels "X,Y,Z" --row-labels "A,B,C"

# 使用深色主题
python3 scripts/chart.py --type line --data "1,3,2,5,4" --theme dark
```

## 技术实现

基于 `matplotlib` + `seaborn` + `numpy` 实现，提供统一的 `dataviz_wrapper` 接口。

## 高级功能

1. **主题系统**：一键切换图表风格
2. **配置灵活**：支持多种图表选项
3. **错误处理**：友好的错误提示和降级方案
4. **性能优化**：生成时间 < 3秒

## 开发计划

- **今天 18:00**：web-scraper 增强版
- **明天**：browser-pilot 基础版
- **本周内**：交互式图表支持（Plotly）