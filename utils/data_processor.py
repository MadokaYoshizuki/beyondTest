import pandas as pd
import numpy as np

class DataProcessor:
    def __init__(self):
        self.dfs = []
        self.dates = []

    def load_data(self, files, dates):
        self.dfs = []
        self.dates = dates
        
        for file in files:
            df = pd.read_csv(file)
            self.dfs.append(df)

    def get_statistics(self, df):
        return df.describe()

    def get_answer_types(self, df):
        answer_types = {}
        
        for column in df.columns:
            values = df[column].dropna()
            
            # Check if all values are numeric
            try:
                values = values.astype(float)
                if all(values.apply(lambda x: float(x).is_integer())):
                    answer_types[column] = "数値回答"
                else:
                    answer_types[column] = "テキスト回答"
            except:
                # Check for multiple numeric values separated by comma
                if all(values.str.match(r'^\d+(?:,\d+)*$')):
                    answer_types[column] = "数値回答（複数回答）"
                else:
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
