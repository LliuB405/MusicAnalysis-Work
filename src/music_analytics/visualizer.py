# -*- coding: utf-8 -*-
"""
可视化模块 - 图表生成层
"""

import os
import io
import csv
import base64
import logging
from datetime import datetime
from typing import List, Optional, Dict, Any, Union

import matplotlib
matplotlib.use('Agg')  # 非交互式后端
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.font_manager import FontProperties  # noqa: E402
from wordcloud import WordCloud  # noqa: E402

from .config import Config
from .models import ArtistStat, SongData

logger = logging.getLogger(__name__)


class ChartGenerator:
    """图表生成类"""

    def __init__(self, config: Optional[Config] = None) -> None:
        self.config: Config = config or Config()
        self._font_path: Optional[str] = None

    def _find_chinese_font(self) -> Optional[str]:
        """查找中文字体"""
        if self._font_path:
            return self._font_path

        for path in self.config.font_paths:
            if os.path.exists(path):
                self._font_path = path
                logger.info(f"找到中文字体: {path}")
                return path

        logger.warning("未找到中文字体")
        return None

    def _get_font(self, size: int = 12) -> Optional[FontProperties]:
        """获取字体属性"""
        font_path = self._find_chinese_font()
        if font_path:
            return FontProperties(fname=font_path, size=size)
        return None

    def generate_bar_chart(
        self,
        top10: List[ArtistStat],
    ) -> Optional[str]:
        """生成 TOP10 歌手柱状图（返回 base64）"""
        if not top10:
            return None

        font: Optional[FontProperties] = self._get_font(14)

        # 设置画布
        plt.figure(figsize=(12, 7), dpi=100)
        plt.rcParams['axes.unicode_minus'] = False

        names: List[str] = [stat.name for stat in top10]
        counts: List[int] = [stat.count for stat in top10]

        # 颜色方案
        colors: List[str] = [
            "#E74C3C", "#E67E22", "#F1C40F", "#2ECC71", "#1ABC9C",
            "#3498DB", "#9B59B6", "#E91E63", "#FF6F00", "#00BCD4"
        ]

        bars = plt.bar(names, counts, color=colors, width=0.6,
                       edgecolor='white', linewidth=1.2)

        # 标注数值
        for bar, count in zip(bars, counts):
            plt.text(
                bar.get_x() + bar.get_width() / 2,
                bar.get_height() + 0.3,
                str(count),
                ha='center', va='bottom',
                fontsize=12, fontweight='bold',
            )

        # 标题和标签
        title: str = "热歌榜歌手TOP10 - 上榜歌曲数量"
        xlabel: str = "歌手名称"
        ylabel: str = "上榜歌曲数量"

        if font:
            plt.title(title, fontsize=18, fontweight='bold',
                      fontproperties=font, pad=20)
            plt.xlabel(xlabel, fontsize=14, fontproperties=font)
            plt.ylabel(ylabel, fontsize=14, fontproperties=font)
            plt.xticks(fontproperties=font, fontsize=11, rotation=30)
        else:
            plt.title(title, fontsize=18, fontweight='bold', pad=20)
            plt.xlabel(xlabel, fontsize=14)
            plt.ylabel(ylabel, fontsize=14)
            plt.xticks(fontsize=11, rotation=30)

        plt.grid(axis='y', alpha=0.3, linestyle='--')
        plt.tight_layout()

        # 保存到内存
        buf = io.BytesIO()
        plt.savefig(buf, format='png', dpi=100, bbox_inches='tight')
        plt.close()
        buf.seek(0)

        return base64.b64encode(buf.read()).decode('utf-8')

    def generate_wordcloud(
        self,
        artist_counter: Dict[str, int],
    ) -> Optional[str]:
        """生成词云图（返回 base64）"""
        if not artist_counter:
            return None

        font_path: Optional[str] = self._find_chinese_font()

        wc = WordCloud(
            width=800,
            height=500,
            background_color='white',
            font_path=font_path,
            max_words=200,
            max_font_size=150,
            min_font_size=12,
            random_state=42,
            colormap='viridis',
            collocations=False,
        )

        wc.generate_from_frequencies(artist_counter)

        buf = io.BytesIO()
        wc.to_image().save(buf, format='PNG')
        buf.seek(0)

        return base64.b64encode(buf.read()).decode('utf-8')

    def generate_csv(
        self,
        songs: List[SongData],
        headers: Optional[List[str]] = None,
        artist_counter: Optional[Dict[str, int]] = None,
        heatmap_data: Optional[Dict[str, List[int]]] = None,
        heatmap_labels: Optional[List[str]] = None,
    ) -> Optional[str]:
        """生成 CSV 文件（返回内容字符串）

        支持多 section（用空行 + section header 分割）：
          1. 热歌榜歌曲列表
          2. 歌手词云榜（出现次数）
          3. 歌手-排名热力榜
        """
        if not songs and not artist_counter and not heatmap_data:
            return None

        if headers is None:
            headers = ["排名", "歌曲名称", "歌手名称"]

        output = io.StringIO()
        # UTF-8 BOM，兼容 Excel
        output.write('\ufeff')
        writer = csv.writer(output)

        # ===== Section 1: 热歌榜 =====
        writer.writerow(["# 网易云音乐热歌榜"])
        writer.writerow([f"# 导出时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"])
        writer.writerow([f"# 歌曲总数: {len(songs)}"])
        if songs:
            output.write('\n')  # 空行分隔
            writer.writerow(headers)
            for song in songs:
                writer.writerow([song.rank, song.title, song.artist])

        # ===== Section 2: 词云榜（歌手出现次数） =====
        if artist_counter:
            output.write('\n\n')
            writer.writerow(["# 歌手词云榜（出现次数 TOP 50）"])
            output.write('\n')
            writer.writerow(["排名", "歌手", "出现次数", "占比%"])
            total_count = sum(artist_counter.values()) or 1
            sorted_artists = sorted(artist_counter.items(), key=lambda x: x[1], reverse=True)[:50]
            for i, (name, count) in enumerate(sorted_artists, 1):
                pct = round(count * 100 / total_count, 2)
                writer.writerow([i, name, count, pct])

        # ===== Section 3: 热力榜（歌手 × 排名区间） =====
        if heatmap_data and heatmap_labels:
            output.write('\n\n')
            writer.writerow(["# 歌手-排名热力榜（每个单元 = 该歌手在对应排名区间的歌曲数）"])
            output.write('\n')
            # 表头：歌手 | 1-10 | 11-25 | ... | 合计
            header_row = ["歌手"] + heatmap_labels + ["合计"]
            writer.writerow(header_row)
            # 按合计降序
            sorted_artists = sorted(
                heatmap_data.items(),
                key=lambda x: sum(x[1]),
                reverse=True,
            )
            for name, row in sorted_artists:
                total = sum(row)
                writer.writerow([name] + list(row) + [total])

        output.seek(0)
        return output.getvalue()

    def save_bar_chart(
        self,
        top10: List[ArtistStat],
        save_path: str,
    ) -> bool:
        """保存柱状图到文件"""
        try:
            if not top10:
                return False

            font: Optional[FontProperties] = self._get_font(13)

            fig, ax = plt.subplots(figsize=(14, 7))

            df_sorted: List[ArtistStat] = sorted(top10, key=lambda x: x.count, reverse=True)
            names: List[str] = [s.name for s in df_sorted]
            counts: List[int] = [s.count for s in df_sorted]

            colors = plt.cm.Reds([
                (i + 3) / (len(df_sorted) + 4)
                for i in range(len(df_sorted))
            ])

            bars = ax.barh(names, counts, height=0.6, color=colors,
                           edgecolor='#8B0000', linewidth=0.8)

            for bar, val in zip(bars, counts):
                ax.text(
                    bar.get_width() + 0.2,
                    bar.get_y() + bar.get_height() / 2,
                    str(val),
                    va='center', fontsize=12,
                    fontproperties=font,
                )

            title: str = "网易云音乐热歌榜 — 歌手上榜次数 TOP10"
            if font:
                ax.set_title(title, fontproperties=font,
                             fontweight='bold', pad=20)
                ax.set_xlabel("上榜歌曲数量", fontproperties=font)
                ax.set_ylabel("歌手名称", fontproperties=font)
                for label in ax.get_yticklabels():
                    label.set_fontproperties(font)

            ax.xaxis.grid(True, linestyle='--', alpha=0.4)
            ax.set_axisbelow(True)
            ax.spines['top'].set_visible(False)
            ax.spines['right'].set_visible(False)

            max_val: int = max(counts)
            ax.set_xlim(0, max_val * 1.25)

            plt.tight_layout()
            plt.savefig(save_path, dpi=150, bbox_inches='tight',
                        facecolor='white')
            plt.close()

            logger.info(f"柱状图已保存: {save_path}")
            return True

        except Exception as e:
            logger.error(f"保存柱状图失败: {e}")
            return False

    def save_wordcloud(
        self,
        artist_counter: Dict[str, int],
        save_path: str,
    ) -> bool:
        """保存词云图到文件"""
        try:
            font_path: Optional[str] = self._find_chinese_font()

            wc = WordCloud(
                width=1200,
                height=800,
                background_color="white",
                font_path=font_path,
                max_words=200,
                max_font_size=160,
                min_font_size=14,
                random_state=42,
                colormap="Reds",
                collocations=False,
            )

            wc.generate_from_frequencies(artist_counter)
            wc.to_file(save_path)

            logger.info(f"词云图已保存: {save_path}")
            return True

        except Exception as e:
            logger.error(f"保存词云图失败: {e}")
            return False

    def generate_pie_chart(
        self,
        top10: List[ArtistStat],
    ) -> Optional[str]:
        """生成 TOP10 歌手饼图（返回 base64）"""
        if not top10:
            return None

        import numpy as np

        font: Optional[FontProperties] = self._get_font(14)

        # 数据准备
        labels = [f"#{i+1}" for i in range(len(top10))]
        sizes = [stat.count for stat in top10]
        total = sum(sizes)

        # 颜色方案 - 红色系渐变
        colors = plt.cm.Reds(np.linspace(0.3, 0.9, len(labels)))[::-1]

        # 创建图表
        fig, ax = plt.subplots(figsize=(10, 10))

        # 绘制环形图（中间空心）
        wedges, texts, autotexts = ax.pie(
            sizes,
            labels=labels,
            colors=colors,
            autopct=lambda pct: f'{pct:.1f}%\n({int(pct/100*total)})' if pct > 5 else '',
            startangle=90,
            pctdistance=0.75,
            wedgeprops=dict(width=0.5, edgecolor='white', linewidth=2),
            textprops=dict(fontsize=12)
        )

        # 标题 (中文)
        title_text = "热歌榜歌手占比分布"
        if font:
            ax.set_title(title_text, fontsize=16, fontweight='bold', pad=20, fontproperties=font)
        else:
            ax.set_title(title_text, fontsize=16, fontweight='bold', pad=20)

        # 添加图例（显示歌手名和上榜次数）
        legend_labels = [f'#{i+1} {stat.name} ({stat.count}首)' for i, stat in enumerate(top10)]
        if font:
            ax.legend(wedges, legend_labels, title="排名", loc="center left",
                    bbox_to_anchor=(1, 0, 0.5, 1), fontsize=9, prop=font)
        else:
            ax.legend(wedges, legend_labels, title="排名", loc="center left",
                    bbox_to_anchor=(1, 0, 0.5, 1), fontsize=9)

        plt.tight_layout()

        # 保存到内存
        buf = io.BytesIO()
        plt.savefig(buf, format='png', dpi=150, bbox_inches='tight', facecolor='white')
        plt.close()
        buf.seek(0)

        return base64.b64encode(buf.read()).decode('utf-8')

    def generate_line_chart(
        self,
        songs: List[SongData],
    ) -> Optional[str]:
        """生成排名趋势折线图（返回 base64）"""
        if not songs:
            return None

        font: Optional[FontProperties] = self._get_font(12)

        # 取前20名数据进行趋势展示
        top20 = songs[:20]

        # 创建图表
        fig, ax = plt.subplots(figsize=(14, 6))

        # 提取排名
        ranks = list(range(1, len(top20) + 1))

        # 绘制折线图
        ax.plot(ranks, marker='o', markersize=8, linewidth=2, color='#E74C3C',
               markerfacecolor='white', markeredgewidth=2)

        # 标题和标签 (中文)
        title_text = "热歌榜 TOP20 排名趋势"
        xlabel_text = "排名"
        ylabel_text = "位置"

        if font:
            ax.set_title(title_text, fontsize=14, fontweight='bold', pad=15, fontproperties=font)
            ax.set_xlabel(xlabel_text, fontsize=12, fontproperties=font)
            ax.set_ylabel(ylabel_text, fontsize=12, fontproperties=font)
        else:
            ax.set_title(title_text, fontsize=14, fontweight='bold', pad=15)
            ax.set_xlabel(xlabel_text, fontsize=12)
            ax.set_ylabel(ylabel_text, fontsize=12)

        # 反转 Y 轴使排名1在最上面
        ax.invert_yaxis()

        # 网格和样式
        ax.xaxis.grid(True, linestyle='--', alpha=0.4)
        ax.set_axisbelow(True)
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)

        # 设置 X 轴范围
        ax.set_xlim(0, 21)

        plt.tight_layout()

        # 保存到内存
        buf = io.BytesIO()
        plt.savefig(buf, format='png', dpi=150, bbox_inches='tight', facecolor='white')
        plt.close()
        buf.seek(0)

        return base64.b64encode(buf.read()).decode('utf-8')

    def generate_heatmap(
        self,
        top_artists: List[ArtistStat],
        songs: List[SongData],
    ) -> Optional[str]:
        """生成歌手-歌���热力图（返回 base64）"""
        if not top_artists or not songs:
            return None

        import numpy as np
        import pandas as pd

        font: Optional[FontProperties] = self._get_font(12)

        # 获取TOP15歌手
        top15_names = [stat.name for stat in top_artists[:15]]
        if not top15_names:
            return None

        # 创建排名区间
        bins = [0, 10, 25, 50, 75, 100, 150, 200]
        labels = ['1-10', '11-25', '26-50', '51-75', '76-100', '101-150', '101-200'][:len(bins) - 1]

        # 构建热力图数据
        data = []
        for artist in top15_names:
            row = []
            for i in range(len(bins) - 1):
                low, high = bins[i], bins[i+1]
                count = sum(1 for s in songs[low-1:high] if artist in s.artist)
                row.append(count)
            data.append(row)

        if not data:
            return None

        # 创建DataFrame
        num_cols = len(labels)
        df = pd.DataFrame(data, index=top15_names, columns=labels[:num_cols])

        # 创建热力图
        fig, ax = plt.subplots(figsize=(12, 8))

        im = ax.imshow(df.values, cmap='YlOrRd', aspect='auto')

        # 设置刻度
        ax.set_xticks(range(num_cols))
        ax.set_xticklabels(labels[:num_cols], fontproperties=font)
        ax.set_yticks(range(len(top15_names)))
        ax.set_yticklabels(top15_names, fontproperties=font, fontsize=10)

        # 标题
        ax.set_title("歌手排名热力图", fontsize=14, fontweight='bold', pad=15, fontproperties=font)
        ax.set_xlabel("排名区间", fontsize=12, fontproperties=font)
        ax.set_ylabel("歌手", fontsize=12, fontproperties=font)

        # 添加数值标注
        for i in range(len(top15_names)):
            for j in range(len(df.columns)):
                val = df.values[i, j]
                color = 'white' if val > df.values.max() / 2 else 'black'
                ax.text(j, i, str(val), ha='center', va='center', color=color, fontsize=10, fontproperties=font)

        # 颜色条
        cbar = plt.colorbar(im, ax=ax)
        if font:
            cbar.set_label('歌曲数量', fontproperties=font)
        else:
            cbar.set_label('歌曲数量')

        plt.tight_layout()

        # 保存到内存
        buf = io.BytesIO()
        plt.savefig(buf, format='png', dpi=150, bbox_inches='tight', facecolor='white')
        plt.close()
        buf.seek(0)

        return base64.b64encode(buf.read()).decode('utf-8')

    def generate_excel(
        self,
        songs: List[SongData],
        artist_counter: Optional[Dict[str, int]] = None,
        chart_name: str = "热歌榜",
        rank_changes: Optional[List[Dict[str, Any]]] = None,
        trend_data: Optional[Dict[str, List[Dict[str, Any]]]] = None,
    ) -> Optional[bytes]:
        """生成 Excel 多 Sheet 报表

        Sheet 结构：
        1. 歌曲列表
        2. 歌手统计
        3. 排名变化
        4. 趋势分析
        """
        try:
            import pandas as pd

            # 准备数据
            # Sheet 1: 歌曲列表
            songs_df = pd.DataFrame([
                {
                    "排名": song.rank,
                    "歌曲名称": song.title,
                    "歌手": song.artist
                }
                for song in songs
            ])

            # Sheet 2: 歌手统计
            if artist_counter:
                total = sum(artist_counter.values()) or 1
                sorted_artists = sorted(artist_counter.items(), key=lambda x: x[1], reverse=True)[:50]
                artists_df = pd.DataFrame([
                    {
                        "排名": i + 1,
                        "歌手": name,
                        "上榜次数": count,
                        "占比": f"{count * 100 / total:.2f}%"
                    }
                    for i, (name, count) in enumerate(sorted_artists)
                ])
            else:
                artists_df = pd.DataFrame(columns=["排名", "歌手", "上榜次数", "占比"])

            # Sheet 3: 排名变化
            if rank_changes:
                changes_df = pd.DataFrame(rank_changes)
                if not changes_df.empty:
                    changes_df = changes_df[["title", "artist", "old_rank", "new_rank", "rank_change"]]
                    changes_df.columns = ["歌曲", "歌手", "原排名", "新排名", "变化"]
            else:
                changes_df = pd.DataFrame(columns=["歌曲", "歌手", "原排名", "新排名", "变化"])

            # Sheet 4: 趋势分析
            if trend_data:
                trend_dfs = {}
                for song_key, trend_points in trend_data.items():
                    if trend_points:
                        trend_dfs[song_key] = pd.DataFrame(trend_points)
            else:
                trend_dfs = {}

            # 写入 Excel（多个 Sheet）
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                # Sheet 1: 歌曲列表
                songs_df.to_excel(writer, sheet_name="歌曲列表", index=False)

                # Sheet 2: 歌手统计
                artists_df.to_excel(writer, sheet_name="歌手统计", index=False)

                # Sheet 3: 排名变化
                if not changes_df.empty:
                    changes_df.to_excel(writer, sheet_name="排名变化", index=False)

                # Sheet 4: 趋势分析（每个歌曲一个子 Sheet）
                if trend_dfs:
                    for song_key, df in trend_dfs.items():
                        # 限制 sheet 名称长度
                        sheet_name = song_key[:31]
                        df.to_excel(writer, sheet_name=sheet_name, index=False)

            output.seek(0)
            return output.getvalue()

        except ImportError:
            logger.error("需要安装 openpyxl 库来生成 Excel 文件")
            return None
        except Exception as e:
            logger.error(f"生成 Excel 失败: {e}")
            return None

    def save_excel(
        self,
        songs: List[SongData],
        save_path: str,
        artist_counter: Optional[Dict[str, int]] = None,
        chart_name: str = "热歌榜",
        rank_changes: Optional[List[Dict[str, Any]]] = None,
        trend_data: Optional[Dict[str, List[Dict[str, Any]]]] = None,
    ) -> bool:
        """保存 Excel 文件"""
        try:
            content = self.generate_excel(
                songs, artist_counter, chart_name, rank_changes, trend_data
            )
            if content is None:
                return False

            with open(save_path, 'wb') as f:
                f.write(content)

            logger.info(f"Excel 已保存: {save_path}")
            return True

        except Exception as e:
            logger.error(f"保存 Excel 失败: {e}")
            return False

    def generate_trend_chart(
        self,
        trend_data: List[Dict[str, Any]],
        song_title: str = "",
        artist: str = "",
    ) -> Optional[str]:
        """生成歌曲排名趋势折线图（返回 base64）

        参数:
            trend_data: [{"rank": 1, "timestamp": "2025-01-01T12:00:00"}, ...]
            song_title: 歌曲名（用于标题）
            artist: 歌手名（用于标题）
        """
        if not trend_data or len(trend_data) < 2:
            return None

        from datetime import datetime as dt

        font: Optional[FontProperties] = self._get_font(12)
        title_font: Optional[FontProperties] = self._get_font(14)

        # 解析时间戳和排名
        timestamps: List[dt] = []
        ranks: List[int] = []
        for point in trend_data:
            try:
                ts = dt.fromisoformat(point["timestamp"])
                timestamps.append(ts)
                ranks.append(int(point["rank"]))
            except (ValueError, KeyError):
                continue

        if len(timestamps) < 2:
            return None

        # 创建图表
        fig, ax = plt.subplots(figsize=(14, 6))

        # 绘制主折线
        ax.plot(
            timestamps, ranks,
            marker='o', markersize=6,
            linewidth=2.5,
            color='#E74C3C',
            markerfacecolor='white',
            markeredgewidth=2,
            markeredgecolor='#E74C3C',
            zorder=5,
        )

        # 填充区域（渐变感）
        ax.fill_between(timestamps, ranks, max(ranks) + 5,
                        alpha=0.08, color='#E74C3C')

        # 反转 Y 轴（排名越小越好）
        ax.invert_yaxis()
        ax.set_ylim(max(ranks) + 2, max(0, min(ranks) - 2))

        # 标题
        title_text = f"「{song_title}」- {artist} 排名趋势" if song_title else "歌曲排名趋势"
        if title_font:
            ax.set_title(title_text, fontsize=16, fontweight='bold',
                         pad=20, fontproperties=title_font)
        else:
            ax.set_title(title_text, fontsize=16, fontweight='bold', pad=20)

        # 轴标签
        if font:
            ax.set_xlabel("时间", fontsize=12, fontproperties=font)
            ax.set_ylabel("排名", fontsize=12, fontproperties=font)
        else:
            ax.set_xlabel("时间", fontsize=12)
            ax.set_ylabel("排名", fontsize=12)

        # 标注每个点的数值
        for ts, r in zip(timestamps, ranks):
            ax.annotate(
                f"#{r}", (ts, r),
                textcoords="offset points",
                xytext=(0, -15),
                ha='center', fontsize=9,
                color='#555',
                fontproperties=font,
            )

        # 样式
        ax.xaxis.grid(True, linestyle='--', alpha=0.3)
        ax.yaxis.grid(True, linestyle='--', alpha=0.3)
        ax.set_axisbelow(True)
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)

        # 时间轴格式化
        fig.autofmt_xdate(rotation=30, ha='right')

        plt.tight_layout()

        # 保存到内存
        buf = io.BytesIO()
        plt.savefig(buf, format='png', dpi=150, bbox_inches='tight', facecolor='white')
        plt.close()
        buf.seek(0)

        return base64.b64encode(buf.read()).decode('utf-8')

    def generate_pdf(
        self,
        songs: List[SongData],
        artist_counter: Optional[Dict[str, int]] = None,
        top10: Optional[List[ArtistStat]] = None,
        chart_name: str = "热歌榜",
    ) -> Optional[bytes]:
        """生成 PDF 报表"""
        try:
            from reportlab.lib.pagesizes import A4
            from reportlab.lib import colors
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
            from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
            from reportlab.lib.units import cm
            from reportlab.pdfbase import pdfmetrics
            from reportlab.pdfbase.ttfonts import TTFont

            # 尝试注册中文字体
            font_path = self._find_chinese_font()
            if font_path:
                try:
                    pdfmetrics.registerFont(TTFont('ChineseFont', font_path))
                except Exception:
                    font_path = None

            # 创建 PDF
            output = io.BytesIO()
            doc = SimpleDocTemplate(
                output,
                pagesize=A4,
                rightMargin=2*cm,
                leftMargin=2*cm,
                topMargin=2*cm,
                bottomMargin=2*cm
            )

            # 样式
            styles = getSampleStyleSheet()
            title_style = ParagraphStyle(
                'CustomTitle',
                parent=styles['Heading1'],
                fontSize=18,
                spaceAfter=30,
                alignment=1,  # 居中
            )

            if font_path:
                title_style.fontName = 'ChineseFont'

            subtitle_style = ParagraphStyle(
                'CustomSubtitle',
                parent=styles['Heading2'],
                fontSize=14,
                spaceAfter=20,
            )

            if font_path:
                subtitle_style.fontName = 'ChineseFont'

            body_style = ParagraphStyle(
                'CustomBody',
                parent=styles['Normal'],
                fontSize=10,
                spaceAfter=12,
            )

            if font_path:
                body_style.fontName = 'ChineseFont'

            # 构建内容
            elements = []

            # 标题
            title = f"网易云音乐 {chart_name} 分析报告"
            elements.append(Paragraph(title, title_style))
            elements.append(Paragraph(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", body_style))
            elements.append(Spacer(1, 20))

            # 概览
            elements.append(Paragraph("一、数据概览", subtitle_style))
            overview_data = [
                ["指标", "数值"],
                ["歌曲总数", str(len(songs))],
                ["歌手数量", str(len(artist_counter) if artist_counter else "N/A")],
                ["榜单名称", chart_name],
            ]
            overview_table = Table(overview_data, colWidths=[5*cm, 5*cm])
            overview_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.red),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ]))
            elements.append(overview_table)
            elements.append(Spacer(1, 30))

            # TOP 10 歌手
            if top10:
                elements.append(Paragraph("二、TOP 10 歌手", subtitle_style))
                top10_data = [["排名", "歌手", "上榜次数"]]
                for i, stat in enumerate(top10[:10], 1):
                    top10_data.append([str(i), stat.name, str(stat.count)])

                top10_table = Table(top10_data, colWidths=[3*cm, 5*cm, 3*cm])
                top10_table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.darkred),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, -1), 10),
                    ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                    ('BACKGROUND', (0, 1), (-1, -1), colors.lightgrey),
                    ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ]))
                elements.append(top10_table)
                elements.append(Spacer(1, 30))

            # 歌曲列表（只显示前20）
            elements.append(Paragraph("三、歌曲列表 TOP 20", subtitle_style))
            songs_data = [["排名", "歌曲名称", "歌手"]]
            for song in songs[:20]:
                songs_data.append([
                    str(song.rank),
                    song.title[:30] + "..." if len(song.title) > 30 else song.title,
                    song.artist[:20] + "..." if len(song.artist) > 20 else song.artist
                ])

            songs_table = Table(songs_data, colWidths=[2*cm, 5*cm, 4*cm])
            songs_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.red),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 8),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.white),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ]))
            elements.append(songs_table)

            # 页脚
            elements.append(Spacer(1, 50))
            footer_style = ParagraphStyle(
                'Footer',
                parent=styles['Normal'],
                fontSize=8,
                textColor=colors.grey,
                alignment=1,
            )
            elements.append(Paragraph(
                "本报告由网易云音乐数据分析系统自动生成",
                footer_style
            ))

            # 生成 PDF
            doc.build(elements)
            output.seek(0)
            return output.getvalue()

        except ImportError as e:
            logger.error(f"缺少必要的库来生成 PDF: {e}")
            return None
        except Exception as e:
            logger.error(f"生成 PDF 失败: {e}")
            return None

    def save_pdf(
        self,
        songs: List[SongData],
        save_path: str,
        artist_counter: Optional[Dict[str, int]] = None,
        top10: Optional[List[ArtistStat]] = None,
        chart_name: str = "热歌榜",
    ) -> bool:
        """保存 PDF 文件"""
        try:
            content = self.generate_pdf(songs, artist_counter, top10, chart_name)
            if content is None:
                return False

            with open(save_path, 'wb') as f:
                f.write(content)

            logger.info(f"PDF 已保存: {save_path}")
            return True

        except Exception as e:
            logger.error(f"保存 PDF 失败: {e}")
            return False
