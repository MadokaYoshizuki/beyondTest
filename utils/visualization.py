import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd

class Visualizer:
    def display_numerical_tables(self, dfs, config_manager):
        if not dfs:
            st.info("データを読み込んでください。")
            return
            
        year_options = [f"{i+1}回目のデータ" for i in range(len(dfs))]
        selected_year_idx = st.selectbox("データを選択:", range(len(dfs)), format_func=lambda x: year_options[x])
        selected_attribute = st.selectbox(
            "属性項目を選択:",
            ["全体"] + config_manager.config['attributes']
        )

        df = dfs[selected_year_idx]
        
        for question_type in ["数値回答", "数値回答（複数回答）"]:
            st.subheader(question_type)
            
            if question_type == "数値回答":
                self._display_numeric_analysis(df, selected_attribute, config_manager)
            else:
                self._display_multiple_choice_analysis(df, selected_attribute, config_manager)

    def _display_numeric_analysis(self, df, attribute, config_manager):
        if attribute == "全体":
            results = pd.DataFrame()
            for col in df.columns:
                if pd.api.types.is_numeric_dtype(df[col]):
                    mean_val = df[col].mean()
                    max_val = df[col].max()
                    results.loc[col, "平均"] = '{:g}'.format(mean_val) if pd.notnull(mean_val) else '-'
                    results.loc[col, "100点換算"] = '{:g}'.format((mean_val / max_val) * 100) if pd.notnull(mean_val) and pd.notnull(max_val) and max_val != 0 else '-'
        else:
            # 数値列を抽出
            numeric_cols = df.select_dtypes(include=['number']).columns
            if len(numeric_cols) == 0:
                st.info("数値データが見つかりませんでした。")
                return
                
            # 属性値ごとの結果を格納するための辞書
            results_dict = {
                '平均': {},
                '100点換算': {}
            }
            
            # 各数値列について処理
            for col in numeric_cols:
                results_dict['平均'][col] = {}
                results_dict['100点換算'][col] = {}
                max_val = df[col].max()  # 全体の最大値を基準とする
                
                # まず全体のデータを計算
                total_mean = df[col].mean()
                results_dict['平均'][col]['全体'] = '{:g}'.format(total_mean) if pd.notnull(total_mean) else '-'
                if pd.notnull(total_mean) and pd.notnull(max_val) and max_val != 0:
                    total_score = (total_mean / max_val) * 100
                    results_dict['100点換算'][col]['全体'] = '{:g}'.format(total_score)
                else:
                    results_dict['100点換算'][col]['全体'] = '-'
                
                # 属性値ごとのデータを計算
                for value in df[attribute].unique():
                    subset = df[df[attribute] == value]
                    mean_val = subset[col].mean()
                    
                    # 平均値の格納
                    results_dict['平均'][col][value] = '{:g}'.format(mean_val) if pd.notnull(mean_val) else '-'
                    
                    # 100点換算値の格納
                    if pd.notnull(mean_val) and pd.notnull(max_val) and max_val != 0:
                        score = (mean_val / max_val) * 100
                        results_dict['100点換算'][col][value] = '{:g}'.format(score)
                    else:
                        results_dict['100点換算'][col][value] = '-'
            
            # DataFrameに変換
            results_mean = pd.DataFrame(results_dict['平均']).T
            results_score = pd.DataFrame(results_dict['100点換算']).T
            
            # 列の順序を調整（全体を最初に配置）
            column_order = ['全体'] + [col for col in results_mean.columns if col != '全体']
            results_mean = results_mean[column_order]
            results_score = results_score[column_order]
            
            # 結果の表示
            st.write("平均値")
            st.dataframe(results_mean)
            st.write("100点換算")
            st.dataframe(results_score)
            return

        st.write("平均値と100点換算")
        st.dataframe(results)

    def _display_multiple_choice_analysis(self, df, attribute, config_manager):
        if attribute == "全体":
            results = pd.DataFrame()
            
            for col in df.columns:
                try:
                    # 数値データと文字列データを適切に処理
                    if pd.api.types.is_numeric_dtype(df[col]):
                        continue  # 数値データはスキップ
                    
                    # 文字列として処理
                    values = df[col].fillna('').astype(str)
                    # カンマを含む値のみを処理（複数回答）
                    if not values.str.contains(',').any():
                        continue
                        
                    values = values.str.split(',').explode()
                    counts = values.value_counts().sort_index()  # 昇順でソート
                    results[col] = counts
                except Exception as e:
                    st.warning(f"列 '{col}' の処理中にエラーが発生しました: {str(e)}")
                    continue
                    
            if not results.empty:
                st.write("回答件数")
                st.dataframe(results)
            else:
                st.info("複数回答の質問が見つかりませんでした。")
        else:
            # マルチインデックスを使用した結果格納用のリスト
            multi_index_data = []
            
            for col in df.columns:
                try:
                    # 数値データと文字列データを適切に処理
                    if pd.api.types.is_numeric_dtype(df[col]):
                        continue  # 数値データはスキップ
                    
                    # 文字列として処理
                    values = df[col].fillna('').astype(str)
                    # カンマを含む値のみを処理（複数回答）
                    if not values.str.contains(',').any():
                        continue
                    
                    # 属性値ごとに集計
                    for value in df[attribute].unique():
                        subset = df[df[attribute] == value]
                        subset_values = subset[col].fillna('').astype(str).str.split(',').explode()
                        counts = subset_values.value_counts().sort_index()  # 昇順でソート
                        
                        # 各回答オプションについて結果を格納
                        for answer, count in counts.items():
                            multi_index_data.append({
                                '質問': col,
                                '属性値': value,
                                '回答': answer,
                                '件数': count
                            })
                except Exception as e:
                    st.warning(f"列 '{col}' の処理中にエラーが発生しました: {str(e)}")
                    continue
            
            if multi_index_data:
                # DataFrameの作成とピボット
                results_df = pd.DataFrame(multi_index_data)
                pivot_results = results_df.pivot_table(
                    index=['質問', '回答'],
                    columns='属性値',
                    values='件数',
                    fill_value=0
                )
                
                st.write("回答件数（属性別）")
                st.dataframe(pivot_results)
            else:
                st.info("複数回答の質問が見つかりませんでした。")

    def display_dashboard(self, dfs, config_manager):
        if not dfs:
            st.info("データを読み込んでください。")
            return
            
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

        df = dfs[selected_year_idx]

        # Heatmap
        st.subheader("ヒートマップ")
        metric = st.radio("指標:", ["平均値", "100点換算"])
        
        numeric_columns = df.select_dtypes(include=['number']).columns
        if not numeric_columns.empty:
            data = df[numeric_columns].corr()
            
            fig = go.Figure(data=go.Heatmap(
                z=data,
                x=data.columns,
                y=data.columns,
                colorscale='RdBu'
            ))
            st.plotly_chart(fig)
        else:
            st.info("数値データが見つかりませんでした。")

        # Scatter plot
        if len(numeric_columns) >= 2:
            st.subheader("相関散布図")
            x_axis = st.selectbox("X軸:", numeric_columns)
            y_axis = st.selectbox("Y軸:", numeric_columns)
            
            fig = px.scatter(df, x=x_axis, y=y_axis)
            st.plotly_chart(fig)

        # Bar chart for multiple choice questions
        st.subheader("複数回答の分布")
        multiple_choice_cols = []
        for col in df.columns:
            if not pd.api.types.is_numeric_dtype(df[col]):
                values = df[col].fillna('').astype(str)
                if values.str.contains(',').any():
                    multiple_choice_cols.append(col)
        
        if multiple_choice_cols:
            selected_col = st.selectbox("質問を選択:", multiple_choice_cols)
            values = df[selected_col].fillna('').astype(str).str.split(',').explode()
            counts = values.value_counts()
            
            fig = px.bar(x=counts.index, y=counts.values)
            st.plotly_chart(fig)
        else:
            st.info("複数回答の質問が見つかりませんでした。")
