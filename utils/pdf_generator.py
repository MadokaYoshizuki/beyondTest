from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
import pandas as pd
import plotly.io as pio
import plotly.graph_objects as go
import plotly.express as px
import os
import streamlit as st

class PDFGenerator:
    def _create_heatmap(self, corr_data, column_names):
        """ヒートマップを生成する内部メソッド"""
        # 列名マッピングを適用
        display_names = [column_names.get(col, col) for col in corr_data.columns]
        
        fig = go.Figure(data=go.Heatmap(
            z=corr_data,
            x=display_names,
            y=display_names,
            colorscale='RdBu'
        ))
        fig.update_layout(
            width=800,
            height=800,
            title="相関ヒートマップ",
            xaxis_title="設問項目",
            yaxis_title="設問項目"
        )
        return fig

    def _create_bar_chart(self, data, title, x_label="選択肢", y_label="回答数"):
        """棒グラフを生成する内部メソッド"""
        fig = px.bar(x=data.index, y=data.values)
        fig.update_layout(
            width=800,
            height=400,
            title=title,
            xaxis_title=x_label,
            yaxis_title=y_label
        )
        return fig

    def generate_pdf(self, dfs, config_manager, visualizer):
        if not dfs:
            st.error("PDFを生成するにはデータが必要です。")
            return None
            
        output_path = "survey_analysis_report.pdf"
        doc = SimpleDocTemplate(output_path, pagesize=A4)
        styles = getSampleStyleSheet()
        
        # カスタムスタイルの追加
        styles.add(ParagraphStyle(
            name='JapaneseParagraph',
            fontName='HeiseiKakuGo-W5',
            fontSize=10,
            leading=14
        ))
        
        elements = []

        # タイトル
        elements.append(Paragraph("意識調査データ分析レポート", styles['Title']))
        elements.append(Spacer(1, 20))

        # 実施概要
        elements.append(Paragraph("実施概要", styles['Heading1']))
        for i, df in enumerate(dfs):
            elements.append(Paragraph(
                f"第{i+1}回調査: {len(df)}件の回答",
                styles['JapaneseParagraph']
            ))
        elements.append(Spacer(1, 20))

        # 列名マッピングの取得
        column_names = config_manager.config.get('column_names', {})

        # 数値分析結果
        elements.append(Paragraph("数値分析結果", styles['Heading1']))
        
        for i, df in enumerate(dfs):
            elements.append(Paragraph(f"データセット {i+1}", styles['Heading2']))
            
            # 基本統計量
            numeric_df = df.select_dtypes(include=['number'])
            if not numeric_df.empty:
                stats = numeric_df.describe()
                # 列名を表示用に変換
                display_cols = [column_names.get(col, col) for col in stats.columns]
                table_data = [["統計量"] + display_cols]
                for idx in stats.index:
                    row = [idx] + ['{:g}'.format(x) if isinstance(x, float) else str(x) for x in stats.loc[idx]]
                    table_data.append(row)
                
                table = Table(table_data)
                table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                    ('FONTNAME', (0, 0), (-1, 0), 'HeiseiKakuGo-W5'),
                    ('FONTSIZE', (0, 0), (-1, 0), 12),
                    ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                    ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ]))
                elements.append(table)
                elements.append(Spacer(1, 20))

            # 複数回答の分析
            multiple_choice_cols = []
            for col in df.columns:
                if not pd.api.types.is_numeric_dtype(df[col]):
                    values = df[col].fillna('').astype(str)
                    if values.str.contains(',').any():
                        multiple_choice_cols.append(col)

            if multiple_choice_cols:
                elements.append(Paragraph("複数回答の分析", styles['Heading3']))
                for col in multiple_choice_cols:
                    display_name = column_names.get(col, col)
                    elements.append(Paragraph(f"質問: {display_name}", styles['JapaneseParagraph']))
                    values = df[col].fillna('').astype(str).str.split(',').explode()
                    counts = values.value_counts().sort_index()
                    
                    # 棒グラフの生成
                    fig = self._create_bar_chart(
                        counts,
                        f"{display_name}の回答分布",
                        "選択肢",
                        "回答数"
                    )
                    temp_path = f"temp_bar_{i}_{col}.png"
                    pio.write_image(fig, temp_path)
                    elements.append(Image(temp_path, width=6*inch, height=3*inch))
                    os.remove(temp_path)
                    
                    # 回答の集計表を追加
                    table_data = [["選択肢", "回答数", "割合(%)"]]
                    total = counts.sum()
                    for answer, count in counts.items():
                        percentage = (count / total) * 100
                        table_data.append([answer, str(count), f"{percentage:.1f}"])
                    
                    table = Table(table_data)
                    table.setStyle(TableStyle([
                        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                        ('FONTNAME', (0, 0), (-1, 0), 'HeiseiKakuGo-W5'),
                        ('GRID', (0, 0), (-1, -1), 1, colors.black),
                    ]))
                    elements.append(table)
                    elements.append(Spacer(1, 20))

        # 相関分析
        elements.append(Paragraph("相関分析", styles['Heading1']))
        
        for i, df in enumerate(dfs):
            elements.append(Paragraph(f"データセット {i+1} の相関分析", styles['Heading2']))
            
            # ヒートマップの生成
            numeric_columns = df.select_dtypes(include=['number']).columns
            if not numeric_columns.empty:
                corr_data = df[numeric_columns].corr()
                fig = self._create_heatmap(corr_data, column_names)
                temp_path = f"temp_heatmap_{i}.png"
                pio.write_image(fig, temp_path)
                elements.append(Image(temp_path, width=6*inch, height=6*inch))
                os.remove(temp_path)
                
                # 相関係数の表を追加
                display_cols = [column_names.get(col, col) for col in corr_data.columns]
                elements.append(Paragraph("相関係数", styles['Heading3']))
                table_data = [[""] + display_cols]
                for idx, display_idx in zip(corr_data.index, display_cols):
                    row = [display_idx] + [f"{x:.2f}" for x in corr_data.loc[idx]]
                    table_data.append(row)
                
                table = Table(table_data)
                table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                    ('FONTNAME', (0, 0), (-1, 0), 'HeiseiKakuGo-W5'),
                    ('FONTSIZE', (0, 0), (-1, 0), 10),
                    ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ]))
                elements.append(table)
            
            elements.append(Spacer(1, 20))

        # PDFの生成
        doc.build(elements)
        return output_path
