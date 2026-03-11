#!/usr/bin/env python3
"""
python-dataviz 包装器 - 提供统一的图表生成接口
"""

import sys
import os
from pathlib import Path
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
import pandas as pd
from datetime import datetime

# 添加 python-dataviz 路径
DATAVIZ_PATH = Path.home() / ".openclaw" / "workspace" / "skills" / "python-dataviz" / "scripts"
if DATAVIZ_PATH.exists():
    sys.path.insert(0, str(DATAVIZ_PATH))

# 输出目录
OUTPUT_DIR = Path.home() / ".openclaw" / "output" / "charts"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# 主题定义
THEMES = {
    "default": {
        "style": "whitegrid",
        "palette": "viridis",
        "font_scale": 1.0,
        "rc_params": {}
    },
    "dark": {
        "style": "darkgrid",
        "palette": "mako",
        "font_scale": 1.0,
        "rc_params": {
            "axes.facecolor": "#2e2e2e",
            "figure.facecolor": "#2e2e2e",
            "text.color": "white",
            "axes.labelcolor": "white",
            "xtick.color": "white",
            "ytick.color": "white"
        }
    },
    "business": {
        "style": "whitegrid",
        "palette": "coolwarm",
        "font_scale": 1.1,
        "rc_params": {
            "font.family": "sans-serif",
            "font.sans-serif": ["Arial", "Helvetica", "DejaVu Sans"],
            "axes.titlesize": 14,
            "axes.labelsize": 12
        }
    }
}

def apply_theme(theme_name="default"):
    """应用主题样式"""
    theme = THEMES.get(theme_name, THEMES["default"])
    
    # 清除现有样式
    plt.style.use('default')
    
    # 应用 seaborn 样式
    sns.set_theme(
        style=theme["style"],
        palette=theme["palette"],
        font_scale=theme["font_scale"]
    )
    
    # 应用 rc 参数
    if theme["rc_params"]:
        plt.rcParams.update(theme["rc_params"])
    
    # 设置中文字体
    try:
        import matplotlib.font_manager as fm
        import os
        
        # 字体搜索路径
        font_paths = [
            '/System/Library/Fonts/Supplemental/AppleGothic.ttf',  # macOS
            '/System/Library/Fonts/PingFang.ttc',  # macOS
            '/System/Library/Fonts/Hiragino Sans GB.ttc',  # macOS
            '/usr/share/fonts/truetype/droid/DroidSansFallbackFull.ttf',  # Linux
            'C:/Windows/Fonts/msyh.ttc',  # Windows
            'C:/Windows/Fonts/simhei.ttf',  # Windows
        ]
        
        # 查找可用字体
        available_fonts = []
        for font_path in font_paths:
            if os.path.exists(font_path):
                available_fonts.append(font_path)
        
        if available_fonts:
            # 使用第一个可用字体
            font_prop = fm.FontProperties(fname=available_fonts[0])
            font_name = font_prop.get_name()
            plt.rcParams['font.sans-serif'] = [font_name]
            plt.rcParams['axes.unicode_minus'] = False
        else:
            # 尝试从系统字体列表查找
            font_list = fm.findSystemFonts(fontpaths=None, fontext='ttf')
            chinese_fonts = [f for f in font_list if any(keyword in f.lower() for keyword in ['pingfang', 'hiragino', 'msyh', 'simhei', 'simsun', 'gothic'])]
            if chinese_fonts:
                font_prop = fm.FontProperties(fname=chinese_fonts[0])
                font_name = font_prop.get_name()
                plt.rcParams['font.sans-serif'] = [font_name]
                plt.rcParams['axes.unicode_minus'] = False
    except Exception as e:
        print(f"⚠️ 中文字体设置失败: {e}")
    
    return theme

def create_line_chart(data, labels=None, title="Line Chart", xlabel=None, ylabel=None, 
                     theme="default", output_path=None, figsize=(10, 6), dpi=300):
    """创建折线图"""
    apply_theme(theme)
    
    if output_path is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = OUTPUT_DIR / f"line_chart_{timestamp}.png"
    
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    plt.figure(figsize=figsize)
    
    # 处理数据
    if isinstance(data, dict):
        # 字典格式：{label: values}
        for label, values in data.items():
            x = range(len(values)) if labels is None else labels
            plt.plot(x, values, marker='o', linewidth=2.5, label=label, markersize=6)
    elif isinstance(data, list) and all(isinstance(x, (list, np.ndarray)) for x in data):
        # 多个数据系列
        for i, series in enumerate(data):
            x = range(len(series)) if labels is None else labels
            label = f"Series {i+1}"
            plt.plot(x, series, marker='o', linewidth=2.5, label=label, markersize=6)
    else:
        # 单个数据系列
        x = range(len(data)) if labels is None else labels
        plt.plot(x, data, marker='o', linewidth=2.5, color='#667eea', markersize=8)
    
    plt.title(title, fontsize=16, fontweight='bold', pad=20)
    if xlabel:
        plt.xlabel(xlabel, fontsize=12)
    if ylabel:
        plt.ylabel(ylabel, fontsize=12)
    
    if isinstance(data, dict) or (isinstance(data, list) and len(data) > 1):
        plt.legend(frameon=True, shadow=True, fontsize=10)
    
    plt.grid(alpha=0.3)
    plt.tight_layout()
    plt.savefig(str(output_path), dpi=dpi, bbox_inches='tight')
    plt.close()
    
    return str(output_path)

def create_bar_chart(data, labels=None, title="Bar Chart", xlabel=None, ylabel=None,
                    theme="default", output_path=None, figsize=(10, 6), dpi=300, 
                    horizontal=False, stacked=False):
    """创建柱状图"""
    apply_theme(theme)
    
    if output_path is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = OUTPUT_DIR / f"bar_chart_{timestamp}.png"
    
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    plt.figure(figsize=figsize)
    
    # 处理数据
    if isinstance(data, dict):
        # 字典格式：{category: value}
        categories = list(data.keys())
        values = list(data.values())
        
        if horizontal:
            plt.barh(categories, values, color='#667eea', alpha=0.8)
        else:
            plt.bar(categories, values, color='#667eea', alpha=0.8)
    
    elif isinstance(data, list) and all(isinstance(x, dict) for x in data):
        # 分组柱状图：多个字典
        import pandas as pd
        df = pd.DataFrame(data)
        
        if horizontal:
            df.plot(kind='barh', figsize=figsize)
        else:
            df.plot(kind='bar', figsize=figsize, stacked=stacked)
    
    elif isinstance(data, list) and all(isinstance(x, (list, np.ndarray)) for x in data):
        # 多个数据系列
        x = np.arange(len(data[0])) if labels is None else labels
        width = 0.8 / len(data)
        
        for i, series in enumerate(data):
            offset = (i - len(data)/2 + 0.5) * width
            if horizontal:
                plt.barh(x + offset, series, width, label=f"Series {i+1}")
            else:
                plt.bar(x + offset, series, width, label=f"Series {i+1}")
    
    else:
        # 单个数据系列
        x = range(len(data)) if labels is None else labels
        
        if horizontal:
            plt.barh(x, data, color='#667eea', alpha=0.8)
        else:
            plt.bar(x, data, color='#667eea', alpha=0.8)
    
    plt.title(title, fontsize=16, fontweight='bold', pad=20)
    if xlabel:
        plt.xlabel(xlabel, fontsize=12)
    if ylabel:
        plt.ylabel(ylabel, fontsize=12)
    
    if (isinstance(data, list) and len(data) > 1) or (isinstance(data, list) and all(isinstance(x, dict) for x in data)):
        plt.legend(frameon=True, shadow=True, fontsize=10)
    
    plt.grid(axis='y', alpha=0.3)
    plt.tight_layout()
    plt.savefig(str(output_path), dpi=dpi, bbox_inches='tight')
    plt.close()
    
    return str(output_path)

def create_pie_chart(data, labels=None, title="Pie Chart", theme="default", 
                    output_path=None, figsize=(8, 8), dpi=300, explode=None, 
                    autopct='%1.1f%%', shadow=True):
    """创建饼图"""
    apply_theme(theme)
    
    if output_path is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = OUTPUT_DIR / f"pie_chart_{timestamp}.png"
    
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    plt.figure(figsize=figsize)
    
    # 处理数据
    if isinstance(data, dict):
        # 字典格式：{label: value}
        labels = list(data.keys())
        sizes = list(data.values())
    else:
        # 列表格式
        sizes = data
        if labels is None:
            labels = [f"Item {i+1}" for i in range(len(data))]
    
    # 设置爆炸效果
    if explode is None:
        explode = [0.05] * len(sizes)
    elif isinstance(explode, (int, float)):
        explode = [explode] * len(sizes)
    
    # 创建饼图
    colors = sns.color_palette(palette=THEMES[theme]["palette"], n_colors=len(sizes))
    plt.pie(sizes, explode=explode, labels=labels, colors=colors,
            autopct=autopct, shadow=shadow, startangle=90)
    
    plt.title(title, fontsize=16, fontweight='bold', pad=20)
    plt.axis('equal')  # 确保饼图是圆形
    plt.tight_layout()
    plt.savefig(str(output_path), dpi=dpi, bbox_inches='tight')
    plt.close()
    
    return str(output_path)

def create_scatter_plot(x_data, y_data, labels=None, title="Scatter Plot", 
                       xlabel=None, ylabel=None, theme="default", output_path=None,
                       figsize=(10, 6), dpi=300, size=50, alpha=0.7):
    """创建散点图"""
    apply_theme(theme)
    
    if output_path is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = OUTPUT_DIR / f"scatter_plot_{timestamp}.png"
    
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    plt.figure(figsize=figsize)
    
    # 处理数据
    if isinstance(x_data, dict) and isinstance(y_data, dict):
        # 多个数据系列
        for key in x_data.keys():
            if key in y_data:
                plt.scatter(x_data[key], y_data[key], s=size, alpha=alpha, label=key)
    elif isinstance(x_data, list) and isinstance(y_data, list) and len(x_data) == len(y_data):
        # 单个数据系列
        plt.scatter(x_data, y_data, s=size, alpha=alpha, color='#667eea')
    else:
        raise ValueError("x_data 和 y_data 格式不匹配")
    
    plt.title(title, fontsize=16, fontweight='bold', pad=20)
    if xlabel:
        plt.xlabel(xlabel, fontsize=12)
    if ylabel:
        plt.ylabel(ylabel, fontsize=12)
    
    if isinstance(x_data, dict) and isinstance(y_data, dict):
        plt.legend(frameon=True, shadow=True, fontsize=10)
    
    plt.grid(alpha=0.3)
    plt.tight_layout()
    plt.savefig(str(output_path), dpi=dpi, bbox_inches='tight')
    plt.close()
    
    return str(output_path)

def create_area_chart(data, labels=None, title="Area Chart", xlabel=None, ylabel=None,
                     theme="default", output_path=None, figsize=(10, 6), dpi=300,
                     alpha=0.5, stacked=False):
    """创建面积图"""
    apply_theme(theme)
    
    if output_path is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = OUTPUT_DIR / f"area_chart_{timestamp}.png"
    
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    plt.figure(figsize=figsize)
    
    # 处理数据
    x = range(len(data[0])) if labels is None else labels
    
    if stacked:
        # 堆叠面积图
        plt.stackplot(x, data, alpha=alpha)
    else:
        # 普通面积图
        for i, series in enumerate(data):
            plt.fill_between(x, series, alpha=alpha, label=f"Series {i+1}")
    
    plt.title(title, fontsize=16, fontweight='bold', pad=20)
    if xlabel:
        plt.xlabel(xlabel, fontsize=12)
    if ylabel:
        plt.ylabel(ylabel, fontsize=12)
    
    if len(data) > 1:
        plt.legend(frameon=True, shadow=True, fontsize=10)
    
    plt.grid(alpha=0.3)
    plt.tight_layout()
    plt.savefig(str(output_path), dpi=dpi, bbox_inches='tight')
    plt.close()
    
    return str(output_path)

def create_heatmap(data, row_labels=None, col_labels=None, title="Heatmap",
                  theme="default", output_path=None, figsize=(10, 8), dpi=300,
                  cmap="viridis", annot=True, fmt=".2f"):
    """创建热力图"""
    apply_theme(theme)
    
    if output_path is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = OUTPUT_DIR / f"heatmap_{timestamp}.png"
    
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    plt.figure(figsize=figsize)
    
    # 处理数据
    if isinstance(data, list):
        data = np.array(data)
    
    # 创建热力图
    sns.heatmap(data, annot=annot, fmt=fmt, cmap=cmap,
                xticklabels=col_labels, yticklabels=row_labels,
                cbar_kws={'label': 'Value'})
    
    plt.title(title, fontsize=16, fontweight='bold', pad=20)
    plt.tight_layout()
    plt.savefig(str(output_path), dpi=dpi, bbox_inches='tight')
    plt.close()
    
    return str(output_path)

def create_box_plot(data, labels=None, title="Box Plot", xlabel=None, ylabel=None,
                   theme="default", output_path=None, figsize=(10, 6), dpi=300,
                   vert=True, notch=False):
    """创建箱线图"""
    apply_theme(theme)
    
    if output_path is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = OUTPUT_DIR / f"box_plot_{timestamp}.png"
    
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    plt.figure(figsize=figsize)
    
    # 处理数据
    if isinstance(data, dict):
        # 字典格式：{label: values}
        data_list = list(data.values())
        if labels is None:
            labels = list(data.keys())
    elif isinstance(data, list):
        data_list = data
    else:
        raise ValueError("数据格式应为字典或列表")
    
    # 创建箱线图
    bp = plt.boxplot(data_list, labels=labels, vert=vert, notch=notch,
                     patch_artist=True)
    
    # 设置颜色
    colors = sns.color_palette(palette=THEMES[theme]["palette"], n_colors=len(data_list))
    for patch, color in zip(bp['boxes'], colors):
        patch.set_facecolor(color)
        patch.set_alpha(0.7)
    
    plt.title(title, fontsize=16, fontweight='bold', pad=20)
    if xlabel:
        plt.xlabel(xlabel, fontsize=12)
    if ylabel:
        plt.ylabel(ylabel, fontsize=12)
    
    plt.grid(axis='y', alpha=0.3)
    plt.tight_layout()
    plt.savefig(str(output_path), dpi=dpi, bbox_inches='tight')
    plt.close()
    
    return str(output_path)

def create_radar_series(ax, values, labels, label, fill_alpha):
    """创建雷达图数据系列（辅助函数）"""
    import numpy as np
    
    # 角度
    N = len(values)
    angles = np.linspace(0, 2 * np.pi, N, endpoint=False).tolist()
    values = values.tolist() if hasattr(values, 'tolist') else values
    
    # 闭合图形
    values += values[:1]
    angles += angles[:1]
    
    # 绘制
    ax.plot(angles, values, linewidth=2, label=label)
    ax.fill(angles, values, alpha=fill_alpha)

def create_radar_chart(data, labels=None, title="Radar Chart", theme="default",
                      output_path=None, figsize=(8, 8), dpi=300, fill_alpha=0.25):
    """创建雷达图"""
    apply_theme(theme)
    
    if output_path is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = OUTPUT_DIR / f"radar_chart_{timestamp}.png"
    
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    import numpy as np
    
    # 雷达图需要极坐标
    fig = plt.figure(figsize=figsize)
    ax = fig.add_subplot(111, polar=True)
    
    # 处理标签
    if labels is None:
        if isinstance(data, dict):
            labels = list(data.keys())
        else:
            labels = [f"Feature {i+1}" for i in range(len(data[0]))]
    
    # 角度
    N = len(labels)
    angles = np.linspace(0, 2 * np.pi, N, endpoint=False).tolist()
    
    # 设置角度标签
    ax.set_xticks(angles)
    ax.set_xticklabels(labels)
    
    # 处理数据
    if isinstance(data, dict):
        # 多个数据系列
        for label, values in data.items():
            create_radar_series(ax, values, labels, label, fill_alpha)
    elif isinstance(data, list) and all(isinstance(x, (list, np.ndarray)) for x in data):
        # 多个数据系列
        for i, series in enumerate(data):
            label = f"Series {i+1}"
            create_radar_series(ax, series, labels, label, fill_alpha)
    else:
        # 单个数据系列
        create_radar_series(ax, data, labels, "Data", fill_alpha)
    
    # 设置标题和图例
    plt.title(title, fontsize=16, fontweight='bold', pad=20)
    ax.legend(loc='upper right', bbox_to_anchor=(0.1, 0.1))
    
    plt.tight_layout()
    plt.savefig(str(output_path), dpi=dpi, bbox_inches='tight')
    plt.close()
    
    return str(output_path)