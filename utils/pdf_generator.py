from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
import pandas as pd
import plotly.io as pio
import os

class PDFGenerator:
    def generate_pdf(self, dfs, config_manager, visualizer):
        output_path = "survey_analysis_report.pdf"
        doc = SimpleDocTemplate(output_path, pagesize=letter)
        styles = getSampleStyleSheet()
        elements = []

        # Title
        elements.append(Paragraph("意識調査データ分析レポート", styles['Title']))
        elements.append(Spacer(1, 20))

        # Add numerical tables
        elements.append(Paragraph("数値分析結果", styles['Heading1']))
        
        for i, df in enumerate(dfs):
            elements.append(Paragraph(f"データセット {i+1}", styles['Heading2']))
            
            # Basic statistics
            stats = df.describe()
            table_data = [["統計量"] + list(stats.columns)]
            for idx in stats.index:
                row = [idx] + [f"{x:.2f}" if isinstance(x, float) else str(x) for x in stats.loc[idx]]
                table_data.append(row)
            
            table = Table(table_data)
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 14),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ]))
            elements.append(table)
            elements.append(Spacer(1, 20))

        # Add visualizations
        elements.append(Paragraph("可視化", styles['Heading1']))
        
        # Save plots as temporary images and add to PDF
        for i, df in enumerate(dfs):
            elements.append(Paragraph(f"データセット {i+1} の可視化", styles['Heading2']))
            
            # Generate and save heatmap
            numeric_columns = df.select_dtypes(include=['number']).columns
            corr_data = df[numeric_columns].corr()
            fig = visualizer._create_heatmap(corr_data)
            temp_path = f"temp_heatmap_{i}.png"
            pio.write_image(fig, temp_path)
            elements.append(Paragraph("相関ヒートマップ", styles['Heading3']))
            elements.append(Image(temp_path))
            os.remove(temp_path)
            
            elements.append(Spacer(1, 20))

        # Generate PDF
        doc.build(elements)
        return output_path
