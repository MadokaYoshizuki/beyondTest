import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import plotly.io as pio
import matplotlib.pyplot as plt
import seaborn as sns
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.utils import ImageReader
import io
class Visualizer:

    def _save_to_excel(self, data_dict, filename):
        excel_path = f"{filename}.xlsx"

        with pd.ExcelWriter(excel_path, engine='openpyxl', mode='w') as writer:
            if isinstance(data_dict, dict):
                for sheet_name, df in data_dict.items():
                    if isinstance(df, pd.DataFrame):
                        # データフレームの場合は直接書き込み
                        df.to_excel(writer,
                                  sheet_name=sheet_name,
                                  index=True,
                                  header=True,
                                  engine='openpyxl')
                    elif isinstance(df, dict):
                        # 辞書の場合はデータフレームに変換して書き込み
                        pd.DataFrame(df).to_excel(writer,
                                               sheet_name=sheet_name,
                                               index=True,
                                               header=True,
                                               engine='openpyxl')
                    else:
                        # その他の形式の場合は文字列に変換してデータフレームとして書き込み
                        pd.DataFrame({'値': [str(df)]}).to_excel(writer,
                                                              sheet_name=sheet_name,
                                                              index=False,
                                                              header=True,
                                                              engine='openpyxl')
            else:
                data_dict.to_excel(writer,
                                 index=True,
                                 header=True,
                                 engine='openpyxl')

        with open(excel_path, 'rb') as f:
            st.download_button(
                label="Excelファイルをダウンロード",
                data=f,
                file_name=excel_path,
                mime=
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

        import os
        os.remove(excel_path)

    def _display_value_distribution(self, df, column_names):
        # 単一回答の数値列のみを抽出
        numeric_columns = []
        for col in df.select_dtypes(include=['number']).columns:
            values = df[col].fillna('').astype(str)
            if not values.str.contains(',').any():  # カンマを含まない = 単一回答
                numeric_columns.append(col)

        if not numeric_columns:
            st.info("単一回答の数値データが見つかりませんでした。")
            return

        # Y軸のポジション設定（質問番号はデータの列名から抽出）
        y_positions = list(range(len(numeric_columns)))
        y_labels = [column_names.get(col, col)
                    for col in numeric_columns]  # 列名をそのまま使用

        # データを格納するリスト
        fig_data = []

        # 色のパレット（回答値ごとに異なる色を割り当て）
        colors = {
            1: 'rgb(255, 65, 54)',  # 赤
            2: 'rgb(255, 144, 14)',  # オレンジ
            3: 'rgb(190, 190, 190)',  # グレー
            4: 'rgb(93, 164, 214)',  # 青
            5: 'rgb(44, 160, 44)'  # 緑
        }

        # 各質問の回答分布を計算
        for i, col in enumerate(numeric_columns):
            value_counts = df[col].value_counts().sort_index()
            total_count = len(df)

            # 各回答値の割合を計算し、個別のバーとして追加
            for value in value_counts.index:
                count = value_counts[value]
                percentage = (count / total_count) * 100

                fig_data.append(
                    go.Bar(
                        name=str(value),  # 凡例に表示する回答値
                        x=[percentage],
                        y=[i],
                        orientation='h',
                        text=f"{percentage:.1f}%",
                        textposition='inside',
                        marker_color=colors.get(
                            value, 'rgb(128, 128, 128)'),  # 定義されていない値はグレーを使用
                        customdata=[[value, count]],
                        hovertemplate=
                        "回答値: %{customdata[0]}<br>回答数: %{customdata[1]}<br>割合: %{x:.1f}%<extra></extra>"
                    ))

        # グラフの作成
        fig = go.Figure(data=fig_data)

        # 凡例の重複を排除（nameでグループ化）
        legend_names = []
        for trace in fig.data:
            if trace.name not in legend_names:
                legend_names.append(trace.name)
                trace.showlegend = True
            else:
                trace.showlegend = False

        # レイアウトの設定
        fig.update_layout(
            title=dict(text="全質問の回答分布（単一回答のみ）", x=0.5, xanchor='center'),
            barmode='stack',
            showlegend=True,
            xaxis=dict(
                title="回答の割合 (%)",
                range=[0, 100],  # X軸の範囲を0-100%に固定
                showgrid=True,
                gridcolor='rgba(0,0,0,0.1)',
                zeroline=True,
                zerolinecolor='rgba(0,0,0,0.2)'),
            yaxis=dict(title="質問項目",
                       ticktext=y_labels,
                       tickvals=y_positions,
                       automargin=True,
                       side='left'),
            height=max(400,
                       len(numeric_columns) * 40),  # 質問数に応じて高さを調整
            margin=dict(l=300, r=50, t=50, b=50),  # マージンの調整
            legend=dict(title="回答値",
                        traceorder='normal',
                        yanchor="top",
                        y=1,
                        xanchor="left",
                        x=1.02,
                        font=dict(size=10)),
            plot_bgcolor='white',
            paper_bgcolor='white',
            bargap=0.4,  # バー間のギャップを調整
            uniformtext=dict(mode="hide", minsize=8)  # テキストサイズの自動調整
        )

        # グラフのサイズとマージンを調整
        fig.update_layout(
            width=1000,  # グラフの幅を固定
            height=max(500,
                       len(numeric_columns) * 40)  # 質問数に応じて高さを調整
        )

        # グラフを表示
        st.plotly_chart(fig, use_container_width=False)  # コンテナ幅に合わせない

    def display_dashboard(self, dfs, config_manager):
        if not dfs:
            st.info("データを読み込んでください。")
            return

        # データセットと属性の選択
        year_options = [
            f"データセット{i+1}({st.session_state.data_processor.dates[i]})"
            for i in range(len(dfs))
        ]
        selected_year_idx = st.selectbox("データを選択:",
                                         range(len(dfs)),
                                         format_func=lambda x: year_options[x])

        df = dfs[selected_year_idx]
        column_names = config_manager.config.get('column_names', {})
        question_groups = config_manager.config.get('question_groups', {})

        # 数値回答の分析
        st.subheader("【数値回答】")

        # 1. 相関係数ヒートマップ
        col1, col2 = st.columns([3, 1])
        with col1:
            st.write("**1. 相関係数ヒートマップ**")
        with col2:
            if st.button("PDF出力", key="correlation_heatmap_pdf"):
                self._save_current_plots_to_pdf()
                st.success("グラフをPDFとして保存しました")
        self._display_correlation_heatmap(df, column_names, question_groups)

        # 2. 回答の件数と構成比の帯グラフ
        st.write("**2. 回答の分布**")
        self._display_value_distribution(df, column_names)

        # 3. 質問グループ間の散布図
        st.write("**3. 質問グループ間の散布図**")
        self._display_scatter_plot(df, column_names, question_groups)

        # 4. 重要度-満足度分析
        st.write("**4. 重要度-満足度分析**")
        self._display_importance_satisfaction_plot(df, column_names,
                                                   config_manager)

    def _display_correlation_heatmap(self,
                                     df,
                                     column_names,
                                     question_groups=None):
        numeric_columns = df.select_dtypes(include=['number']).columns
        if not numeric_columns.empty:
            # 表示モードの選択
            correlation_mode = st.radio("相関分析の表示モード:",
                                        ["質問間の相関", "質問グループ間の相関"],
                                        key="correlation_mode")

            if correlation_mode == "質問間の相関":
                # 質問グループの選択（質問間の相関モードの場合のみ表示）
                group_options = ["すべての質問"] + list(question_groups.keys())
                selected_group = st.selectbox("質問グループを選択:", group_options)

                # 選択されたグループの列を取得
                target_columns = question_groups.get(
                    selected_group,
                    df.columns) if selected_group != "すべての質問" else df.columns
                df_filtered = df[target_columns]
                numeric_columns = df_filtered.select_dtypes(
                    include=['number']).columns
                display_columns = [
                    column_names.get(col, col) for col in numeric_columns
                ]
                corr_data = df[numeric_columns].corr()

                fig = go.Figure(
                    data=go.Heatmap(z=corr_data,
                                    x=display_columns,
                                    y=display_columns,
                                    colorscale='RdBu',
                                    text=[[f'{val:.2f}' for val in row]
                                          for row in corr_data.values],
                                    texttemplate='%{text}',
                                    textfont={"size": 10},
                                    hoverongaps=False))

                title = "質問間の相関係数"

            else:  # 質問グループ間の相関
                if not question_groups:
                    st.info("質問グループが設定されていません。")
                    return

                # グループごとの平均値を計算
                group_means = {}
                for group_name, questions in question_groups.items():
                    numeric_questions = [
                        q for q in questions if q in numeric_columns
                    ]
                    if numeric_questions:
                        # 各質問の回答の平均値をグループの特徴ベクトルとして使用
                        group_means[group_name] = df[numeric_questions].mean()

                # グループ間の相関係数行列を作成
                group_names = list(group_means.keys())
                group_values = pd.DataFrame(group_means).fillna(0)  # 欠損値を0で埋める
                corr_data = group_values.corr()

                fig = go.Figure(
                    data=go.Heatmap(z=corr_data,
                                    x=group_names,
                                    y=group_names,
                                    colorscale='RdBu',
                                    text=[[f'{val:.2f}' for val in row]
                                          for row in corr_data.values],
                                    texttemplate='%{text}',
                                    textfont={"size": 12},
                                    hoverongaps=False))

                title = "質問グループ間の相関係数"

            fig.update_layout(title=title,
                              width=800,
                              height=800,
                              xaxis={'tickangle': 45},
                              yaxis={'tickangle': 0})

            # セッション状態にグラフを保存
            st.session_state.current_plot = fig
            st.plotly_chart(fig)
        else:
            st.info("数値データが見つかりませんでした。")

    def _display_importance_satisfaction_plot(self, df, column_names,
                                              config_manager):
        """重要度-満足度分析の散布図を表示"""
        importance_satisfaction_pairs = config_manager.config.get(
            'importance_satisfaction_pairs', {})

        if not importance_satisfaction_pairs:
            st.info("重要度-満足度の対応関係が設定されていません。")
            return

        # 散布図を作成
        fig = go.Figure()

        # 各ペアのデータをプロット
        for pair_name, pair_data in importance_satisfaction_pairs.items():
            importance_col = pair_data['importance']
            satisfaction_col = pair_data['satisfaction']

            # 数値データのみを抽出
            valid_data = df[[importance_col, satisfaction_col]].dropna()

            if not valid_data.empty:
                # 平均値を計算
                importance_mean = valid_data[importance_col].mean()
                satisfaction_mean = valid_data[satisfaction_col].mean()

                # データポイントの追加
                fig.add_trace(
                    go.Scatter(x=[importance_mean],
                               y=[satisfaction_mean],
                               mode='markers+text',
                               name=pair_name,
                               text=[pair_name],
                               textposition="top center",
                               marker=dict(size=12, symbol='circle'),
                               hovertemplate="<b>%{text}</b><br>" +
                               "重要度: %{x:.1f}<br>" + "満足度: %{y:.1f}<br>" +
                               "<extra></extra>"))

        # 重要度と満足度の平均値を計算
        importance_means = []
        satisfaction_means = []
        for pair_name, pair_data in importance_satisfaction_pairs.items():
            importance_col = pair_data['importance']
            satisfaction_col = pair_data['satisfaction']

            # 数値データのみを抽出
            valid_data = df[[importance_col, satisfaction_col]].dropna()

            if not valid_data.empty:
                importance_mean = valid_data[importance_col].mean()
                satisfaction_mean = valid_data[satisfaction_col].mean()
                importance_means.append(importance_mean)
                satisfaction_means.append(satisfaction_mean)

        # 全体の平均値を計算（小数点第1位で丸める）
        overall_importance_mean = round(
            sum(importance_means) / len(importance_means), 1)
        overall_satisfaction_mean = round(
            sum(satisfaction_means) / len(satisfaction_means), 1)

        print(f"Debug - 重要度の平均値: {overall_importance_mean}")
        print(f"Debug - 満足度の平均値: {overall_satisfaction_mean}")
        print(f"Debug - 重要度の値一覧: {importance_means}")
        print(f"Debug - 満足度の値一覧: {satisfaction_means}")

        # 軸の範囲を設定
        x_min, x_max = 2.0, 3.2  # 重要度の範囲
        y_min, y_max = 2.0, 3.6  # 満足度の範囲

        # 平均値の点線を追加
        # 満足度の平均値（横線）
        fig.add_shape(type="line",
                      x0=x_min,
                      x1=x_max,
                      y0=overall_satisfaction_mean,
                      y1=overall_satisfaction_mean,
                      xref="x",
                      yref="y",
                      line=dict(color="orange", width=1, dash="dot"))
        # 重要度の平均値（縦線）
        fig.add_shape(type="line",
                      x0=overall_importance_mean,
                      x1=overall_importance_mean,
                      y0=y_min,
                      y1=y_max,
                      xref="x",
                      yref="y",
                      line=dict(color="orange", width=1, dash="dot"))

        # 平均値のテキストを個別のアノテーションとして追加
        fig.add_annotation(text=f"満足度平均：{overall_satisfaction_mean:.1f}",
                           x=x_min,
                           y=overall_satisfaction_mean + 0.04,
                           xref="x",
                           yref="y",
                           showarrow=False,
                           xanchor="left",
                           yanchor="middle")
        fig.add_annotation(text=f"重要度平均：{overall_importance_mean:.1f}",
                           x=overall_importance_mean + 0.04,
                           y=y_min,
                           xref="x",
                           yref="y",
                           showarrow=False,
                           xanchor="left",
                           yanchor="bottom")

        # レイアウトの設定
        fig.update_layout(
            # title='重要度-満足度分析',
            xaxis=dict(title='重要度',
                       range=[x_min, x_max],
                       showgrid=True,
                       gridwidth=1,
                       gridcolor='rgba(128, 128, 128, 0.2)',
                       zeroline=False,
                       showline=True,
                       linewidth=1,
                       linecolor='rgba(128, 128, 128, 1)'),
            yaxis=dict(title='満足度',
                       range=[y_min, y_max],
                       showgrid=True,
                       gridwidth=1,
                       gridcolor='rgba(128, 128, 128, 0.2)',
                       zeroline=False,
                       showline=True,
                       linewidth=1,
                       linecolor='rgba(128, 128, 128, 1)'),
            width=800,
            height=600,
            showlegend=True,
            plot_bgcolor='white',
            # # プロットエリアの枠線を追加
            # shapes=[
            #     dict(type='rect',
            #          xref='paper',
            #          yref='paper',
            #          x0=0,
            #          y0=0,
            #          x1=1,
            #          y1=1,
            #          line=dict(color='rgba(128, 128, 128, 1)', width=1))
            # ]
        )

        # ラベルの位置を自動調整
        fig.update_traces(textposition='top center',
                          textfont=dict(size=12),
                          cliponaxis=False)

        st.plotly_chart(fig)

    def _display_scatter_plot(self, df, column_names, question_groups=None):
        if not question_groups:
            st.info("質問グループが設定されていません。散布図を表示するには質問グループの設定が必要です。")
            return

        # 各質問グループの平均値を計算
        group_means = {}
        for group_name, questions in question_groups.items():
            numeric_questions = [
                q for q in questions
                if q in df.columns and pd.api.types.is_numeric_dtype(df[q])
            ]
            if numeric_questions:
                # 各回答者ごとの質問グループの平均値を計算
                group_means[group_name] = df[numeric_questions].mean(axis=1)

        if len(group_means) >= 2:
            # 平均値をデータフレームに変換
            scatter_df = pd.DataFrame(group_means)

            col1, col2 = st.columns(2)
            with col1:
                x_axis = st.selectbox("X軸の質問グループ:",
                                      list(group_means.keys()),
                                      key="scatter_x_axis")
            with col2:
                y_axis = st.selectbox("Y軸の質問グループ:",
                                      list(group_means.keys()),
                                      key="scatter_y_axis")

            if x_axis and y_axis:
                fig = px.scatter(scatter_df,
                                 x=x_axis,
                                 y=y_axis,
                                 labels={
                                     x_axis: x_axis,
                                     y_axis: y_axis
                                 })

                # X軸とY軸の平均値を計算
                x_mean = scatter_df[x_axis].mean()
                y_mean = scatter_df[y_axis].mean()

                # 平均値の位置に点線を追加
                fig.add_hline(y=y_mean,
                              line_dash="dash",
                              line_color="orange",
                              line_width=1,
                              annotation_text=f"平均：{y_mean:.1f}")
                fig.add_vline(x=x_mean,
                              line_dash="dash",
                              line_color="orange",
                              line_width=1,
                              annotation_text=f"平均：{x_mean:.1f}")

                fig.update_layout(
                    # title=f"{x_axis}と{y_axis}の相関",
                    height=500,
                    xaxis=dict(
                        title=f"{x_axis}の平均値",
                        tickmode='linear',
                        dtick=1,  # 目盛りの間隔を1に設定
                        showgrid=True,
                        gridwidth=1,
                        gridcolor='rgba(128, 128, 128, 0.2)'),
                    yaxis=dict(
                        title=f"{y_axis}の平均値",
                        tickmode='linear',
                        dtick=1,  # 目盛りの間隔を1に設定
                        showgrid=True,
                        gridwidth=1,
                        gridcolor='rgba(128, 128, 128, 0.2)'))

                st.plotly_chart(fig)

    def _display_multiple_choice_analysis(self, df, attribute, column_names,
                                          display_mode):
        multiple_choice_cols = [
            col for col in df.columns
            if not pd.api.types.is_numeric_dtype(df[col])
            and df[col].fillna('').astype(str).str.contains(',').any()
        ]

        if not multiple_choice_cols:
            st.info("複数回答の質問が見つかりませんでした。")
            return

        for col in multiple_choice_cols:
            display_name = column_names.get(col, col)
            st.subheader(f"{display_name}")

            # 回答の分解と集計
            values = df[col].fillna('').astype(str).str.split(',').explode()
            counts = values.value_counts().sort_index()

            if display_mode == "まとめて表示":
                # 1つのチャートにまとめて表示
                if attribute != "全体":
                    fig = go.Figure()
                    for attr_value in df[attribute].unique():
                        subset = df[df[attribute] == attr_value]
                        subset_values = subset[col].fillna('').astype(
                            str).str.split(',').explode()
                        subset_counts = subset_values.value_counts(
                        ).sort_index()

                        fig.add_trace(
                            go.Bar(name=str(attr_value),
                                   x=subset_counts.index,
                                   y=subset_counts.values,
                                   text=subset_counts.values,
                                   textposition='auto'))

                    fig.update_layout(title=f"{display_name}の回答分布（属性別）",
                                      barmode='group',
                                      height=400)

                    st.plotly_chart(fig)
                else:
                    # 全体表示
                    fig = go.Figure([
                        go.Bar(x=counts.index,
                               y=counts.values,
                               text=counts.values,
                               textposition='auto')
                    ])

                    fig.update_layout(title=f"{display_name}の回答分布", height=400)

                    st.plotly_chart(fig)
            else:
                # 属性値ごとに個別のチャートを表示
                if attribute != "全体":
                    for attr_value in df[attribute].unique():
                        subset = df[df[attribute] == attr_value]
                        subset_values = subset[col].fillna('').astype(
                            str).str.split(',').explode()
                        subset_counts = subset_values.value_counts(
                        ).sort_index()

                        fig = go.Figure([
                            go.Bar(x=subset_counts.index,
                                   y=subset_counts.values,
                                   text=subset_counts.values,
                                   textposition='auto')
                        ])

                        fig.update_layout(
                            title=f"{display_name}の回答分布（{attr_value}）",
                            height=400)

                        st.plotly_chart(fig)
                else:
                    # 全体表示
                    fig = go.Figure([
                        go.Bar(x=counts.index,
                               y=counts.values,
                               text=counts.values,
                               textposition='auto')
                    ])

                    fig.update_layout(title=f"{display_name}の回答分布", height=400)

                    st.plotly_chart(fig)

    def display_numerical_tables(self, dfs, config_manager):
        if not dfs:
            st.info("データを読み込んでください。")
            return

        # データセットの選択
        year_options = [
            f"データセット{i+1}({st.session_state.data_processor.dates[i]})"
            for i in range(len(dfs))
        ]
        selected_year_idx = st.selectbox("データを選択:",
                                         range(len(dfs)),
                                         format_func=lambda x: year_options[x])

        # 属性の選択
        attributes = ["全体"] + config_manager.config.get('attributes', [])
        selected_attribute = st.selectbox("属性項目:", attributes)

        df = dfs[selected_year_idx]

        # 数値回答の分析を実行
        self._display_numeric_analysis(df, selected_attribute, config_manager)

    def _save_current_plots_to_pdf(self):
        """現在表示されているPlotlyグラフをPDFとして保存する"""
        # 一時的なバッファを作成
        buffer = io.BytesIO()

        # PDFを作成
        c = canvas.Canvas(buffer, pagesize=A4)

        # 現在のPlotlyグラフを画像として保存
        for fig in [st.session_state.get('current_plot', None)]:
            if fig:
                # グラフを画像として保存
                img_bytes = fig.to_image(format="png", width=800, height=600)
                img_buffer = io.BytesIO(img_bytes)

                # PDFに画像を配置
                c.drawImage(img_buffer, 50, 500, width=500, height=300)

        c.save()
        buffer.seek(0)

        # PDFをダウンロード
        st.download_button(
            label="グラフをPDFでダウンロード",
            data=buffer,
            file_name="visualization.pdf",
            mime="application/pdf"
        )
        
    def _display_numeric_analysis(self, df, attribute, config_manager):
        column_names = config_manager.config.get('column_names', {})
        question_groups = config_manager.config.get('question_groups', {})
        value_groups = config_manager.config.get('value_groups', {})
        max_scores = config_manager.config.get('max_scores', {})

        # 数値列の取得
        numeric_cols = df.select_dtypes(include=['number']).columns
        if len(numeric_cols) == 0:
            st.info("数値データが見つかりませんでした。")
            return

        # メインセクション：質問ごとの分析
        st.header("質問ごとの分析結果")
        results = {'平均': {}, '100点換算': {}}

        for col in numeric_cols:
            display_name = column_names.get(col, col)
            max_val = df[col].max()
            max_score = max_scores.get(col, max_val)

            results['平均'][display_name] = {}
            results['100点換算'][display_name] = {}

            # 全体の集計
            total_mean = df[col].mean()
            results['平均'][display_name]['全体'] = '{:g}'.format(
                total_mean) if pd.notnull(total_mean) else '-'

            if pd.notnull(total_mean) and max_score > 0:
                score = (total_mean / max_score) * 100
                results['100点換算'][display_name]['全体'] = '{:g}'.format(score)
            else:
                results['100点換算'][display_name]['全体'] = '-'

            # 属性値ごとの集計
            if attribute != "全体":
                for value in df[attribute].unique():
                    subset = df[df[attribute] == value]
                    mean_val = subset[col].mean()

                    results['平均'][display_name][value] = '{:g}'.format(
                        mean_val) if pd.notnull(mean_val) else '-'
                    if pd.notnull(mean_val) and max_score > 0:
                        score = (mean_val / max_score) * 100
                        results['100点換算'][display_name][value] = '{:g}'.format(
                            score)
                    else:
                        results['100点換算'][display_name][value] = '-'

        # 結果の表示
        results_mean = pd.DataFrame(results['平均']).T
        results_score = pd.DataFrame(results['100点換算']).T

        if attribute != "全体":
            column_order = ['全体'] + [
                col for col in results_mean.columns if col != '全体'
            ]
            results_mean = results_mean[column_order]
            results_score = results_score[column_order]

        st.write("平均値")
        results_mean_t = results_mean.T
        results_mean_t.index.name = '属性'
        st.dataframe(results_mean_t)

        st.write("100点換算")
        results_score_t = results_score.T
        results_score_t.index.name = '属性'
        st.dataframe(results_score_t)

        # 質問グループごとの分析
        if question_groups:
            st.header("質問グループごとの分析結果")
            group_results = {'平均': {}, '100点換算': {}}

            for group_name, questions in question_groups.items():
                numeric_questions = [
                    q for q in questions
                    if q in df.columns and pd.api.types.is_numeric_dtype(df[q])
                ]
                if numeric_questions:
                    group_results['平均'][group_name] = {}
                    group_results['100点換算'][group_name] = {}

                    # 全体の集計
                    group_mean = df[numeric_questions].mean().mean()
                    group_results['平均'][group_name]['全体'] = '{:g}'.format(
                        group_mean) if pd.notnull(group_mean) else '-'

                    # 100点換算の計算
                    scores = []
                    for q in numeric_questions:
                        mean_val = df[q].mean()
                        max_score = max_scores.get(q, df[q].max())
                        if pd.notnull(mean_val) and max_score > 0:
                            score = (mean_val / max_score) * 100
                            scores.append(score)

                    if scores:
                        avg_score = sum(scores) / len(scores)
                        group_results['100点換算'][group_name][
                            '全体'] = '{:g}'.format(avg_score)
                    else:
                        group_results['100点換算'][group_name]['全体'] = '-'

                    # 属性値ごとの集計
                    if attribute != "全体":
                        for value in df[attribute].unique():
                            subset = df[df[attribute] == value]
                            subset_mean = subset[numeric_questions].mean(
                            ).mean()

                            group_results['平均'][group_name][
                                value] = '{:g}'.format(
                                    subset_mean) if pd.notnull(
                                        subset_mean) else '-'

                            # 属性値ごとの100点換算
                            subset_scores = []
                            for q in numeric_questions:
                                mean_val = subset[q].mean()
                                max_score = max_scores.get(q, df[q].max())
                                if pd.notnull(mean_val) and max_score > 0:
                                    score = (mean_val / max_score) * 100
                                    subset_scores.append(score)

                            if subset_scores:
                                avg_score = sum(subset_scores) / len(
                                    subset_scores)
                                group_results['100点換算'][group_name][
                                    value] = '{:g}'.format(avg_score)
                            else:
                                group_results['100点換算'][group_name][
                                    value] = '-'

            group_mean_df = pd.DataFrame(group_results['平均']).T
            group_score_df = pd.DataFrame(group_results['100点換算']).T

            if attribute != "全体":
                column_order = ['全体'] + [
                    col for col in group_mean_df.columns if col != '全体'
                ]
                group_mean_df = group_mean_df[column_order]
                group_score_df = group_score_df[column_order]

            st.write("平均値")
            group_mean_df_t = group_mean_df.T
            group_mean_df_t.index.name = '属性'
            st.dataframe(group_mean_df_t)

            st.write("100点換算")
            group_score_df_t = group_score_df.T
            group_score_df_t.index.name = '属性'
            st.dataframe(group_score_df_t)

        if value_groups:
            st.header("値グループ分析結果")

            # 質問ごとの値グループ分析
            st.subheader("質問ごとの値グループ分析")

            # 数値回答の質問を取得
            numeric_cols = df.select_dtypes(include=['number']).columns

            for col in numeric_cols:
                display_name = column_names.get(col, col)

                st.write(f"● {display_name}")
                if col in value_groups:
                    value_group_results = {}
                    total_count = len(df)

                    # 全体の集計
                    for range_str, label in value_groups[col].items():
                        min_val, max_val = map(float, range_str.split('-'))
                        mask = (df[col] >= min_val) & (df[col] <= max_val)
                        count = mask.sum()

                        if label not in value_group_results:
                            value_group_results[label] = {}

                        value_group_results[label]['全体'] = {
                            '件数':
                            count,
                            '割合':
                            '{:.1f}'.format((count / total_count) *
                                            100) if total_count > 0 else '-'
                        }

                        # 属性値ごとの集計
                        if attribute != "全体":
                            for attr_value in df[attribute].unique():
                                subset = df[df[attribute] == attr_value]
                                subset_mask = (subset[col] >= min_val) & (
                                    subset[col] <= max_val)
                                subset_count = subset_mask.sum()
                                value_group_results[label][attr_value] = {
                                    '件数':
                                    subset_count,
                                    '割合':
                                    '{:.1f}'.format(
                                        (subset_count / len(subset)) *
                                        100) if len(subset) > 0 else '-'
                                }

                    # 結果の表示
                    col1, col2 = st.columns(2)
                    for metric in ['件数', '割合']:
                        columns = ['全体'] + (list(df[attribute].unique())
                                            if attribute != "全体" else [])
                        result_df = pd.DataFrame({
                            label: {
                                col: data.get(col, {}).get(metric, '-')
                                for col in columns
                            }
                            for label, data in value_group_results.items()
                        }).T

                        if metric == '件数':
                            with col1:
                                st.write(f"{metric}")
                                result_df_t = result_df.T
                                result_df_t.index.name = '属性'
                                st.dataframe(result_df_t)
                        else:
                            with col2:
                                st.write(f"{metric}")
                                result_df_t = result_df.T
                                result_df_t.index.name = '属性'
                                st.dataframe(result_df_t)
                else:
                    st.info("この質問には値グループが設定されていません。")

            # 質問グループごとの値グループ分析
            if question_groups:
                st.write("質問グループごとの値グループ分析")

                for group_name, questions in question_groups.items():
                    # グループ内の数値列かつ値グループが設定されている列のみを処理
                    numeric_questions = [
                        q for q in questions if q in df.columns
                        and pd.api.types.is_numeric_dtype(df[q])
                    ]

                    valid_questions = [
                        q for q in numeric_questions if q in value_groups
                    ]

                    st.write(f"● {group_name}")
                    if not numeric_questions:
                        st.info("このグループには数値回答の質問が含まれていません。")
                    elif not valid_questions:
                        st.info("このグループの質問には値グループが設定されていません。")
                    else:
                        # 各値グループのラベルを収集
                        all_labels = set()
                        for col in valid_questions:
                            all_labels.update(value_groups[col].values())

                        # グループ全体の結果を集計
                        group_results = {}
                        total_count = len(df) * len(valid_questions)  # 全回答数

                        for label in all_labels:
                            label_count = 0

                            for col in valid_questions:
                                for range_str, range_label in value_groups[
                                        col].items():
                                    if range_label == label:
                                        min_val, max_val = map(
                                            float, range_str.split('-'))
                                        mask = (df[col] >= min_val) & (
                                            df[col] <= max_val)
                                        label_count += mask.sum()

                            # 有効な回答数で計算
                            valid_responses = sum(
                                1
                                for _ in df.iterrows()) * len(valid_questions)
                            group_results[label] = {}
                            group_results[label]['全体'] = {
                                '件数':
                                label_count,
                                '割合':
                                '{:.1f}'.format(
                                    (label_count / valid_responses) *
                                    100) if valid_responses > 0 else '-'
                            }

                            # 属性値ごとの集計
                            if attribute != "全体":
                                for attr_value in df[attribute].unique():
                                    subset = df[df[attribute] == attr_value]
                                    attr_label_count = 0

                                    for col in valid_questions:
                                        for range_str, range_label in value_groups[
                                                col].items():
                                            if range_label == label:
                                                min_val, max_val = map(
                                                    float,
                                                    range_str.split('-'))
                                                mask = (subset[col] >= min_val
                                                        ) & (subset[col]
                                                             <= max_val)
                                                attr_label_count += mask.sum()

                                    # 属性ごとの有効な回答数で計算
                                    attr_valid_responses = len(subset) * len(
                                        valid_questions)
                                    group_results[label][attr_value] = {
                                        '件数':
                                        attr_label_count,
                                        '割合':
                                        '{:.1f}'.format(
                                            (attr_label_count /
                                             attr_valid_responses) * 100)
                                        if attr_valid_responses > 0 else '-'
                                    }

                        # 結果の表示
                        col1, col2 = st.columns(2)
                        for metric in ['件数', '割合']:
                            columns = ['全体'] + (list(df[attribute].unique())
                                                if attribute != "全体" else [])
                            result_df = pd.DataFrame({
                                label: {
                                    col: data.get(col, {}).get(metric, '-')
                                    for col in columns
                                }
                                for label, data in group_results.items()
                            }).T

                            if metric == '件数':
                                with col1:
                                    st.write(f"{metric}")
                                    result_df_t = result_df.T
                                    result_df_t.index.name = '属性'
                                    st.dataframe(result_df_t)
                            else:
                                with col2:
                                    st.write(f"{metric}")
                                    result_df_t = result_df.T
                                    result_df_t.index.name = '属性'
                                    st.dataframe(result_df_t)

        # Excelファイルの保存用のデータ準備
        excel_data = {
            "質問ごとの分析_平均": results_mean,
            "質問ごとの分析_100点換算": results_score,
        }

        if question_groups:
            excel_data.update({
                "グループごとの分析_平均": group_mean_df,
                "グループごとの分析_100点換算": group_score_df
            })

        self._save_to_excel(excel_data, f"numeric_analysis_{attribute}")



