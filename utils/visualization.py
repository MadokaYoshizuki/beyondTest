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
        # Average and 100-point conversion
        results = pd.DataFrame()
        
        if attribute == "全体":
            for col in df.columns:
                if pd.api.types.is_numeric_dtype(df[col]):
                    results.loc[col, "平均"] = df[col].mean()
                    results.loc[col, "100点換算"] = (df[col].mean() / df[col].max()) * 100
        else:
            for value in df[attribute].unique():
                subset = df[df[attribute] == value]
                for col in df.columns:
                    if pd.api.types.is_numeric_dtype(df[col]):
                        results.loc[f"{col} ({value})", "平均"] = subset[col].mean()
                        results.loc[f"{col} ({value})", "100点換算"] = (subset[col].mean() / subset[col].max()) * 100

        st.write("平均値と100点換算")
        st.dataframe(results)

    def _display_multiple_choice_analysis(self, df, attribute, config_manager):
        results = pd.DataFrame()
        
        for col in df.columns:
            values = df[col].str.split(',').explode()
            if attribute == "全体":
                counts = values.value_counts()
                results[col] = counts
            else:
                for value in df[attribute].unique():
                    subset = df[df[attribute] == value]
                    subset_values = subset[col].str.split(',').explode()
                    counts = subset_values.value_counts()
                    results[f"{col} ({value})"] = counts

        st.write("回答件数")
        st.dataframe(results)

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
        data = df[numeric_columns].corr()
        
        fig = go.Figure(data=go.Heatmap(
            z=data,
            x=data.columns,
            y=data.columns,
            colorscale='RdBu'
        ))
        st.plotly_chart(fig)

        # Scatter plot
        st.subheader("相関散布図")
        x_axis = st.selectbox("X軸:", numeric_columns)
        y_axis = st.selectbox("Y軸:", numeric_columns)
        
        fig = px.scatter(df, x=x_axis, y=y_axis)
        st.plotly_chart(fig)

        # Bar chart for multiple choice questions
        st.subheader("複数回答の分布")
        multiple_choice_cols = [col for col in df.columns if ',' in str(df[col].iloc[0])]
        
        if multiple_choice_cols:
            selected_col = st.selectbox("質問を選択:", multiple_choice_cols)
            values = df[selected_col].str.split(',').explode()
            counts = values.value_counts()
            
            fig = px.bar(x=counts.index, y=counts.values)
            st.plotly_chart(fig)
