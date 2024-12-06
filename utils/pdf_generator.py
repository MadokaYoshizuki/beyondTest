from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image, PageBreak
from reportlab.platypus import Frame, PageTemplate
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, cm
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import pandas as pd
import plotly.io as pio
import plotly.graph_objects as go
import plotly.express as px
import os
import streamlit as st
from datetime import datetime

class PDFGenerator:
    def __init__(self):
        # 日本語フォントの登録
        font_path = "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc"
        pdfmetrics.registerFont(TTFont('NotoSans', font_path))
        
    def _create_header_footer(self, canvas, doc):
        """ヘッダーとフッターを描画"""
        canvas.saveState()
        
        # ヘッダー
        canvas.setFont('NotoSans', 8)
        canvas.drawString(doc.leftMargin, doc.height + doc.topMargin + 10, "意識調査データ分析レポート")
        canvas.drawString(doc.width + doc.leftMargin - 100, doc.height + doc.topMargin + 10,
                         datetime.now().strftime("%Y年%m月%d日"))
        
        # フッター（ページ番号）
        canvas.drawString(doc.width/2 + doc.leftMargin, doc.bottomMargin - 20,
                         f"- {canvas.getPageNumber()} -")
        
        canvas.restoreState()
        
    def _create_title_page(self):
        """タイトルページの要素を生成"""
        elements = []
        
        # タイトル
        title_style = ParagraphStyle(
            'CustomTitle',
            fontName='NotoSans',
            fontSize=24,
            leading=30,
            alignment=1,
            spaceAfter=30
        )
        elements.append(Spacer(1, 2*inch))
        elements.append(Paragraph("意識調査データ分析レポート", title_style))
        
        # 日付
        date_style = ParagraphStyle(
            'Date',
            fontName='NotoSans',
            fontSize=12,
            alignment=1,
            spaceAfter=1*inch
        )
        elements.append(Spacer(1, 1*inch))
        elements.append(Paragraph(datetime.now().strftime("%Y年%m月%d日"), date_style))
        
        elements.append(PageBreak())
        return elements
        
    def _create_toc(self):
        """目次を生成"""
        elements = []
        
        # 目次タイトル
        toc_title_style = ParagraphStyle(
            'TOCTitle',
            fontName='NotoSans',
            fontSize=16,
            leading=20,
            spaceAfter=20
        )
        elements.append(Paragraph("目次", toc_title_style))
        
        # 目次項目のスタイル
        toc_item_style = ParagraphStyle(
            'TOCItem',
            fontName='NotoSans',
            fontSize=12,
            leading=14,
            leftIndent=20
        )
        
        # 目次項目の追加
        elements.append(Paragraph("1. 実施概要", toc_item_style))
        elements.append(Paragraph("2. 数値分析結果", toc_item_style))
        elements.append(Paragraph("3. 複数回答の分析", toc_item_style))
        elements.append(Paragraph("4. 相関分析", toc_item_style))
        
        elements.append(PageBreak())
        return elements
        
    def _create_heatmap(self, corr_data, column_names):
        """ヒートマップを生成する内部メソッド"""
        # 列名マッピングを適用
        display_names = [column_names.get(col, col) for col in corr_data.columns]
        
        fig = go.Figure(data=go.Heatmap(
            z=corr_data,
            x=display_names,
            y=display_names,
            colorscale='RdBu',
            text=[[f'{val:.2f}' for val in row] for row in corr_data.values],
            texttemplate='%{text}',
            textfont={"size": 10},
            hoverongaps=False
        ))
        
        fig.update_layout(
            width=1000,
            height=1000,
            title={
                'text': "相関ヒートマップ",
                'x': 0.5,
                'xanchor': 'center',
                'font': {'size': 24}
            },
            xaxis_title="設問項目",
            yaxis_title="設問項目",
            xaxis={'tickangle': 45},
            margin=dict(t=100, l=100, r=100, b=100),
            font=dict(size=12)
        )
        
        return fig

    def _create_bar_chart(self, data, title, x_label="選択肢", y_label="回答数"):
        """棒グラフを生成する内部メソッド"""
        fig = go.Figure(data=[
            go.Bar(
                x=data.index,
                y=data.values,
                text=data.values,
                textposition='auto',
                hoverinfo='x+y',
                marker_color='rgb(55, 83, 109)'
            )
        ])
        
        fig.update_layout(
            width=1000,
            height=500,
            title={
                'text': title,
                'x': 0.5,
                'xanchor': 'center',
                'font': {'size': 20}
            },
            xaxis_title=x_label,
            yaxis_title=y_label,
            xaxis={'tickangle': 45},
            margin=dict(t=100, l=100, r=100, b=100),
            font=dict(size=12),
            showlegend=False
        )
        
        return fig

    def generate_pdf(self, dfs, config_manager, visualizer):
        if not dfs:
            st.error("PDFを生成するにはデータが必要です。")
            return None
            
        output_path = "survey_analysis_report.pdf"
        
        # ドキュメントの基本設定
        doc = SimpleDocTemplate(
            output_path,
            pagesize=A4,
            leftMargin=2*cm,
            rightMargin=2*cm,
            topMargin=2.5*cm,
            bottomMargin=2.5*cm
        )
        
        # ヘッダー・フッター付きのページテンプレート作成
        frame = Frame(
            doc.leftMargin,
            doc.bottomMargin,
            doc.width,
            doc.height,
            id='normal'
        )
        template = PageTemplate(
            id='header_footer',
            frames=frame,
            onPage=self._create_header_footer
        )
        doc.addPageTemplates([template])
        
        # スタイルの設定
        styles = getSampleStyleSheet()
        
        # カスタムスタイルの追加
        styles.add(ParagraphStyle(
            name='JapaneseParagraph',
            fontName='NotoSans',
            fontSize=10,
            leading=14
        ))
        
        styles.add(ParagraphStyle(
            name='Heading1',
            fontName='NotoSans',
            fontSize=16,
            leading=20,
            spaceBefore=20,
            spaceAfter=10
        ))
        
        styles.add(ParagraphStyle(
            name='Heading2',
            fontName='NotoSans',
            fontSize=14,
            leading=18,
            spaceBefore=15,
            spaceAfter=8
        ))
        
        elements = []

        # タイトルページの追加
        elements.extend(self._create_title_page())
        
        # 目次の追加
        elements.extend(self._create_toc())
        
        # 実施概要
        elements.append(Paragraph("1. 実施概要", styles['Heading1']))
        elements.append(Paragraph(
            "本レポートは、意識調査の分析結果をまとめたものです。",
            styles['JapaneseParagraph']
        ))
        elements.append(Spacer(1, 0.5*cm))
        
        for i, df in enumerate(dfs):
            elements.append(Paragraph(
                f"第{i+1}回調査: {len(df)}件の回答",
                styles['JapaneseParagraph']
            ))
        elements.append(Spacer(1, 1*cm))

        # 列名マッピングの取得
        column_names = config_manager.config.get('column_names', {})

        # 数値分析結果
        elements.append(Paragraph("2. 数値分析結果", styles['Heading1']))
        elements.append(Paragraph(
            "各設問項目の数値データについて、基本統計量を算出し分析を行いました。",
            styles['JapaneseParagraph']
        ))
        elements.append(Spacer(1, 0.5*cm))
        
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
            elements.append(Paragraph("3. 複数回答の分析", styles['Heading1']))
            elements.append(Paragraph(
                "複数回答方式の設問について、回答の分布と傾向を分析しました。",
                styles['JapaneseParagraph']
            ))
            elements.append(Spacer(1, 0.5*cm))
            
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
