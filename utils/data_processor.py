import pandas as pd
import numpy as np
import streamlit as st

class DataProcessor:
    def __init__(self):
        self.dfs = []
        self.dates = []

    def load_data(self, files, dates):
        self.dfs = []
        self.dates = dates
        first_df = None
        structure_mismatch = False
        
        for i, file in enumerate(files):
            try:
                df = pd.read_csv(file, encoding='utf-8-sig')
                
                if i == 0:
                    first_df = df
                    first_columns = set(df.columns)
                else:
                    current_columns = set(df.columns)
                    missing_columns = first_columns - current_columns
                    extra_columns = current_columns - first_columns
                    
                    if missing_columns or extra_columns:
                        st.error(f"エラー: {i+1}回目のデータ構成が1回目と異なります。")
                        if missing_columns:
                            st.error(f"欠けている列: {', '.join(missing_columns)}")
                        if extra_columns:
                            st.error(f"追加の列: {', '.join(extra_columns)}")
                        structure_mismatch = True
                        break
                    
                    for col in df.columns:
                        if col in first_df.columns:
                            current_type = self.get_answer_types(pd.DataFrame({col: df[col]}))[col]
                            first_type = self.get_answer_types(pd.DataFrame({col: first_df[col]}))[col]
                            if current_type != first_type:
                                st.error(f"エラー: {col}の回答タイプが一致しません。{i+1}回目: {current_type}, 1回目: {first_type}")
                                structure_mismatch = True
                                break
                
                if not structure_mismatch:
                    self.dfs.append(df)
                
            except Exception as e:
                st.error(f"{i+1}回目のデータ読み込み中にエラーが発生しました: {str(e)}")
                structure_mismatch = True
                break
        
        # 構造の不一致がある場合は全てのデータをクリア
        if structure_mismatch:
            self.dfs = []
            self.dates = []
            st.error("データ構成の不一致が検出されたため、処理を中止します。")

    def get_statistics(self, df):
        numeric_df = df.select_dtypes(include=['number'])
        if numeric_df.empty:
            return pd.DataFrame()
        return numeric_df.describe()

    def get_answer_types(self, df):
        answer_types = {}
        
        for column in df.columns:
            values = df[column].dropna()
            if len(values) == 0:
                answer_types[column] = "データなし"
                continue
            
            # 数値判定（優先順位最高）
            try:
                numeric_values = pd.to_numeric(values, errors='raise')
                
                # 整数/小数の判定を明確に
                if numeric_values.dtype == 'int64' or all(numeric_values.apply(lambda x: float(x).is_integer())):
                    answer_types[column] = "数値回答（整数）"
                else:
                    answer_types[column] = "数値回答（小数）"
                continue
            except (ValueError, TypeError):
                # 数値変換に失敗した場合、他の判定に進む
                pass
            
            # 複数回答（数値）のチェック
            try:
                # カンマで区切られた数値のパターン
                if all(values.astype(str).str.match(r'^\s*\d+(?:\s*,\s*\d+)*\s*$')):
                    answer_types[column] = "数値回答（複数回答）"
                    continue
            except (ValueError, TypeError, AttributeError):
                pass
            
            # 複数回答（テキスト）のチェック
            if values.astype(str).str.contains(',').any():
                answer_types[column] = "テキスト回答（複数回答）"
                continue
            
            # 単一テキスト回答
            answer_types[column] = "テキスト回答（単一）"
        
        return answer_types

    def calculate_statistics(self, df, column, group_by=None):
        if group_by is None:
            return {
                'mean': df[column].mean(),
                'count': df[column].count(),
                'percentage': df[column].value_counts(normalize=True) * 100
            }
        else:
            return df.groupby(group_by)[column].agg(['mean', 'count'])
