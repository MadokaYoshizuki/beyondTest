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
        results = pd.DataFrame()
        
        if attribute == "全体":
            for col in df.columns:
                if pd.api.types.is_numeric_dtype(df[col]):
                    mean_val = df[col].mean()
                    max_val = df[col].max()
                    results.loc[col, "平均"] = '{:g}'.format(mean_val) if pd.notnull(mean_val) else '-'
                    results.loc[col, "100点換算"] = '{:g}'.format((mean_val / max_val) * 100) if pd.notnull(mean_val) and pd.notnull(max_val) and max_val != 0 else '-'
        else:
            for value in df[attribute].unique():
                subset = df[df[attribute] == value]
                for col in df.columns:
                    if pd.api.types.is_numeric_dtype(df[col]):
                        mean_val = subset[col].mean()
                        max_val = subset[col].max()
                        results.loc[f"{col} ({value})", "平均"] = '{:g}'.format(mean_val) if pd.notnull(mean_val) else '-'
                        results.loc[f"{col} ({value})", "100点換算"] = '{:g}'.format((mean_val / max_val) * 100) if pd.notnull(mean_val) and pd.notnull(max_val) and max_val != 0 else '-'

        st.write("平均値と100点換算")
        st.dataframe(results)

    def _display_multiple_choice_analysis(self, df, attribute, config_manager):
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
                
                if attribute == "全体":
                    counts = values.value_counts()
                    results[col] = counts
                else:
                    for value in df[attribute].unique():
                        subset = df[df[attribute] == value]
                        subset_values = subset[col].fillna('').astype(str).str.split(',').explode()
                        counts = subset_values.value_counts()
                        results[f"{col} ({value})"] = counts
            except Exception as e:
                st.warning(f"列 '{col}' の処理中にエラーが発生しました: {str(e)}")
                continue

        if not results.empty:
            st.write("回答件数")
            st.dataframe(results)
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
