import json
import os

class ConfigManager:
    def __init__(self):
        self.config_file = "config.json"
        self.config = self.load_config()

    def load_config(self):
        if os.path.exists(self.config_file):
            with open(self.config_file, 'r') as f:
                return json.load(f)
        return {
            'column_names': {},
            'attributes': [],
            'question_groups': {},
            'value_mappings': {},
            'value_groups': {},
            'importance_satisfaction_pairs': {}  # 重要度と満足度の対応関係を保存
        }

    def save_config(self):
        with open(self.config_file, 'w') as f:
            json.dump(self.config, f, indent=4)

    def save_column_mapping(self, mapping):
        self.config['column_names'] = mapping
        self.save_config()

    def save_attributes(self, attributes):
        self.config['attributes'] = attributes
        self.save_config()

    def save_question_group(self, group_name, questions):
        if 'question_groups' not in self.config:
            self.config['question_groups'] = {}
        self.config['question_groups'][group_name] = questions
        self.save_config()

    def save_value_mapping(self, column, mapping):
        if 'value_mappings' not in self.config:
            self.config['value_mappings'] = {}
        self.config['value_mappings'][column] = mapping
        self.save_config()

    def save_value_groups(self, column, groups):
        if 'value_groups' not in self.config:
            self.config['value_groups'] = {}
        self.config['value_groups'][column] = groups
    def save_importance_satisfaction_pairs(self, pairs):
        """重要度と満足度の対応関係を保存する"""
        self.config['importance_satisfaction_pairs'] = pairs
        self.save_config()

        self.save_config()
