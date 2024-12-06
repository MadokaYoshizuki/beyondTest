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
    def _create_heatmap(self, corr_data):
        """ヒートマップを生成する内部メソッド"""
        fig = go.Figure(data=go.Heatmap(
            z=corr_data,
            x=corr_data.columns,
            y=corr_data.columns,
            colorscale='RdBu'
        ))
        fig.update_layout(
            width=800,
            height=800,
            title="相関ヒートマップ"
        )
        return fig

    def _create_bar_chart(self, data, title):
        """棒グラフを生成する内部メソッド"""
        fig = px.bar(x=data.index, y=data.values)
        fig.update_layout(
            width=800,
            height=400,
            title=title,
            xaxis_title="選択肢",
            yaxis_title="回答数"
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

        # 数値分析結果
        elements.append(Paragraph("数値分析結果", styles['Heading1']))
        
        for i, df in enumerate(dfs):
            elements.append(Paragraph(f"データセット {i+1}", styles['Heading2']))
            
            # 基本統計量
            numeric_df = df.select_dtypes(include=['number'])
            if not numeric_df.empty:
                stats = numeric_df.describe()
                table_data = [["統計量"] + list(stats.columns)]
                for idx in stats.index:
                    row = [idx] + ['{:g}'.format(x) if isinstance(x, float) else str(x) for x in stats.loc[idx]]
                    table_data.append(row)
                
                table = Table(table_data)
                table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, 0), 12),
                    ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                    ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ]))
                elements.append(table)
                elements.append(Spacer(1, 20))

            # 複数回答の分析
            multiple_choice_cols = [col for col in df.columns if ',' in str(df[col].iloc[0])]
            if multiple_choice_cols:
                elements.append(Paragraph("複数回答の分析", styles['Heading3']))
                for col in multiple_choice_cols:
                    elements.append(Paragraph(f"質問: {col}", styles['JapaneseParagraph']))
                    values = df[col].str.split(',').explode()
                    counts = values.value_counts()
                    
                    # 棒グラフの生成
                    fig = self._create_bar_chart(counts, f"{col}の回答分布")
                    temp_path = f"temp_bar_{i}_{col}.png"
                    pio.write_image(fig, temp_path)
                    elements.append(Image(temp_path, width=6*inch, height=3*inch))
                    os.remove(temp_path)
                    elements.append(Spacer(1, 20))

        # 相関分析
        elements.append(Paragraph("相関分析", styles['Heading1']))
        
        for i, df in enumerate(dfs):
            elements.append(Paragraph(f"データセット {i+1} の相関分析", styles['Heading2']))
            
            # ヒートマップの生成
            numeric_columns = df.select_dtypes(include=['number']).columns
            if not numeric_columns.empty:
                corr_data = df[numeric_columns].corr()
                fig = self._create_heatmap(corr_data)
                temp_path = f"temp_heatmap_{i}.png"
                pio.write_image(fig, temp_path)
                elements.append(Image(temp_path, width=6*inch, height=6*inch))
                os.remove(temp_path)
                
                # 相関係数の表を追加
                elements.append(Paragraph("相関係数", styles['Heading3']))
                table_data = [[""]+list(corr_data.columns)]
                for idx in corr_data.index:
                    row = [idx] + [f"{x:.2f}" for x in corr_data.loc[idx]]
                    table_data.append(row)
                
                table = Table(table_data)
                table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, 0), 10),
                    ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ]))
                elements.append(table)
            
            elements.append(Spacer(1, 20))

        # PDFの生成
        doc.build(elements)
        return output_path
