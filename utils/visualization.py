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

    def _display_numeric_analysis(self, df, attribute, config_manager):
        column_names = config_manager.config.get('column_names', {})
        question_groups = config_manager.config.get('question_groups', {})
        value_groups = config_manager.config.get('value_groups', {})
        
        if attribute == "全体":
            results = pd.DataFrame()
            group_results = pd.DataFrame()
            value_group_results = pd.DataFrame()
            
            # 数値列の処理
            for col in df.columns:
                if pd.api.types.is_numeric_dtype(df[col]):
                    mean_val = df[col].mean()
                    max_val = df[col].max()
                    display_name = column_names.get(col, col)
                    
                    results.loc[display_name, "平均"] = '{:g}'.format(mean_val) if pd.notnull(mean_val) else '-'
                    
                    if pd.notnull(mean_val) and pd.notnull(max_val) and max_val != 0:
                        score = (mean_val / max_val) * 100
                        results.loc[display_name, "100点換算"] = '{:g}'.format(score)
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

            if not results.empty:
                st.write("質問ごとの分析結果")
                st.dataframe(results)
                
                if not group_results.empty:
                    st.write("質問グループごとの分析結果")
                    st.dataframe(group_results)
                
                if not value_group_results.empty:
                    st.write("値グループ化による分析結果")
                    st.dataframe(value_group_results)
                    
                # 質問グループごとの値グループ分析
                if question_groups and value_groups:
                    st.write("質問グループごとの値グループ分析")
                    group_value_results = pd.DataFrame()
                    
                    for group_name, questions in question_groups.items():
                        # グループ内の数値列かつ値グループが設定されている列のみを処理
                        valid_questions = [q for q in questions 
                                         if q in df.columns and 
                                         pd.api.types.is_numeric_dtype(df[q]) and 
                                         q in value_groups]
                        
                        if valid_questions:
                            for col in valid_questions:
                                display_name = f"{group_name}: {column_names.get(col, col)}"
                                total_count = len(df)
                                
                                for range_str, label in value_groups[col].items():
                                    min_val, max_val = map(float, range_str.split('-'))
                                    mask = (df[col] >= min_val) & (df[col] <= max_val)
                                    count = mask.sum()
                                    percentage = (count / total_count) * 100
                                    group_value_results.loc[display_name, f"{label}（件数）"] = count
                                    group_value_results.loc[display_name, f"{label}（%）"] = '{:.1f}'.format(percentage)
                                    group_value_results.loc[display_name, f"{label}（平均）"] = '{:g}'.format(df[col][mask].mean()) if count > 0 else '-'
                    
                    if not group_value_results.empty:
                        st.write("質問グループごとの値グループ分析結果")
                        st.dataframe(group_value_results)

                # Excelエクスポートにすべてのデータを含める
                excel_data = {
                    "質問ごとの分析": results,
                    "グループごとの分析": group_results,
                    "値グループ分析": value_group_results
                }
                if 'group_value_results' in locals() and not group_value_results.empty:
                    excel_data["グループ別値グループ分析"] = group_value_results
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

    def display_numerical_tables(self, dfs, config_manager):
        if not dfs:
            st.info("データを読み込んでください。")
            return
            
        question_groups = config_manager.config.get('question_groups', {})
            
        year_options = [f"{i+1}回目のデータ" for i in range(len(dfs))]
        selected_year_idx = st.selectbox(
            "データを選択:",
            range(len(dfs)),
            format_func=lambda x: year_options[x]
        )
        
        column_names = config_manager.config.get('column_names', {})
        attributes = ["全体"] + config_manager.config['attributes']
        attribute_display_names = {
            attr: column_names.get(attr, attr) if attr != "全体" else attr
            for attr in attributes
        }
        
        selected_attribute = st.selectbox(
            "属性項目を選択:",
            attributes,
            format_func=lambda x: attribute_display_names[x]
        )
        
        df = dfs[selected_year_idx]
        
        for question_type in ["数値回答", "数値回答（複数回答）"]:
            st.subheader(f"{question_type}の分析結果")
            
            if question_type == "数値回答":
                self._display_numeric_analysis(df, selected_attribute, config_manager)
            else:
                self._display_multiple_choice_analysis(df, selected_attribute, config_manager)

    def _display_multiple_choice_analysis(self, df, attribute, config_manager):
        # 列名のマッピングを取得
        column_names = config_manager.config.get('column_names', {})
        
        if attribute == "全体":
            results = pd.DataFrame()
            
            for col in df.columns:
                try:
                    if pd.api.types.is_numeric_dtype(df[col]) or not df[col].fillna('').astype(str).str.contains(',').any():
                        continue
                        
                    values = df[col].fillna('').astype(str).str.split(',').explode()
                    counts = values.value_counts().sort_index()
                    results[column_names.get(col, col)] = counts
                    
                except Exception as e:
                    st.warning(f"列 '{col}' の処理中にエラーが発生しました: {str(e)}")
                    continue
            
            if not results.empty:
                st.write("回答件数")
                st.dataframe(results)
                self._save_to_excel(results, "multiple_choice_analysis_all")
            else:
                st.info("複数回答の質問が見つかりませんでした。")
        else:
            # 属性値ごとの結果を辞書に格納
            all_results = {}
            
            for attr_value in df[attribute].unique():
                results = pd.DataFrame()
                subset_df = df[df[attribute] == attr_value]
                
                for col in df.columns:
                    try:
                        if pd.api.types.is_numeric_dtype(df[col]) or not df[col].fillna('').astype(str).str.contains(',').any():
                            continue
                            
                        values = subset_df[col].fillna('').astype(str).str.split(',').explode()
                        counts = values.value_counts().sort_index()
                        results[column_names.get(col, col)] = counts
                        
                    except Exception as e:
                        st.warning(f"列 '{col}' の処理中にエラーが発生しました: {str(e)}")
                        continue
                
                if not results.empty:
                    st.write(f"【{attr_value}】")
                    st.dataframe(results)
                    all_results[attr_value] = results
            
            # すべての結果を1つのExcelファイルに保存
            if all_results:
                self._save_to_excel(all_results, f"multiple_choice_analysis_{attribute}")

    def display_dashboard(self, dfs, config_manager):
        if not dfs:
            st.info("データを読み込んでください。")
            return
            
        # 列名のマッピングを取得
        column_names = config_manager.config.get('column_names', {})
        question_groups = config_manager.config.get('question_groups', {})
            
        year_options = [f"{i+1}回目のデータ" for i in range(len(dfs))]
        selected_year_idx = st.selectbox(
            "データを選択:", 
            range(len(dfs)), 
            format_func=lambda x: year_options[x],
            key="dashboard_year"
        )
        
        selected_attribute = st.selectbox(
            "属性項目を選択:",
            ["全体"] + config_manager.config['attributes'],
            key="dashboard_attribute"
        )
        
        # 質問グループの選択
        group_options = ["すべての質問"] + list(question_groups.keys())
        selected_group = st.selectbox(
            "質問グループを選択:",
            group_options,
            key="dashboard_group"
        )

        df = dfs[selected_year_idx]
        
        # 選択された質問グループに基づいて列を制限
        if selected_group != "すべての質問":
            target_columns = question_groups[selected_group]
            df = df[target_columns]

        # Heatmap
        st.subheader("相関係数ヒートマップ")
        
        numeric_columns = df.select_dtypes(include=['number']).columns
        if not numeric_columns.empty:
            # 列名を日本語表示に変換
            display_columns = [column_names.get(col, col) for col in numeric_columns]
            
            # 相関行列の計算
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
                title={
                    'text': f"{selected_group}の相関係数ヒートマップ",
                    'x': 0.5,
                    'xanchor': 'center',
                    'font': {'size': 20}
                },
                width=800,
                height=800,
                xaxis={'tickangle': 45},
                yaxis={'tickangle': 0},
                margin=dict(t=100, l=100, r=100, b=100)
            )
            
            st.plotly_chart(fig)
        else:
            st.info("数値データが見つかりませんでした。")

        # Scatter plot
        if len(numeric_columns) >= 2:
            st.subheader("相関散布図")
            numeric_display_names = {col: column_names.get(col, col) for col in numeric_columns}
            x_axis = st.selectbox(
                "X軸:",
                numeric_columns,
                format_func=lambda x: numeric_display_names[x]
            )
            y_axis = st.selectbox(
                "Y軸:",
                numeric_columns,
                format_func=lambda x: numeric_display_names[x]
            )
            
            fig = px.scatter(
                df,
                x=x_axis,
                y=y_axis,
                labels={
                    x_axis: numeric_display_names[x_axis],
                    y_axis: numeric_display_names[y_axis]
                }
            )
            st.plotly_chart(fig)

        # 複数回答の分析
        st.subheader("複数回答の分析")
        
        # 数値回答（複数回答）の表示
        multiple_numeric_cols = []
        multiple_numeric_display_names = {}
        
        for col in df.columns:
            values = df[col].fillna('').astype(str)
            if values.str.contains(',').any() and values.str.match(r'^\s*\d+(?:\s*,\s*\d+)*\s*$').all():
                multiple_numeric_cols.append(col)
                multiple_numeric_display_names[col] = column_names.get(col, col)
        
        if multiple_numeric_cols:
            selected_numeric_col = st.selectbox(
                "数値複数回答の質問を選択:",
                multiple_numeric_cols,
                format_func=lambda x: multiple_numeric_display_names[x],
                key="numeric_multiple"
            )
            
            # 回答の分解と集計
            values = df[selected_numeric_col].fillna('').astype(str).str.split(',').explode()
            counts = values.value_counts().sort_index()
            
            # 横棒グラフの作成
            fig = go.Figure()
            fig.add_trace(go.Bar(
                y=counts.index,
                x=counts.values,
                orientation='h',
                text=counts.values,
                textposition='auto',
            ))
            
            fig.update_layout(
                title=f"{multiple_numeric_display_names[selected_numeric_col]}の回答件数",
                xaxis_title="回答件数",
                yaxis_title="選択肢",
                height=400 + len(counts) * 20,
                margin=dict(l=200)
            )
            
            st.plotly_chart(fig)
            
            # 100%積み上げグラフ
            if selected_attribute != "全体":
                st.subheader("属性別の回答分布")
                
                # クロス集計
                cross_tab = pd.crosstab(
                    df[selected_attribute],
                    df[selected_numeric_col].fillna('').astype(str).str.split(',').explode(),
                    normalize='index'
                ) * 100
                
                # 100%積み上げ横棒グラフ
                fig = go.Figure()
                
                for col in cross_tab.columns:
                    fig.add_trace(go.Bar(
                        y=cross_tab.index,
                        x=cross_tab[col],
                        name=col,
                        orientation='h',
                    ))
                
                fig.update_layout(
                    barmode='relative',
                    title=f"{multiple_numeric_display_names[selected_numeric_col]}の属性別分布",
                    xaxis_title="割合 (%)",
                    yaxis_title=column_names.get(selected_attribute, selected_attribute),
                    height=400 + len(cross_tab.index) * 20,
                    margin=dict(l=200)
                )
                
                st.plotly_chart(fig)
        
        # テキスト複数回答の表示
        multiple_text_cols = []
        multiple_text_display_names = {}
        
        for col in df.columns:
            values = df[col].fillna('').astype(str)
            if values.str.contains(',').any() and not values.str.match(r'^\s*\d+(?:\s*,\s*\d+)*\s*$').all():
                multiple_text_cols.append(col)
                multiple_text_display_names[col] = column_names.get(col, col)
        
        if multiple_text_cols:
            selected_text_col = st.selectbox(
                "テキスト複数回答の質問を選択:",
                multiple_text_cols,
                format_func=lambda x: multiple_text_display_names[x],
                key="text_multiple"
            )
            
            # 回答の分解と集計
            values = df[selected_text_col].fillna('').astype(str).str.split(',').explode()
            counts = values.value_counts()
            
            # 横棒グラフの作成
            fig = go.Figure()
            fig.add_trace(go.Bar(
                y=counts.index,
                x=counts.values,
                orientation='h',
                text=counts.values,
                textposition='auto',
            ))
            
            fig.update_layout(
                title=f"{multiple_text_display_names[selected_text_col]}の回答件数",
                xaxis_title="回答件数",
                yaxis_title="選択肢",
                height=400 + len(counts) * 20,
                margin=dict(l=200)
            )
            
            st.plotly_chart(fig)
            
            # 100%積み上げグラフ
            if selected_attribute != "全体":
                st.subheader("属性別の回答分布")
                
                # クロス集計
                cross_tab = pd.crosstab(
                    df[selected_attribute],
                    df[selected_text_col].fillna('').astype(str).str.split(',').explode(),
                    normalize='index'
                ) * 100
                
                # 100%積み上げ横棒グラフ
                fig = go.Figure()
                
                for col in cross_tab.columns:
                    fig.add_trace(go.Bar(
                        y=cross_tab.index,
                        x=cross_tab[col],
                        name=col,
                        orientation='h',
                    ))
                
                fig.update_layout(
                    barmode='relative',
                    title=f"{multiple_text_display_names[selected_text_col]}の属性別分布",
                    xaxis_title="割合 (%)",
                    yaxis_title=column_names.get(selected_attribute, selected_attribute),
                    height=400 + len(cross_tab.index) * 20,
                    margin=dict(l=200)
                )
                
                st.plotly_chart(fig)