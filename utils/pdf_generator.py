from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image, PageBreak
from reportlab.platypus import Frame, PageTemplate, KeepTogether
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
        # 日本語フォントの設定
        try:
            pdfmetrics.registerFont(TTFont('NotoSans', 'NotoSansCJKjp-Regular.ttf'))
        except:
            st.warning("日本語フォントが見つかりません。デフォルトフォントを使用します。")

        # スタイルの設定
        self.styles = getSampleStyleSheet()
        
        # カスタムスタイルの追加
        self.styles.add(ParagraphStyle(
            name='JapaneseParagraph',
            fontName='NotoSans' if 'NotoSans' in pdfmetrics.getRegisteredFontNames() else 'Helvetica',
            fontSize=10,
            leading=14
        ))
        
        # 既存のヘッディングスタイルを日本語フォントで上書き
        for style_name in ['Title', 'Heading1', 'Heading2', 'Heading3']:
            if style_name in self.styles:
                self.styles[style_name].fontName = 'NotoSans' if 'NotoSans' in pdfmetrics.getRegisteredFontNames() else 'Helvetica'
                if style_name == 'Title':
                    self.styles[style_name].fontSize = 24
                    self.styles[style_name].leading = 28
                elif style_name == 'Heading1':
                    self.styles[style_name].fontSize = 16
                    self.styles[style_name].leading = 20
                elif style_name == 'Heading2':
                    self.styles[style_name].fontSize = 14
                    self.styles[style_name].leading = 18
                elif style_name == 'Heading3':
                    self.styles[style_name].fontSize = 12
                    self.styles[style_name].leading = 16


    def _create_title_page(self):
        """タイトルページの作成"""
        elements = []
        styles = self.styles

        # タイトル
        elements.append(Paragraph("意識調査 分析レポート", styles['Title']))
        elements.append(Spacer(1, 2*cm))

        # 日付
        date = datetime.now().strftime("%Y年%m月%d日")
        elements.append(Paragraph(f"作成日：{date}", styles['Normal']))
        elements.append(PageBreak())

        return elements

    def _create_toc(self):
        """目次の作成"""
        elements = []
        styles = self.styles

        elements.append(Paragraph("目次", styles['Heading1']))
        elements.append(Spacer(1, 1*cm))
        elements.append(Paragraph("1. 実施概要", styles['JapaneseParagraph']))
        elements.append(Paragraph("2. 数値分析結果", styles['JapaneseParagraph']))
        elements.append(Paragraph("3. 相関分析", styles['JapaneseParagraph']))
        elements.append(Paragraph("4. 重要度満足度分析", styles['JapaneseParagraph']))
        elements.append(PageBreak())

        return elements

    def _create_heatmap(self, corr_data, column_names):
        """相関係数ヒートマップの作成"""
        display_cols = [column_names.get(col, col) for col in corr_data.columns]
        
        fig = go.Figure(data=go.Heatmap(
            z=corr_data,
            x=display_cols,
            y=display_cols,
            colorscale='RdBu',
            text=[[f'{val:.2f}' for val in row] for row in corr_data.values],
            texttemplate='%{text}',
            textfont={"size": 10},
            hoverongaps=False
        ))
        
        fig.update_layout(
            width=800,
            height=800,
            xaxis={'tickangle': 45},
            yaxis={'tickangle': 0}
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

    def _add_numeric_analysis_section(self, elements, dfs, config_manager, section_number, options):
        """数値分析のセクションを追加"""
        styles = self.styles
        column_names = config_manager.config.get('column_names', {})
        
        elements.append(Paragraph(f"{section_number}. 数値分析結果", styles['Heading1']))
        elements.append(Paragraph(
            "各設問項目の数値データについて、基本統計量を算出し分析を行いました。",
            styles['JapaneseParagraph']
        ))
        elements.append(Spacer(1, 0.5*cm))

        for i, df in enumerate(dfs):
            dataset_elements = []
            dataset_elements.append(Paragraph(f"データセット {i+1}", styles['Heading2']))
            
            # 基本統計量
            numeric_df = df.select_dtypes(include=['number'])
            if not numeric_df.empty:
                stats = numeric_df.describe()
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
                    ('FONTNAME', (0, 0), (-1, 0), 'NotoSans'),
                    ('FONTSIZE', (0, 0), (-1, 0), 10),
                    ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ]))
                dataset_elements.append(table)
                dataset_elements.append(Spacer(1, 0.5*cm))
            
            elements.append(KeepTogether(dataset_elements))

    def _add_correlation_analysis_section(self, elements, dfs, config_manager, section_number, options):
        """相関分析のセクションを追加"""
        styles = self.styles
        column_names = config_manager.config.get('column_names', {})
        
        elements.append(Paragraph(f"{section_number}. 相関分析", styles['Heading1']))
        elements.append(Paragraph(
            "各設問項目間の相関関係を分析しました。",
            styles['JapaneseParagraph']
        ))
        elements.append(Spacer(1, 0.5*cm))

        for i, df in enumerate(dfs):
            correlation_elements = []
            correlation_elements.append(Paragraph(f"データセット {i+1}", styles['Heading2']))
            
            numeric_columns = df.select_dtypes(include=['number']).columns
            if not numeric_columns.empty:
                corr_data = df[numeric_columns].corr()
                
                # ヒートマップの生成
                fig = self._create_heatmap(corr_data, column_names)
                temp_path = f"temp_heatmap_{i}.png"
                pio.write_image(fig, temp_path)
                correlation_elements.append(Image(temp_path, width=6*inch, height=6*inch))
                os.remove(temp_path)
                
                # 相関係数の表
                display_cols = [column_names.get(col, col) for col in corr_data.columns]
                correlation_elements.append(Paragraph("相関係数", styles['Heading3']))
                table_data = [[""] + display_cols]
                for idx, display_idx in zip(corr_data.index, display_cols):
                    row = [display_idx] + [f"{x:.2f}" for x in corr_data.loc[idx]]
                    table_data.append(row)
                
                table = Table(table_data)
                table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                    ('FONTNAME', (0, 0), (-1, 0), 'NotoSans'),
                    ('FONTSIZE', (0, 0), (-1, 0), 10),
                    ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ]))
                correlation_elements.append(table)
                correlation_elements.append(Spacer(1, 0.5*cm))
            
            elements.append(KeepTogether(correlation_elements))

    def _add_importance_satisfaction_section(self, elements, dfs, config_manager, section_number):
        """重要度-満足度分析のセクションを追加"""
        styles = self.styles
        
        elements.append(Paragraph(f"{section_number}. 重要度-満足度分析", styles['Heading1']))
        elements.append(Paragraph(
            "各項目の重要度と満足度の関係を分析しました。",
            styles['JapaneseParagraph']
        ))
        elements.append(Spacer(1, 0.5*cm))

        for i, df in enumerate(dfs):
            is_elements = []
            is_elements.append(Paragraph(f"データセット {i+1}", styles['Heading2']))
            
            # 重要度-満足度の散布図を生成
            fig = go.Figure()
            pairs = config_manager.config.get('importance_satisfaction_pairs', {})
            
            for pair_name, pair_data in pairs.items():
                importance_col = pair_data['importance']
                satisfaction_col = pair_data['satisfaction']
                
                valid_data = df[[importance_col, satisfaction_col]].dropna()
                if not valid_data.empty:
                    importance_mean = valid_data[importance_col].mean()
                    satisfaction_mean = valid_data[satisfaction_col].mean()
                    
                    fig.add_trace(
                        go.Scatter(
                            x=[importance_mean],
                            y=[satisfaction_mean],
                            mode='markers+text',
                            name=pair_name,
                            text=[pair_name],
                            textposition="top center",
                            marker=dict(size=12),
                            hovertemplate=f"{pair_name}<br>重要度: %{{x:.1f}}<br>満足度: %{{y:.1f}}<extra></extra>"
                        )
                    )
            
            # 軸の設定
            fig.update_layout(
                xaxis=dict(title='重要度', range=[2.0, 3.2]),
                yaxis=dict(title='満足度', range=[2.0, 3.6]),
                width=800,
                height=600,
                showlegend=True
            )
            
            # 一時ファイルとして保存
            temp_path = f"temp_scatter_{i}.png"
            pio.write_image(fig, temp_path)
            is_elements.append(Image(temp_path, width=6*inch, height=6*inch))
            os.remove(temp_path)
            
            elements.append(KeepTogether(is_elements))

    def generate_pdf(self, dfs, config_manager, visualizer, settings_name="デフォルト設定"):
        """PDFレポートを生成"""
        if not dfs:
            st.error("PDFを生成するにはデータが必要です。")
            return None

        # 設定の取得
        pdf_settings = config_manager.config.get('pdf_settings', {})
        if settings_name not in pdf_settings:
            st.error(f"PDF設定 '{settings_name}' が見つかりません。")
            return None

        settings = pdf_settings[settings_name]
        output_path = "survey_analysis_report.pdf"

        # ドキュメントの基本設定
        doc = SimpleDocTemplate(
            output_path,
            pagesize=A4,
            rightMargin=2.5*cm,
            leftMargin=2.5*cm,
            topMargin=2.5*cm,
            bottomMargin=2.5*cm
        )

        # 要素の準備
        elements = []
        
        # タイトルページと目次の追加
        elements.extend(self._create_title_page())
        elements.extend(self._create_toc())
        
        # 実施概要（常に含める）
        overview_elements = []
        overview_elements.append(Paragraph("1. 実施概要", self.styles['Heading1']))
        overview_elements.append(Paragraph(
            "本レポートは、意識調査の分析結果をまとめたものです。",
            self.styles['JapaneseParagraph']
        ))
        overview_elements.append(Spacer(1, 0.5*cm))
        
        for i, df in enumerate(dfs):
            overview_elements.append(Paragraph(
                f"第{i+1}回調査: {len(df)}件の回答",
                self.styles['JapaneseParagraph']
            ))
        overview_elements.append(Spacer(1, 1*cm))
        elements.append(KeepTogether(overview_elements))

        # 設定に基づいてセクションを生成
        section_number = 2
        for section in settings['sections']:
            if section['type'] == '数値表':
                self._add_numeric_analysis_section(
                    elements, dfs, config_manager, 
                    section_number, section['options']
                )
            elif section['type'] == '相関分析':
                self._add_correlation_analysis_section(
                    elements, dfs, config_manager,
                    section_number, section['options']
                )
            elif section['type'] == '重要度満足度':
                self._add_importance_satisfaction_section(
                    elements, dfs, config_manager,
                    section_number
                )
            section_number += 1

        # PDFの生成
        doc.build(elements)
        return output_path