import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd

class Visualizer:
    def _save_to_excel(self, data_dict, filename):
        excel_path = f"{filename}.xlsx"
        
        with pd.ExcelWriter(excel_path, engine='openpyxl') as writer:
            if isinstance(data_dict, dict):
                for sheet_name, df in data_dict.items():
                    # インデックスと列名のみの単純な表として出力
                    df.to_excel(
                        writer,
                        sheet_name=sheet_name,
                        index=True,
                        header=True
                    )
            else:
                data_dict.to_excel(
                    writer,
                    index=True,
                    header=True
                )
        
        # ダウンロードボタンを表示
        with open(excel_path, 'rb') as f:
            st.download_button(
                label="Excelファイルをダウンロード",
                data=f,
                file_name=excel_path,
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        
        # 一時ファイルを削除
        import os
        os.remove(excel_path)

    def display_numerical_tables(self, dfs, config_manager):
        if not dfs:
            st.info("データを読み込んでください。")
            return
            
        year_options = [f"{i+1}回目のデータ" for i in range(len(dfs))]
        selected_year_idx = st.selectbox(
            "データを選択:",
            range(len(dfs)),
            format_func=lambda x: year_options[x]
        )
        
        # 属性の表示名を取得
        column_names = config_manager.config.get('column_names', {})
        attributes = ["全体"] + [
            attr for attr in config_manager.config['attributes']
        ]
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
            st.subheader(question_type)
            
            if question_type == "数値回答":
                self._display_numeric_analysis(df, selected_attribute, config_manager)
            else:
                self._display_multiple_choice_analysis(df, selected_attribute, config_manager)

    def _display_numeric_analysis(self, df, attribute, config_manager):
        # 列名のマッピングを取得
        column_names = config_manager.config.get('column_names', {})
        
        if attribute == "全体":
            results = pd.DataFrame()
            for col in df.columns:
                if pd.api.types.is_numeric_dtype(df[col]):
                    mean_val = df[col].mean()
                    max_val = df[col].max()
                    display_name = column_names.get(col, col)
                    results.loc[display_name, "平均"] = '{:g}'.format(mean_val) if pd.notnull(mean_val) else '-'
                    results.loc[display_name, "100点換算"] = '{:g}'.format((mean_val / max_val) * 100) if pd.notnull(mean_val) and pd.notnull(max_val) and max_val != 0 else '-'
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
            
            # 結果の表示と保存
            if attribute != "全体":
                # 属性別表示時のみ別シートとして出力
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
                # 全体表示時は1つの表で表示
                combined_results = pd.DataFrame()
                combined_results["平均"] = results["平均"]
                combined_results["100点換算"] = results["100点換算"]
                st.write("平均値と100点換算")
                st.dataframe(combined_results)
                self._save_to_excel(combined_results, "numeric_analysis_all")

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
                subset_df = df[df[attribute] == attr_value]
                results = pd.DataFrame()
                
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
                else:
                    st.info(f"【{attr_value}】の複数回答の質問が見つかりませんでした。")
            
            # すべての結果を1つのExcelファイルに保存
            if all_results:
                self._save_to_excel(all_results, f"multiple_choice_analysis_{attribute}")

    def display_dashboard(self, dfs, config_manager):
        if not dfs:
            st.info("データを読み込んでください。")
            return
            
        # 列名のマッピングを取得
        column_names = config_manager.config.get('column_names', {})
            
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
            
            # 列名を日本語表示に変換
            display_columns = [column_names.get(col, col) for col in data.columns]
            
            fig = go.Figure(data=go.Heatmap(
                z=data,
                x=display_columns,
                y=display_columns,
                colorscale='RdBu'
            ))
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

        # Bar chart for multiple choice questions
        st.subheader("複数回答の分布")
        column_names = config_manager.config.get('column_names', {})
        multiple_choice_cols = []
        multiple_choice_display_names = {}
        
        for col in df.columns:
            if not pd.api.types.is_numeric_dtype(df[col]):
                values = df[col].fillna('').astype(str)
                if values.str.contains(',').any():
                    multiple_choice_cols.append(col)
                    multiple_choice_display_names[col] = column_names.get(col, col)
        
        if multiple_choice_cols:
            selected_col = st.selectbox(
                "質問を選択:",
                multiple_choice_cols,
                format_func=lambda x: multiple_choice_display_names[x]
            )
            values = df[selected_col].fillna('').astype(str).str.split(',').explode()
            counts = values.value_counts()
            
            fig = px.bar(
                x=counts.index,
                y=counts.values,
                title=f"{multiple_choice_display_names[selected_col]}の回答分布"
            )
            st.plotly_chart(fig)
        else:
            st.info("複数回答の質問が見つかりませんでした。")
