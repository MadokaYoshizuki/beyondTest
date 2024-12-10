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
import matplotlib.pyplot as plt
import seaborn as sns
import os
import streamlit as st
from datetime import datetime

class PDFGenerator:
    def __init__(self):
        # 日本語フォントの設定
        self.font_name = 'Helvetica'
        try:
            # システムフォントパスを探索
            font_paths = [
                '/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc',
                '/usr/share/fonts/noto-cjk/NotoSansCJK-Regular.ttc',
                'NotoSansCJKjp-Regular.ttf'
            ]
            
            for font_path in font_paths:
                if os.path.exists(font_path):
                    pdfmetrics.registerFont(TTFont('NotoSans', font_path))
                    self.font_name = 'NotoSans'
                    break
            
            if self.font_name == 'Helvetica':
                st.warning("日本語フォントが見つかりません。代替フォントを使用します。")
        except Exception as e:
            st.warning(f"フォント設定中にエラーが発生しました: {str(e)}")

        # スタイルの設定
        self.styles = getSampleStyleSheet()
        
        # カスタムスタイルの追加
        self.styles.add(ParagraphStyle(
            name='JapaneseParagraph',
            fontName=self.font_name,
            fontSize=10,
            leading=14
        ))
        
        # 既存のヘッディングスタイルを上書き
        for style_name in ['Title', 'Heading1', 'Heading2', 'Heading3']:
            if style_name in self.styles:
                self.styles[style_name].fontName = self.font_name
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
        import matplotlib.pyplot as plt
        import seaborn as sns
        from io import BytesIO
        
        # プロットサイズの設定
        plt.figure(figsize=(10, 8))
        
        # ヒートマップの作成
        display_cols = [column_names.get(col, col) for col in corr_data.columns]
        sns.heatmap(corr_data, 
                   xticklabels=display_cols,
                   yticklabels=display_cols,
                   annot=True,
                   fmt='.2f',
                   cmap='RdBu_r',
                   center=0,
                   cbar_kws={'label': '相関係数'})
        
        # 軸ラベルの回転
        plt.xticks(rotation=45, ha='right')
        plt.yticks(rotation=0)
        plt.tight_layout()
        
        # プロットをバイトストリームとして保存
        img_stream = BytesIO()
        plt.savefig(img_stream, format='png', dpi=300, bbox_inches='tight')
        img_stream.seek(0)
        plt.close()
        
        return img_stream

    def _create_scatter_plot(self, data_points, title="重要度-満足度分析"):
        """散布図の作成"""
        from io import BytesIO
        plt.figure(figsize=(10, 8))
        
        # 散布図のプロット
        plt.scatter(data_points['importance'], data_points['satisfaction'])
        
        # ラベルの追加
        for idx, point in data_points.iterrows():
            plt.annotate(point['name'], 
                        (point['importance'], point['satisfaction']),
                        xytext=(5, 5), textcoords='offset points')
        
        # 軸の設定
        plt.xlim(2.0, 3.2)
        plt.ylim(2.0, 3.6)
        plt.xlabel('重要度')
        plt.ylabel('満足度')
        plt.title(title)
        plt.grid(True, linestyle='--', alpha=0.7)
        plt.tight_layout()
        
        # プロットをバイトストリームとして保存
        img_stream = BytesIO()
        plt.savefig(img_stream, format='png', dpi=300, bbox_inches='tight')
        img_stream.seek(0)
        plt.close()
        
        return img_stream

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
                    ('FONTNAME', (0, 0), (-1, -1), self.font_name),
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
                img_stream = self._create_heatmap(corr_data, column_names)
                try:
                    correlation_elements.append(Image(img_stream, width=6*inch, height=6*inch))
                except Exception as e:
                    st.error(f"画像の追加中にエラーが発生しました: {str(e)}")
                
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
                    ('FONTNAME', (0, 0), (-1, -1), self.font_name),
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
            
            # データポイントの準備
            pairs = config_manager.config.get('importance_satisfaction_pairs', {})
            data_points = []
            
            for pair_name, pair_data in pairs.items():
                importance_col = pair_data['importance']
                satisfaction_col = pair_data['satisfaction']
                
                valid_data = df[[importance_col, satisfaction_col]].dropna()
                if not valid_data.empty:
                    data_points.append({
                        'name': pair_name,
                        'importance': valid_data[importance_col].mean(),
                        'satisfaction': valid_data[satisfaction_col].mean()
                    })
            
            if data_points:
                # データポイントをDataFrameに変換
                plot_data = pd.DataFrame(data_points)
                
                # 散布図の生成
                img_stream = self._create_scatter_plot(plot_data)
                try:
                    is_elements.append(Image(img_stream, width=6*inch, height=6*inch))
                except Exception as e:
                    st.error(f"画像の追加中にエラーが発生しました: {str(e)}")
            
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
