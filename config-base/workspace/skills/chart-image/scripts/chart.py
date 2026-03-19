#!/usr/bin/env python3
"""
chart-image 增强版 - 图表生成脚本
基于 dataviz_wrapper 实现，支持8种图表类型和3种主题
"""

import argparse
import json
import os
import sys
from pathlib import Path
from datetime import datetime

# 导入包装器
try:
    from dataviz_wrapper import (
        create_line_chart, create_bar_chart, create_pie_chart,
        create_scatter_plot, create_area_chart, create_heatmap,
        create_box_plot, create_radar_chart,
        THEMES
    )
    HAS_WRAPPER = True
except ImportError as e:
    HAS_WRAPPER = False
    # 定义降级模式的 THEMES
    THEMES = {"default": {}}
    print(f"⚠️ 警告：dataviz_wrapper 导入失败: {e}")
    print("使用降级方案：基础matplotlib实现")

# 输出目录
OUTPUT_DIR = Path.home() / ".openclaw" / "output" / "charts"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

def parse_data(data_str):
    """解析数据字符串"""
    if data_str.startswith("[") and data_str.endswith("]"):
        # JSON 数组
        return json.loads(data_str)
    else:
        # 逗号分隔
        return [float(x.strip()) for x in data_str.split(",")]

def parse_labels(labels_str):
    """解析标签字符串"""
    if labels_str.startswith("[") and labels_str.endswith("]"):
        return json.loads(labels_str)
    else:
        return [x.strip() for x in labels_str.split(",")]

def generate_chart(chart_type, data, labels=None, title="Chart", output_file=None, 
                   theme="default", **kwargs):
    """生成图表（增强版）"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    if not output_file:
        output_file = OUTPUT_DIR / f"{chart_type}_{timestamp}.png"
    else:
        output_file = Path(output_file)
        if not output_file.is_absolute():
            output_file = OUTPUT_DIR / output_file
    
    # 确保输出目录存在
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    try:
        if HAS_WRAPPER:
            # 使用增强版包装器
            if chart_type == "line":
                output_path = create_line_chart(
                    data=data,
                    labels=labels,
                    title=title,
                    theme=theme,
                    output_path=str(output_file)
                )
            elif chart_type == "bar":
                output_path = create_bar_chart(
                    data=data,
                    labels=labels,
                    title=title,
                    theme=theme,
                    output_path=str(output_file),
                    horizontal=kwargs.get("horizontal", False),
                    stacked=kwargs.get("stacked", False)
                )
            elif chart_type == "pie":
                output_path = create_pie_chart(
                    data=data,
                    labels=labels,
                    title=title,
                    theme=theme,
                    output_path=str(output_file),
                    explode=kwargs.get("explode", None),
                    autopct=kwargs.get("autopct", '%1.1f%%')
                )
            elif chart_type == "scatter":
                if "x_data" in kwargs and "y_data" in kwargs:
                    output_path = create_scatter_plot(
                        x_data=kwargs["x_data"],
                        y_data=kwargs["y_data"],
                        labels=labels,
                        title=title,
                        theme=theme,
                        output_path=str(output_file)
                    )
                else:
                    raise ValueError("散点图需要 x_data 和 y_data 参数")
            elif chart_type == "area":
                output_path = create_area_chart(
                    data=data,
                    labels=labels,
                    title=title,
                    theme=theme,
                    output_path=str(output_file),
                    stacked=kwargs.get("stacked", False)
                )
            elif chart_type == "heatmap":
                output_path = create_heatmap(
                    data=data,
                    row_labels=kwargs.get("row_labels"),
                    col_labels=kwargs.get("col_labels") or labels,
                    title=title,
                    theme=theme,
                    output_path=str(output_file)
                )
            elif chart_type == "box":
                output_path = create_box_plot(
                    data=data,
                    labels=labels,
                    title=title,
                    theme=theme,
                    output_path=str(output_file),
                    vert=kwargs.get("vert", True)
                )
            elif chart_type == "radar":
                output_path = create_radar_chart(
                    data=data,
                    labels=labels,
                    title=title,
                    theme=theme,
                    output_path=str(output_file)
                )
            else:
                raise ValueError(f"不支持的图表类型: {chart_type}")
            
            print(f"✅ 图表已生成: {output_path}")
            return {
                "success": True,
                "output_file": output_path,
                "chart_type": chart_type,
                "theme": theme,
                "timestamp": timestamp
            }
        
        else:
            # 降级方案：基础 matplotlib 实现
            import matplotlib.pyplot as plt
            
            plt.figure(figsize=(10, 6))
            
            if chart_type == "line":
                plt.plot(data, marker='o', linewidth=2)
            elif chart_type == "bar":
                plt.bar(range(len(data)), data, alpha=0.8)
            elif chart_type == "pie":
                plt.pie(data, labels=labels if labels else [f"Item {i+1}" for i in range(len(data))])
            elif chart_type == "scatter" and "x_data" in kwargs and "y_data" in kwargs:
                plt.scatter(kwargs["x_data"], kwargs["y_data"], s=50, alpha=0.7)
            else:
                raise ValueError(f"降级模式不支持 {chart_type} 图表")
            
            plt.title(title, fontsize=14, fontweight='bold')
            if labels and chart_type != "pie":
                plt.xticks(range(len(labels)), labels, rotation=45)
            plt.grid(alpha=0.3)
            plt.tight_layout()
            plt.savefig(str(output_file), dpi=150)
            plt.close()
            
            print(f"✅ 图表已生成（降级模式）: {output_file}")
            return {
                "success": True,
                "output_file": str(output_file),
                "chart_type": chart_type,
                "theme": "default",
                "timestamp": timestamp,
                "note": "使用降级模式生成"
            }
    
    except Exception as e:
        print(f"❌ 图表生成失败: {e}")
        return {
            "success": False,
            "error": str(e),
            "chart_type": chart_type
        }

def main():
    parser = argparse.ArgumentParser(description="生成图表（增强版）")
    parser.add_argument("--type", required=True, 
                       choices=["line", "bar", "pie", "scatter", "area", "heatmap", "box", "radar"],
                       help="图表类型")
    parser.add_argument("--data", required=True, help="数据（逗号分隔或JSON数组）")
    parser.add_argument("--labels", help="标签（逗号分隔或JSON数组）")
    parser.add_argument("--title", default="Chart", help="图表标题")
    parser.add_argument("--theme", default="default", choices=["default", "dark", "business"],
                       help="图表主题")
    parser.add_argument("--output", help="输出文件路径")
    parser.add_argument("--x-data", help="散点图X轴数据（仅scatter类型需要）")
    parser.add_argument("--y-data", help="散点图Y轴数据（仅scatter类型需要）")
    parser.add_argument("--row-labels", help="热力图行标签")
    parser.add_argument("--col-labels", help="热力图列标签")
    parser.add_argument("--horizontal", action="store_true", help="水平柱状图")
    parser.add_argument("--stacked", action="store_true", help="堆叠图（柱状图/面积图）")
    parser.add_argument("--check", action="store_true", help="健康检查")
    
    args = parser.parse_args()
    
    if args.check:
        result = {
            "skill": "chart-image",
            "version": "2.5.1-enhanced",
            "status": "ok" if HAS_WRAPPER else "warn",
            "backend": "dataviz-wrapper" if HAS_WRAPPER else "matplotlib-fallback",
            "supported_charts": ["line", "bar", "pie", "scatter", "area", "heatmap", "box", "radar"],
            "themes": list(THEMES.keys()) if HAS_WRAPPER else ["default"],
            "output_dir": str(OUTPUT_DIR),
            "timestamp": datetime.now().isoformat()
        }
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return 0 if HAS_WRAPPER else 1
    
    # 解析数据
    data = parse_data(args.data)
    
    # 解析标签（如果有）
    labels = None
    if args.labels:
        labels = parse_labels(args.labels)
    
    # 准备额外参数
    kwargs = {}
    
    # 散点图需要特殊处理
    if args.type == "scatter":
        if not args.x_data or not args.y_data:
            print("❌ 散点图需要 --x-data 和 --y-data 参数")
            return 1
        kwargs["x_data"] = parse_data(args.x_data)
        kwargs["y_data"] = parse_data(args.y_data)
    
    # 热力图标签
    if args.type == "heatmap":
        if args.row_labels:
            kwargs["row_labels"] = parse_labels(args.row_labels)
        if args.col_labels:
            kwargs["col_labels"] = parse_labels(args.col_labels)
    
    # 其他选项
    if args.horizontal:
        kwargs["horizontal"] = True
    if args.stacked:
        kwargs["stacked"] = True
    
    # 检查数据维度
    if args.type in ["line", "bar", "pie"] and labels and len(labels) != len(data):
        print(f"⚠️ 警告：标签数量({len(labels)})与数据数量({len(data)})不匹配")
    
    # 生成图表
    result = generate_chart(
        chart_type=args.type,
        data=data,
        labels=labels,
        title=args.title,
        theme=args.theme,
        output_file=args.output,
        **kwargs
    )
    
    # 输出结果
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0 if result["success"] else 1

if __name__ == "__main__":
    sys.exit(main())