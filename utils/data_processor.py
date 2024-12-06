import pandas as pd
import numpy as np

class DataProcessor:
    def __init__(self):
        self.dfs = []
        self.dates = []

    def load_data(self, files, dates):
        self.dfs = []
        self.dates = dates
        first_df = None
        
        for i, file in enumerate(files):
            df = pd.read_csv(file, encoding='utf-8-sig')
            
            # 最初のファイルの構造を保存
            if i == 0:
                first_df = df
            else:
                # 構造の比較
                for col in df.columns:
                    if col in first_df.columns:
                        current_type = self.get_answer_types(pd.DataFrame({col: df[col]}))[col]
                        first_type = self.get_answer_types(pd.DataFrame({col: first_df[col]}))[col]
                        if current_type != first_type:
                            st.warning(f"警告: {col}の回答タイプが一致しません。{i+1}回目: {current_type}, 1回目: {first_type}")
            
            self.dfs.append(df)

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
                
            # 数値判定の優先順位を上げる
            try:
                # pd.to_numericを使用して数値変換を試みる
                numeric_values = pd.to_numeric(values, errors='raise')
                if numeric_values.dtype in ['int64', 'float64']:
                    if all(numeric_values.apply(lambda x: float(x).is_integer())):
                        answer_types[column] = "数値回答"
                    else:
                        answer_types[column] = "数値回答（小数）"
                    continue
            except (ValueError, TypeError):
                pass
            
            # 複数回答（数値）のチェック
            try:
                if all(values.astype(str).str.match(r'^\d+(?:,\d+)*$')):
                    answer_types[column] = "数値回答（複数回答）"
                    continue
            except (ValueError, TypeError, AttributeError):
                pass
            
            # テキスト回答として処理
            answer_types[column] = "テキスト回答"
        
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
