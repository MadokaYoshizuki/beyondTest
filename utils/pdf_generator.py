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
import matplotlib
matplotlib.use('Agg')  # バックエンドをAggに設定

class PDFGenerator:
    def __init__(self, config_manager=None):
        # デフォルトフォントの設定
        self.font_name = 'Helvetica'
        
        if config_manager is None:
            st.warning("設定マネージャーが提供されていません")
            return
        
        try:
            # フォントディレクトリの確認
            if not os.path.exists('fonts'):
                os.makedirs('fonts')
            
            # configからフォント設定を読み込む
            font_config = config_manager.config.get('pdf_font', {})
            if font_config and os.path.exists(font_config.get('path', '')):
                try:
                    font_path = font_config['path']
                    font_name = os.path.splitext(font_config['filename'])[0]
                    
                    # フォントの登録
                    pdfmetrics.registerFont(TTFont(font_name, font_path))
                    self.font_name = font_name
                    
                    # Matplotlibのグローバル設定
                    matplotlib.rcParams['font.family'] = self.font_name
                    matplotlib.rcParams['font.sans-serif'] = [self.font_name, 'sans-serif']
                    matplotlib.rcParams['axes.unicode_minus'] = False
                    matplotlib.rcParams['font.size'] = 12
                    
                    st.info(f"フォント '{font_config['filename']}' を使用します")
                except Exception as e:
                    st.error(f"フォントの読み込み中にエラーが発生しました: {str(e)}")
                    self.font_name = 'Helvetica'
            else:
                st.info("デフォルトフォントを使用します")
        except Exception as e:
            st.error(f"フォント設定中にエラーが発生しました: {str(e)}")

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

    def _create_title_page(self, title, description):
        """タイトルページの作成"""
        elements = []
        styles = self.styles

        # タイトル
        elements.append(Paragraph(title, styles['Title']))
        elements.append(Spacer(1, 1*cm))

        # 説明文
        if description:
            elements.append(Paragraph(description, styles['JapaneseParagraph']))
            elements.append(Spacer(1, 1*cm))

        # 日付
        date = datetime.now().strftime("%Y年%m月%d日")
        elements.append(Paragraph(f"作成日：{date}", styles['JapaneseParagraph']))
        elements.append(PageBreak())

        return elements

    def _create_sections(self, sections, dfs, config_manager):
        """セクションの作成"""
        elements = []
        
        for i, section in enumerate(sections, 1):
            if section['type'] == '相関係数':
                self._add_correlation_analysis_section(elements, dfs, config_manager, i, section)
            elif section['type'] == '回答分布':
                self._add_numeric_analysis_section(elements, dfs, config_manager, i, section)
            elif section['type'] == '重要度満足度':
                self._add_importance_satisfaction_section(elements, dfs, config_manager, i, section)
            
            elements.append(PageBreak())
        
        return elements

    def _create_heatmap(self, corr_data, column_names):
        """相関係数ヒートマップの作成"""
        try:
            # 既存のプロットをクリア
            plt.clf()
            
            # プロットサイズと解像度の設定
            plt.figure(figsize=(12, 10), dpi=300)
            
            # ヒートマップの作成
            display_cols = [column_names.get(col, col) for col in corr_data.columns]
            ax = sns.heatmap(corr_data, 
                       xticklabels=display_cols,
                       yticklabels=display_cols,
                       annot=True,
                       fmt='.2f',
                       cmap='RdBu_r',
                       center=0,
                       cbar_kws={'label': '相関係数'})
            
            # 軸ラベルの回転と配置の調整
            plt.xticks(rotation=45, ha='right')
            plt.yticks(rotation=0)
            
            # タイトルとラベルのフォントサイズ調整
            ax.set_xticklabels(ax.get_xticklabels(), fontsize=8)
            ax.set_yticklabels(ax.get_yticklabels(), fontsize=8)
            
            # レイアウトの調整
            plt.tight_layout(pad=1.5)
            
            # プロットをバイトストリームとして保存（高解像度）
            from io import BytesIO
            img_stream = BytesIO()
            plt.savefig(img_stream, format='png', dpi=300, bbox_inches='tight', 
                       pad_inches=0.5, facecolor='white', edgecolor='none')
            img_stream.seek(0)
            plt.close()
            
            return img_stream
        except Exception as e:
            st.error(f"ヒートマップの生成中にエラーが発生しました: {str(e)}")
            return None

    def _create_scatter_plot(self, data_points, title="重要度-満足度分析"):
        """散布図の作成"""
        try:
            from io import BytesIO
            
            # プロットサイズと解像度の設定
            plt.figure(figsize=(12, 10), dpi=300)
            
            # 散布図のプロット
            plt.scatter(data_points['importance'], data_points['satisfaction'], s=100)
            
            # ラベルの追加
            for idx, point in data_points.iterrows():
                plt.annotate(point['name'], 
                            (point['importance'], point['satisfaction']),
                            xytext=(5, 5), 
                            textcoords='offset points',
                            fontsize=10)
            
            # 軸の設定
            plt.xlim(2.0, 3.2)
            plt.ylim(2.0, 3.6)
            plt.xlabel('重要度', fontsize=12)
            plt.ylabel('満足度', fontsize=12)
            plt.title(title, fontsize=14, pad=20)
            plt.grid(True, linestyle='--', alpha=0.7)
            
            # レイアウトの調整
            plt.tight_layout(pad=1.5)
            
            # プロットをバイトストリームとして保存
            img_stream = BytesIO()
            plt.savefig(img_stream, format='png', dpi=300, bbox_inches='tight',
                       pad_inches=0.5, facecolor='white', edgecolor='none')
            img_stream.seek(0)
            plt.close()
            
            return img_stream
        except Exception as e:
            st.error(f"散布図の生成中にエラーが発生しました: {str(e)}")
            return None

    def _add_numeric_analysis_section(self, elements, dfs, config_manager, section_number, section):
        """数値分析のセクションを追加"""
        try:
            styles = self.styles
            column_names = config_manager.config.get('column_names', {})
            
            elements.append(Paragraph(f"{section_number}. {section['title']}", styles['Heading1']))
            if section.get('description'):
                elements.append(Paragraph(section['description'], styles['JapaneseParagraph']))
            elements.append(Spacer(1, 0.5*cm))

            for i, df in enumerate(dfs):
                section_elements = []
                section_elements.append(Paragraph(f"データセット {i+1}", styles['Heading2']))
                
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
                    section_elements.append(table)
                    section_elements.append(Spacer(1, 0.5*cm))
                
                elements.append(KeepTogether(section_elements))
        except Exception as e:
            st.error(f"数値分析セクションの生成中にエラーが発生しました: {str(e)}")

    def _add_correlation_analysis_section(self, elements, dfs, config_manager, section_number, section):
        """相関分析のセクションを追加"""
        try:
            styles = self.styles
            column_names = config_manager.config.get('column_names', {})
            
            elements.append(Paragraph(f"{section_number}. {section['title']}", styles['Heading1']))
            if section.get('description'):
                elements.append(Paragraph(section['description'], styles['JapaneseParagraph']))
            elements.append(Spacer(1, 0.5*cm))

            for i, df in enumerate(dfs):
                correlation_elements = []
                correlation_elements.append(Paragraph(f"データセット {i+1}", styles['Heading2']))
                
                numeric_columns = df.select_dtypes(include=['number']).columns
                if not numeric_columns.empty:
                    corr_data = df[numeric_columns].corr()
                    
                    # ヒートマップの生成
                    img_stream = self._create_heatmap(corr_data, column_names)
                    if img_stream:
                        correlation_elements.append(Image(img_stream, width=6*inch, height=6*inch))
                    
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
        except Exception as e:
            st.error(f"相関分析セクションの生成中にエラーが発生しました: {str(e)}")

    def _add_importance_satisfaction_section(self, elements, dfs, config_manager, section_number, section):
        """重要度-満足度分析のセクションを追加"""
        try:
            styles = self.styles
            
            elements.append(Paragraph(f"{section_number}. {section['title']}", styles['Heading1']))
            if section.get('description'):
                elements.append(Paragraph(section['description'], styles['JapaneseParagraph']))
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
                    if img_stream:
                        is_elements.append(Image(img_stream, width=6*inch, height=6*inch))
                
                elements.append(KeepTogether(is_elements))
        except Exception as e:
            st.error(f"重要度-満足度分析セクションの生成中にエラーが発生しました: {str(e)}")

    def generate_pdf(self, dfs, config_manager, visualizer, template_name):
        """PDFレポートを生成"""
        try:
            if not dfs:
                st.error("PDFを生成するにはデータが必要です。")
                return None

            # テンプレート設定の取得
            templates = config_manager.config.get('pdf_settings', {}).get('templates', {})
            if template_name not in templates:
                st.error(f"テンプレート '{template_name}' が見つかりません。")
                return None

            template = templates[template_name]
            if not template.get('sections'):
                st.error("テンプレートにセクションが設定されていません。")
                return None

            output_path = f"reports/{template_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
            
            # 出力ディレクトリの作成
            os.makedirs('reports', exist_ok=True)

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
            
            # タイトルページの追加
            elements.extend(self._create_title_page(template['title'], template.get('description', '')))

            # セクションの生成
            for i, section in enumerate(template['sections'], 1):
                try:
                    if section['type'] == '回答分布':
                        self._add_numeric_analysis_section(elements, dfs, config_manager, i, section)
                    elif section['type'] == '相関係数':
                        self._add_correlation_analysis_section(elements, dfs, config_manager, i, section)
                    elif section['type'] == '重要度満足度':
                        self._add_importance_satisfaction_section(elements, dfs, config_manager, i, section)
                    st.success(f"セクション {section['title']} を生成しました")
                except Exception as e:
                    st.error(f"セクション {section['title']} の生成中にエラーが発生: {str(e)}")
                    import traceback
                    st.error(traceback.format_exc())

            # PDFの生成
            doc.build(elements)
            return output_path

        except Exception as e:
            st.error(f"PDF生成中にエラーが発生しました: {str(e)}")
            import traceback
            st.error(f"エラーの詳細:\n{traceback.format_exc()}")
            return None
