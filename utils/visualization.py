import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd

class Visualizer:
    def _save_to_excel(self, data_dict, filename):
        excel_path = f"{filename}.xlsx"
        
        with pd.ExcelWriter(excel_path, engine='openpyxl', mode='w') as writer:
            if isinstance(data_dict, dict):
                for sheet_name, df in data_dict.items():
                    df.to_excel(
                        writer,
                        sheet_name=sheet_name,
                        index=True,
                        header=True,
                        engine='openpyxl'
                    )
            else:
                data_dict.to_excel(
                    writer,
                    index=True,
                    header=True,
                    engine='openpyxl'
                )
        
        with open(excel_path, 'rb') as f:
            st.download_button(
                label="Excelファイルをダウンロード",
                data=f,
                file_name=excel_path,
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        
        import os
        os.remove(excel_path)

    def display_dashboard(self, dfs, config_manager):
        if not dfs:
            st.info("データを読み込んでください。")
            return
            
        # データセットと属性の選択
        year_options = [f"データセット{i+1}({st.session_state.data_processor.dates[i]})" for i in range(len(dfs))]
        selected_year_idx = st.selectbox("データを選択:", range(len(dfs)), format_func=lambda x: year_options[x])
        
        df = dfs[selected_year_idx]
        column_names = config_manager.config.get('column_names', {})
        question_groups = config_manager.config.get('question_groups', {})
        
        # 質問グループの選択
        group_options = ["すべての質問"] + list(question_groups.keys())
        selected_group = st.selectbox("質問グループを選択:", group_options)
        
        # 選択されたグループの列を取得
        target_columns = question_groups.get(selected_group, df.columns) if selected_group != "すべての質問" else df.columns
        df_filtered = df[target_columns]

        # 数値回答の分析
        st.header("【数値回答】")
        
        # 1. 相関係数ヒートマップ
        st.subheader("1. 質問間の相関係数ヒートマップ")
        self._display_correlation_heatmap(df_filtered, column_names)
        
        # 2. 回答の件数と構成比の帯グラフ
        st.subheader("2. 回答の分布")
        self._display_value_distribution(df_filtered, column_names)
        
        # 3. 平均値の散布図
        st.subheader("3. 平均値の散布図")
        self._display_scatter_plot(df_filtered, column_names)
        
        # 数値回答（複数回答）の分析
        st.header("【数値回答（複数回答）】")
        
        # 属性の選択
        attributes = ["全体"] + config_manager.config.get('attributes', [])
        selected_attribute = st.selectbox("属性項目:", attributes)
        
        # 表示方法の選択
        display_mode = st.radio("表示方法:", ["まとめて表示", "個別に表示"])
        
        self._display_multiple_choice_analysis(df_filtered, selected_attribute, column_names, display_mode)

    def _display_correlation_heatmap(self, df, column_names):
        numeric_columns = df.select_dtypes(include=['number']).columns
        if not numeric_columns.empty:
            display_columns = [column_names.get(col, col) for col in numeric_columns]
            corr_data = df[numeric_columns].corr()
            
            fig = go.Figure(data=go.Heatmap(
                z=corr_data,
                x=display_columns,
                y=display_columns,
                colorscale='RdBu',
                text=[[f'{val:.2f}' for val in row] for row in corr_data.values],
                texttemplate='%{text}',
                textfont={"size": 10},
                hoverongaps=False
            ))
            
            fig.update_layout(
                title="相関係数ヒートマップ",
                width=800,
                height=800,
                xaxis={'tickangle': 45},
                yaxis={'tickangle': 0}
            )
            
            st.plotly_chart(fig)
        else:
            st.info("数値データが見つかりませんでした。")

    def _display_value_distribution(self, df, column_names):
        numeric_columns = df.select_dtypes(include=['number']).columns
        if not numeric_columns.empty:
            # 値の分布を表示
            for col in numeric_columns:
                display_name = column_names.get(col, col)
                
                # 回答の件数と構成比の計算
                value_counts = df[col].value_counts().sort_index()
                total_count = len(df)
                
                # 帯グラフの作成
                fig = go.Figure()
                
                # 回答件数のバー
                fig.add_trace(go.Bar(
                    name="回答件数",
                    x=value_counts.index,
                    y=value_counts.values,
                    text=value_counts.values,
                    textposition='auto',
                ))
                
                # 構成比の折れ線
                fig.add_trace(go.Scatter(
                    name="構成比(%)",
                    x=value_counts.index,
                    y=(value_counts.values / total_count) * 100,
                    yaxis="y2",
                    line=dict(color='red'),
                    mode='lines+markers+text',
                    text=[f'{(v/total_count)*100:.1f}%' for v in value_counts.values],
                    textposition='top center'
                ))
                
                fig.update_layout(
                    title=f"{display_name}の回答分布",
                    xaxis_title="回答値",
                    yaxis_title="回答件数",
                    yaxis2=dict(
                        title="構成比(%)",
                        overlaying="y",
                        side="right",
                        range=[0, 100]
                    ),
                    showlegend=True,
                    height=400
                )
                
                st.plotly_chart(fig)
        else:
            st.info("数値データが見つかりませんでした。")

    def _display_scatter_plot(self, df, column_names):
        numeric_columns = df.select_dtypes(include=['number']).columns
        if len(numeric_columns) >= 2:
            col1, col2 = st.columns(2)
            with col1:
                x_axis = st.selectbox(
                    "X軸の項目:",
                    numeric_columns,
                    format_func=lambda x: column_names.get(x, x),
                    key="scatter_x_axis"
                )
            with col2:
                y_axis = st.selectbox(
                    "Y軸の項目:",
                    numeric_columns,
                    format_func=lambda x: column_names.get(x, x),
                    key="scatter_y_axis"
                )
            
            if x_axis and y_axis:
                fig = px.scatter(
                    df,
                    x=x_axis,
                    y=y_axis,
                    labels={
                        x_axis: column_names.get(x_axis, x_axis),
                        y_axis: column_names.get(y_axis, y_axis)
                    }
                )
                
                fig.update_layout(
                    title=f"{column_names.get(x_axis, x_axis)}と{column_names.get(y_axis, y_axis)}の相関",
                    height=500
                )
                
                st.plotly_chart(fig)

    def _display_multiple_choice_analysis(self, df, attribute, column_names, display_mode):
        multiple_choice_cols = [col for col in df.columns 
                            if not pd.api.types.is_numeric_dtype(df[col]) and 
                            df[col].fillna('').astype(str).str.contains(',').any()]
        
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
                        subset_values = subset[col].fillna('').astype(str).str.split(',').explode()
                        subset_counts = subset_values.value_counts().sort_index()
                        
                        fig.add_trace(go.Bar(
                            name=str(attr_value),
                            x=subset_counts.index,
                            y=subset_counts.values,
                            text=subset_counts.values,
                            textposition='auto'
                        ))
                    
                    fig.update_layout(
                        title=f"{display_name}の回答分布（属性別）",
                        barmode='group',
                        height=400
                    )
                    
                    st.plotly_chart(fig)
                else:
                    # 全体表示
                    fig = go.Figure([go.Bar(
                        x=counts.index,
                        y=counts.values,
                        text=counts.values,
                        textposition='auto'
                    )])
                    
                    fig.update_layout(
                        title=f"{display_name}の回答分布",
                        height=400
                    )
                    
                    st.plotly_chart(fig)
            else:
                # 属性値ごとに個別のチャートを表示
                if attribute != "全体":
                    for attr_value in df[attribute].unique():
                        subset = df[df[attribute] == attr_value]
                        subset_values = subset[col].fillna('').astype(str).str.split(',').explode()
                        subset_counts = subset_values.value_counts().sort_index()
                        
                        fig = go.Figure([go.Bar(
                            x=subset_counts.index,
                            y=subset_counts.values,
                            text=subset_counts.values,
                            textposition='auto'
                        )])
                        
                        fig.update_layout(
                            title=f"{display_name}の回答分布（{attr_value}）",
                            height=400
                        )
                        
                        st.plotly_chart(fig)
                else:
                    # 全体表示
                    fig = go.Figure([go.Bar(
                        x=counts.index,
                        y=counts.values,
                        text=counts.values,
                        textposition='auto'
                    )])
                    
                    fig.update_layout(
                        title=f"{display_name}の回答分布",
                        height=400
                    )
                    
                    st.plotly_chart(fig)

    def display_numerical_tables(self, dfs, config_manager):
        if not dfs:
            st.info("データを読み込んでください。")
            return
            
        # データセットの選択
        year_options = [f"データセット{i+1}({st.session_state.data_processor.dates[i]})" for i in range(len(dfs))]
        selected_year_idx = st.selectbox(
            "データを選択:",
            range(len(dfs)),
            format_func=lambda x: year_options[x]
        )
        
        # 属性の選択
        attributes = ["全体"] + config_manager.config.get('attributes', [])
        selected_attribute = st.selectbox("属性項目:", attributes)
        
        df = dfs[selected_year_idx]
        
        # 数値回答と複数回答の分析を実行
        self._display_numeric_analysis(df, selected_attribute, config_manager)
        self._display_multiple_choice_analysis(
        df, 
        selected_attribute, 
        config_manager.config.get('column_names', {}),  # ConfigManager.configからcolumn_namesを取得
        "まとめて表示"
    )

    def _display_numeric_analysis(self, df, attribute, config_manager):
        column_names = config_manager.config.get('column_names', {})
        question_groups = config_manager.config.get('question_groups', {})
        value_groups = config_manager.config.get('value_groups', {})
        
        if attribute == "全体":
            results = pd.DataFrame()
            group_results = pd.DataFrame()
            value_group_results = pd.DataFrame()
            group_value_results = pd.DataFrame()
            
            # 数値列の処理
            for col in df.columns:
                if pd.api.types.is_numeric_dtype(df[col]):
                    mean_val = df[col].mean()
                    max_val = df[col].max()
                    display_name = column_names.get(col, col)
                    
                    results.loc[display_name, "平均"] = '{:g}'.format(mean_val) if pd.notnull(mean_val) else '-'
                    
                    # 満点の取得
                    max_scores = config_manager.config.get('max_scores', {})
                    
                    if pd.notnull(mean_val):
                        # 設定された満点、もしくはデータの最大値を使用
                        max_score = max_scores.get(col, max_val)
                        if max_score > 0:
                            score = (mean_val / max_score) * 100
                            results.loc[display_name, "100点換算"] = '{:g}'.format(score)
                        else:
                            results.loc[display_name, "100点換算"] = '-'
                    else:
                        results.loc[display_name, "100点換算"] = '-'
                        
                    # 値グループ化の処理
                    if col in value_groups:
                        group_counts = {}
                        total_count = len(df)
                        
                        for range_str, label in value_groups[col].items():
                            min_val, max_val = map(float, range_str.split('-'))
                            mask = (df[col] >= min_val) & (df[col] <= max_val)
                            count = mask.sum()
                            percentage = (count / total_count) * 100
                            group_counts[label] = count
                            value_group_results.loc[display_name, f"{label}（件数）"] = count
                            value_group_results.loc[display_name, f"{label}（%）"] = '{:.1f}'.format(percentage)
                            value_group_results.loc[display_name, f"{label}（平均）"] = '{:g}'.format(df[col][mask].mean()) if count > 0 else '-'

            # グループごとの集計結果を計算
            if question_groups:
                for group_name, questions in question_groups.items():
                    numeric_questions = [q for q in questions if q in df.columns and pd.api.types.is_numeric_dtype(df[q])]
                    if numeric_questions:
                        group_mean = df[numeric_questions].mean().mean()
                        max_val = df[numeric_questions].max().max()
                        group_results.loc[group_name, "平均"] = '{:g}'.format(group_mean) if pd.notnull(group_mean) else '-'
                        if pd.notnull(group_mean) and pd.notnull(max_val) and max_val != 0:
                            score = (group_mean / max_val) * 100
                            group_results.loc[group_name, "100点換算"] = '{:g}'.format(score)
                        else:
                            group_results.loc[group_name, "100点換算"] = '-'

            # 質問グループごとの値グループ分析
            if question_groups and value_groups:
                for group_name, questions in question_groups.items():
                    # グループ内の数値列かつ値グループが設定されている列のみを処理
                    valid_questions = [q for q in questions 
                                   if q in df.columns and 
                                   pd.api.types.is_numeric_dtype(df[q]) and 
                                   q in value_groups]
                    
                    if valid_questions:
                        # 各値グループのラベルを収集
                        all_labels = set()
                        for col in valid_questions:
                            all_labels.update(value_groups[col].values())
                        
                        # 各ラベルごとに集計
                        total_count = len(df)
                        for label in all_labels:
                            # 各質問の件数を合計
                            total_label_count = 0
                            label_sum = 0
                            
                            for col in valid_questions:
                                col_count = 0
                                col_sum = 0
                                for range_str, range_label in value_groups[col].items():
                                    if range_label == label:
                                        min_val, max_val = map(float, range_str.split('-'))
                                        mask = (df[col] >= min_val) & (df[col] <= max_val)
                                        count = mask.sum()
                                        col_count += count
                                        if count > 0:
                                            col_sum += df[col][mask].mean() * count
                                total_label_count += col_count
                                if col_count > 0:
                                    label_sum += col_sum
                            
                            # 結果を集計
                            group_value_results.loc[group_name, f"{label}（件数）"] = total_label_count
                            group_value_results.loc[group_name, f"{label}（%）"] = '{:.1f}'.format((total_label_count / (len(valid_questions) * total_count)) * 100)
                            group_value_results.loc[group_name, f"{label}（平均）"] = '{:g}'.format(label_sum / total_label_count) if total_label_count > 0 else '-'

            if not results.empty:
                st.write("質問ごとの分析結果")
                st.dataframe(results)
                
                if not group_results.empty:
                    st.write("質問グループごとの分析結果")
                    st.dataframe(group_results)
                
                if not value_group_results.empty:
                    st.write("値グループ化による分析結果")
                    st.dataframe(value_group_results)
                
                if not group_value_results.empty:
                    st.write("質問グループごとの値グループ分析結果")
                    st.dataframe(group_value_results)

                # Excelエクスポートにすべてのデータを含める
                excel_data = {
                    "質問ごとの分析": results,
                    "グループごとの分析": group_results,
                    "値グループ分析": value_group_results,
                    "グループ別値グループ分析": group_value_results if not group_value_results.empty else pd.DataFrame()
                }
                self._save_to_excel(excel_data, "numeric_analysis_all")
            else:
                st.info("数値データが見つかりませんでした。")

        else:
            # 属性別の分析
            numeric_cols = df.select_dtypes(include=['number']).columns
            if len(numeric_cols) == 0:
                st.info("数値データが見つかりませんでした。")
                return
                
            results_dict = {
                '平均': {},
                '100点換算': {}
            }
            
            for col in numeric_cols:
                results_dict['平均'][col] = {}
                results_dict['100点換算'][col] = {}
                max_val = df[col].max()
                
                total_mean = df[col].mean()
                results_dict['平均'][col]['全体'] = '{:g}'.format(total_mean) if pd.notnull(total_mean) else '-'
                if pd.notnull(total_mean) and pd.notnull(max_val) and max_val != 0:
                    total_score = (total_mean / max_val) * 100
                    results_dict['100点換算'][col]['全体'] = '{:g}'.format(total_score)
                else:
                    results_dict['100点換算'][col]['全体'] = '-'
                
                for value in df[attribute].unique():
                    subset = df[df[attribute] == value]
                    mean_val = subset[col].mean()
                    
                    results_dict['平均'][col][value] = '{:g}'.format(mean_val) if pd.notnull(mean_val) else '-'
                    
                    if pd.notnull(mean_val) and pd.notnull(max_val) and max_val != 0:
                        score = (mean_val / max_val) * 100
                        results_dict['100点換算'][col][value] = '{:g}'.format(score)
                    else:
                        results_dict['100点換算'][col][value] = '-'
            
            results_mean = pd.DataFrame(results_dict['平均']).T
            results_score = pd.DataFrame(results_dict['100点換算']).T
            
            column_order = ['全体'] + [col for col in results_mean.columns if col != '全体']
            results_mean = results_mean[column_order]
            results_score = results_score[column_order]
            
            if attribute != "全体":
                self._save_to_excel(
                    {
                        "平均値": results_mean,
                        "100点換算": results_score
                    },
                    f"numeric_analysis_{attribute}"
                )
                
                st.write("平均値")
                st.dataframe(results_mean)
                st.write("100点換算")
                st.dataframe(results_score)
            else:
                combined_results = pd.DataFrame()
                combined_results["平均"] = results["平均"]
                combined_results["100点換算"] = results["100点換算"]
                st.write("平均値と100点換算")
                st.dataframe(combined_results)
                self._save_to_excel(combined_results, "numeric_analysis_all")