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
        st.subheader("【数値回答】")
        
        # 1. 相関係数ヒートマップ
        st.write("1. 質問間の相関係数ヒートマップ")
        self._display_correlation_heatmap(df_filtered, column_names)
        
        # 2. 回答の件数と構成比の帯グラフ
        st.write("2. 回答の分布")
        self._display_value_distribution(df_filtered, column_names)
        
        # 3. 平均値の散布図
        st.write("3. 平均値の散布図")
        self._display_scatter_plot(df_filtered, column_names)
        
        # 数値回答（複数回答）の分析
        st.subheader("【数値回答（複数回答）】")
        
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
        
        # 数値回答の分析を実行
        self._display_numeric_analysis(df, selected_attribute, config_manager)

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
        st.subheader("質問ごとの分析結果")
        results = {'平均': {}, '100点換算': {}}
        
        for col in numeric_cols:
            display_name = column_names.get(col, col)
            max_val = df[col].max()
            max_score = max_scores.get(col, max_val)
            
            results['平均'][display_name] = {}
            results['100点換算'][display_name] = {}
            
            # 全体の集計
            total_mean = df[col].mean()
            results['平均'][display_name]['全体'] = '{:g}'.format(total_mean) if pd.notnull(total_mean) else '-'
            
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
                    
                    results['平均'][display_name][value] = '{:g}'.format(mean_val) if pd.notnull(mean_val) else '-'
                    if pd.notnull(mean_val) and max_score > 0:
                        score = (mean_val / max_score) * 100
                        results['100点換算'][display_name][value] = '{:g}'.format(score)
                    else:
                        results['100点換算'][display_name][value] = '-'
        
        # 結果の表示
        results_mean = pd.DataFrame(results['平均']).T
        results_score = pd.DataFrame(results['100点換算']).T
        
        if attribute != "全体":
            column_order = ['全体'] + [col for col in results_mean.columns if col != '全体']
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
            st.subheader("質問グループごとの分析結果")
            group_results = {'平均': {}, '100点換算': {}}
            
            for group_name, questions in question_groups.items():
                numeric_questions = [q for q in questions if q in df.columns and pd.api.types.is_numeric_dtype(df[q])]
                if numeric_questions:
                    group_results['平均'][group_name] = {}
                    group_results['100点換算'][group_name] = {}
                    
                    # 全体の集計
                    group_mean = df[numeric_questions].mean().mean()
                    group_results['平均'][group_name]['全体'] = '{:g}'.format(group_mean) if pd.notnull(group_mean) else '-'
                    
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
                        group_results['100点換算'][group_name]['全体'] = '{:g}'.format(avg_score)
                    else:
                        group_results['100点換算'][group_name]['全体'] = '-'
                    
                    # 属性値ごとの集計
                    if attribute != "全体":
                        for value in df[attribute].unique():
                            subset = df[df[attribute] == value]
                            subset_mean = subset[numeric_questions].mean().mean()
                            
                            group_results['平均'][group_name][value] = '{:g}'.format(subset_mean) if pd.notnull(subset_mean) else '-'
                            
                            # 属性値ごとの100点換算
                            subset_scores = []
                            for q in numeric_questions:
                                mean_val = subset[q].mean()
                                max_score = max_scores.get(q, df[q].max())
                                if pd.notnull(mean_val) and max_score > 0:
                                    score = (mean_val / max_score) * 100
                                    subset_scores.append(score)
                            
                            if subset_scores:
                                avg_score = sum(subset_scores) / len(subset_scores)
                                group_results['100点換算'][group_name][value] = '{:g}'.format(avg_score)
                            else:
                                group_results['100点換算'][group_name][value] = '-'
            
            group_mean_df = pd.DataFrame(group_results['平均']).T
            group_score_df = pd.DataFrame(group_results['100点換算']).T
            
            if attribute != "全体":
                column_order = ['全体'] + [col for col in group_mean_df.columns if col != '全体']
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
        
        # 値グループごとの分析
        if value_groups:
            st.subheader("値グループ分析結果")
            
            # 質問ごとの値グループ分析
            st.write("質問ごとの値グループ分析")
            
            # 数値回答の質問を取得
            numeric_cols = df.select_dtypes(include=['number']).columns
            
            for col in numeric_cols:
                display_name = column_names.get(col, col)
                
                # expanderを使用してレイアウトを改善
                with st.expander(f"● {display_name}"):
                    if col in value_groups:
                        value_group_results = {}
                        
                        # 全体の集計
                        total_count = len(df)
                        for range_str, label in value_groups[col].items():
                            min_val, max_val = map(float, range_str.split('-'))
                            mask = (df[col] >= min_val) & (df[col] <= max_val)
                            count = mask.sum()
                            
                            value_group_results[label] = {}
                            value_group_results[label]['全体'] = {
                                '件数': count,
                                '割合': '{:.1f}'.format((count / total_count) * 100) if total_count > 0 else '-'
                            }
                            
                            # 属性値ごとの集計
                            if attribute != "全体":
                                for attr_value in df[attribute].unique():
                                    subset = df[df[attribute] == attr_value]
                                    subset_mask = (subset[col] >= min_val) & (subset[col] <= max_val)
                                    subset_count = subset_mask.sum()
                                    
                                    value_group_results[label][attr_value] = {
                                        '件数': subset_count,
                                        '割合': '{:.1f}'.format((subset_count / len(subset)) * 100) if len(subset) > 0 else '-'
                                    }
                        
                        # 結果の表示
                        col1, col2 = st.columns(2)
                        for metric in ['件数', '割合']:
                            columns = ['全体'] + (list(df[attribute].unique()) if attribute != "全体" else [])
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
                    numeric_questions = [q for q in questions 
                                      if q in df.columns and 
                                      pd.api.types.is_numeric_dtype(df[q])]
                    
                    valid_questions = [q for q in numeric_questions if q in value_groups]
                    
                    with st.expander(f"● {group_name}"):
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
                                    for range_str, range_label in value_groups[col].items():
                                        if range_label == label:
                                            min_val, max_val = map(float, range_str.split('-'))
                                            mask = (df[col] >= min_val) & (df[col] <= max_val)
                                            label_count += mask.sum()
                                
                                # 有効な回答数で計算
                                valid_responses = sum(1 for _ in df.iterrows()) * len(valid_questions)
                                group_results[label] = {}
                                group_results[label]['全体'] = {
                                    '件数': label_count,
                                    '割合': '{:.1f}'.format((label_count / valid_responses) * 100) if valid_responses > 0 else '-'
                                }
                                
                                # 属性値ごとの集計
                                if attribute != "全体":
                                    for attr_value in df[attribute].unique():
                                        subset = df[df[attribute] == attr_value]
                                        attr_label_count = 0
                                        
                                        for col in valid_questions:
                                            for range_str, range_label in value_groups[col].items():
                                                if range_label == label:
                                                    min_val, max_val = map(float, range_str.split('-'))
                                                    mask = (subset[col] >= min_val) & (subset[col] <= max_val)
                                                    attr_label_count += mask.sum()
                                        
                                        # 属性ごとの有効な回答数で計算
                                        attr_valid_responses = len(subset) * len(valid_questions)
                                        group_results[label][attr_value] = {
                                            '件数': attr_label_count,
                                            '割合': '{:.1f}'.format((attr_label_count / attr_valid_responses) * 100) if attr_valid_responses > 0 else '-'
                                        }
                            
                            # 結果の表示
                            col1, col2 = st.columns(2)
                            for metric in ['件数', '割合']:
                                columns = ['全体'] + (list(df[attribute].unique()) if attribute != "全体" else [])
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
        
        # Excelファイルの保存
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