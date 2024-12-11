import streamlit as st
import pandas as pd
import json
import os
from datetime import datetime
from utils.data_processor import DataProcessor
from utils.config_manager import ConfigManager
from utils.visualization import Visualizer
from utils.pdf_generator import PDFGenerator

st.set_page_config(layout="wide", page_title="意識調査データ分析ダッシュボード")

def main():
    # Initialize session state
    if 'data_processor' not in st.session_state:
        st.session_state.data_processor = DataProcessor()
    if 'config_manager' not in st.session_state:
        st.session_state.config_manager = ConfigManager()
    if 'visualizer' not in st.session_state:
        st.session_state.visualizer = Visualizer()
    if 'current_menu' not in st.session_state:
        st.session_state.current_menu = "1.データアップロード"

    # メインメニューの追加
    menu_options = [
        "1.データアップロード",
        "2.データ分析",
        "3.設定",
        "4.集計",
        "5.可視化",
        "6.PDF出力"
    ]

    # サイドバーにタイトルを追加
    st.sidebar.title("意識調査データ分析ダッシュボード")
    st.sidebar.markdown("---")  # 区切り線を追加
    st.sidebar.markdown("### メニュー")
    st.session_state.current_menu = st.sidebar.radio("", menu_options)

    # 各セクションの条件分岐
    if st.session_state.current_menu == "1.データアップロード":
        st.markdown("## 1. データアップロード")
        st.markdown("##### ※ 時期の古いものから順にしてください")
        st.markdown("---")
        
        # セッション状態の初期化
        if 'upload_status' not in st.session_state:
            st.session_state.upload_status = [False] * 3
        
        # 3列に分割してデータアップロード
        cols = st.columns(3)
        dates = []
        files = []
        
        for i in range(3):
            with cols[i]:
                st.subheader(f"{i+1}回目のデータ")
                
                # 実施時期の入力
                date = st.text_input(
                    f"実施時期",
                    key=f"date_{i}",
                    help="例: 2023年度"
                )
                dates.append(date)
                
                # ファイルのアップロード
                uploaded_file = st.file_uploader(
                    "CSVファイルを選択", 
                    type="csv",
                    key=f"file_{i}",
                    help="CSVファイルをアップロードしてください"
                )
                files.append(uploaded_file)
                
                # アップロード状態の更新と表示
                st.session_state.upload_status[i] = bool(date and uploaded_file)
                
                if st.session_state.upload_status[i]:
                    st.success(f"✓ {date}のデータがアップロードされました")
                else:
                    if date and not uploaded_file:
                        st.warning("CSVファイルを選択してください")
                    elif uploaded_file and not date:
                        st.warning("実施時期を入力してください")

        if any(files):  # いずれかのファイルがアップロードされている場合
            if st.button("データを読み込む"):
                valid_files = []
                valid_dates = []
                
                # 有効なファイルと日付のペアのみを処理
                for i, (file, date) in enumerate(zip(files, dates)):
                    if file and date:
                        valid_files.append(file)
                        valid_dates.append(date)
                        st.write(f"{i+1}回目: {date}のデータを読み込みます")
                
                if valid_files:
                    st.session_state.data_processor.load_data(valid_files, valid_dates)
                else:
                    st.warning("有効なデータがありません。日付とファイルの両方を指定してください。")

    elif st.session_state.current_menu == "2.データ分析":
        st.markdown("## 2. データ分析")
        st.markdown("---")
        
        # Display raw data and analysis
        if hasattr(st.session_state.data_processor, 'dfs'):
            for i, df in enumerate(st.session_state.data_processor.dfs):
                with st.expander(f"データセット {i+1} ({st.session_state.data_processor.dates[i]}) の分析"):
                    st.write("基本統計量:")
                    stats = st.session_state.data_processor.get_statistics(df)
                    
                    def highlight_missing(x):
                        if x.name == 'count':
                            return ['background-color: pink' if pd.isna(v) else '' for v in x]
                        return ['' for _ in x]
                        
                    formatted_stats = stats.apply(lambda x: ['{:g}'.format(v) if isinstance(v, float) else str(v) for v in x])
                    st.dataframe(formatted_stats.style.apply(highlight_missing, axis=1))
                    
                    st.write("回答タイプ:")
                    answer_types = st.session_state.data_processor.get_answer_types(df)
                    st.write(answer_types)
        else:
            st.info("データを読み込んでください。")

    elif st.session_state.current_menu == "3.設定":
        st.markdown("## 3. 設定")
        st.markdown("---")
        
        # Column mapping with grid layout
        with st.expander("列名の設定"):
            config = st.session_state.config_manager.load_config()
            new_column_names = {}
            
            if hasattr(st.session_state.data_processor, 'dfs') and st.session_state.data_processor.dfs:
                columns = st.session_state.data_processor.dfs[0].columns
                col_count = len(columns)
                cols_per_row = 3
                
                for i in range(0, col_count, cols_per_row):
                    cols = st.columns(cols_per_row)
                    for j in range(cols_per_row):
                        col_idx = i + j
                        if col_idx < col_count:
                            col = columns[col_idx]
                            with cols[j]:
                                new_name = st.text_input(
                                    f"列{col_idx + 1}",
                                    value=config.get('column_names', {}).get(col, col),
                                    help=f"元の列名: {col}"
                                )
                                new_column_names[col] = new_name
                
                col1, col2, col3 = st.columns([1, 1, 1])
                with col2:
                    if st.button("列名を保存", use_container_width=True):
                        st.session_state.config_manager.save_column_mapping(new_column_names)
                        st.success("列名の設定を保存しました")
            else:
                st.info("データを読み込むと、列名の設定が可能になります。")

        # Attribute selection
        with st.expander("属性項目の設定"):
            if hasattr(st.session_state.data_processor, 'dfs') and st.session_state.data_processor.dfs:
                # 現在の属性設定を取得
                current_attributes = st.session_state.config_manager.config.get('attributes', [])
                column_names = st.session_state.config_manager.config.get('column_names', {})
                
                # 属性の選択
                attributes = st.multiselect(
                    "属性として扱う列を選択:",
                    st.session_state.data_processor.dfs[0].columns,
                    default=current_attributes,
                    format_func=lambda x: column_names.get(x, x)
                )
                
                if st.button("属性を保存"):
                    st.session_state.config_manager.save_attributes(attributes)
                    st.success("属性の設定を保存しました")
                    st.rerun()
            else:
                st.info("データを読み込むと、属性の設定が可能になります。")

        # Question grouping
        with st.expander("質問グループの設定"):
            if hasattr(st.session_state.data_processor, 'dfs') and st.session_state.data_processor.dfs:
                # 列名のマッピングを取得
                column_names = st.session_state.config_manager.config.get('column_names', {})
                
                # 既存の質問グループの一覧表示
                if question_groups := st.session_state.config_manager.config.get('question_groups', {}):
                    st.write("登録済み質問グループ一覧")
                    
                    # グループごとに1行で表示
                    selected_groups = []
                    for group_name, questions in question_groups.items():
                        col1, col2, col3 = st.columns([0.1, 0.7, 0.2])
                        with col1:
                            if st.checkbox("", key=f"delete_{group_name}"):
                                selected_groups.append(group_name)
                        with col2:
                            st.write(f"📁 {group_name} ({len(questions)}問)")
                            st.caption(f"質問項目: {', '.join([column_names.get(q, q) for q in questions])}")
                    
                    # 削除機能
                    if selected_groups:
                        if st.button("選択したグループを削除"):
                            for group_name in selected_groups:
                                del st.session_state.config_manager.config['question_groups'][group_name]
                            st.session_state.config_manager.save_config()
                            st.success(f"選択したグループを削除しました")
                            st.rerun()
                
                # 新規グループの追加
                st.write("新規グループの追加")
                group_name = st.text_input("グループ名:", key="question_group_name")
                questions = st.multiselect(
                    "グループに含める質問:",
                    [col for col in st.session_state.data_processor.dfs[0].columns 
                     if pd.api.types.is_numeric_dtype(st.session_state.data_processor.dfs[0][col]) and 
                     not st.session_state.data_processor.dfs[0][col].astype(str).str.contains(',').any()],
                    format_func=lambda x: column_names.get(x, x),
                    key="question_group_items"
                )
                if st.button("グループを保存", key="save_question_group"):
                    if group_name and questions:
                        try:
                            st.session_state.config_manager.save_question_group(group_name, questions)
                            st.success("質問グループを保存しました")
                            # セッション状態をクリア
                            if 'question_group_name' in st.session_state:
                                st.session_state.pop('question_group_name')
                            if 'question_group_items' in st.session_state:
                                st.session_state.pop('question_group_items')
                            # 保存後にページを再読み込み
                            st.rerun()
                        except Exception as e:
                            st.error(f"グループの保存中にエラーが発生しました: {str(e)}")
                    else:
                        st.warning("グループ名と質問項目を入力してください")
            else:
                st.info("データを読み込むと、質問グループの設定が可能になります。")

        # Value grouping
        # 満点設定
        with st.expander("満点設定"):
            if hasattr(st.session_state.data_processor, 'dfs') and st.session_state.data_processor.dfs:
                # 列名のマッピングを取得
                column_names = st.session_state.config_manager.config.get('column_names', {})
                max_scores = st.session_state.config_manager.config.get('max_scores', {})
                
                st.write("数値回答の満点設定")
                
                # 数値列のみを対象とする
                numeric_columns = [col for col in st.session_state.data_processor.dfs[0].columns 
                                 if pd.api.types.is_numeric_dtype(st.session_state.data_processor.dfs[0][col])]
                
                # 各数値列の満点を設定
                new_max_scores = {}
                for col in numeric_columns:
                    display_name = column_names.get(col, col)
                    current_max = max_scores.get(col, 5)  # デフォルト値は5
                    new_max = st.number_input(
                        f"{display_name}の満点:",
                        min_value=1,
                        value=int(current_max),
                        key=f"max_score_{col}"
                    )
                    new_max_scores[col] = new_max
                
                if st.button("満点設定を保存"):
                    # データの最大値チェック
                    df = st.session_state.data_processor.dfs[0]  # データフレームの参照を追加
                    invalid_settings = []
                    for col, max_score in new_max_scores.items():
                        data_max = float(df[col].max())
                        if max_score < data_max:
                            display_name = column_names.get(col, col)
                            invalid_settings.append(f"{display_name}（設定値: {max_score}, データの最大値: {data_max}）")
                    
                    if invalid_settings:
                        st.error("以下の項目で設定された満点がデータの最大値より小さいため保存できません：\n" + "\n".join(invalid_settings))
                    else:
                        st.session_state.config_manager.config['max_scores'] = new_max_scores
                        st.session_state.config_manager.save_config()
                        st.success("満点設定を保存しました")
            else:
                st.info("データを読み込むと、満点の設定が可能になります。")

        # 重要度-満足度分析の設定
        with st.expander("重要度-満足度分析の設定"):
            if hasattr(st.session_state.data_processor, 'dfs') and st.session_state.data_processor.dfs:
                # 現在の設定を取得
                current_pairs = st.session_state.config_manager.config.get('importance_satisfaction_pairs', {})
                column_names = st.session_state.config_manager.config.get('column_names', {})
                
                st.write("重要度と満足度の対応関係を設定")
                
                # 数値列のみを対象とする
                numeric_columns = [col for col in st.session_state.data_processor.dfs[0].columns 
                               if pd.api.types.is_numeric_dtype(st.session_state.data_processor.dfs[0][col])]
                
                # 既存のペアの表示と削除機能
                if current_pairs:
                    st.write("登録済みの対応関係")
                    selected_pairs = []
                    for pair_name, pair_data in current_pairs.items():
                        col1, col2, col3 = st.columns([0.1, 0.7, 0.2])
                        with col1:
                            if st.checkbox("", key=f"delete_pair_{pair_name}"):
                                selected_pairs.append(pair_name)
                        with col2:
                            imp_name = column_names.get(pair_data['importance'], pair_data['importance'])
                            sat_name = column_names.get(pair_data['satisfaction'], pair_data['satisfaction'])
                            st.write(f"📊 {pair_name}")
                            st.caption(f"重要度: {imp_name} → 満足度: {sat_name}")
                    
                    if selected_pairs:
                        if st.button("選択した対応関係を削除"):
                            for pair_name in selected_pairs:
                                st.session_state.config_manager.remove_importance_satisfaction_pair(pair_name)
                            st.success("選択した対応関係を削除しました")
                            st.rerun()
                
                # 新規ペアの追加
                st.write("新規対応関係の追加")
                
                # ペアの名前入力
                pair_name = st.text_input(
                    "対応関係の名前",
                    help="例：人間関係、キャリアアップ環境など",
                    key="pair_name"
                )
                
                col1, col2 = st.columns(2)
                with col1:
                    importance = st.selectbox(
                        "重要度の質問:",
                        numeric_columns,
                        format_func=lambda x: column_names.get(x, x),
                        key="importance_question"
                    )
                with col2:
                    satisfaction = st.selectbox(
                        "満足度の質問:",
                        numeric_columns,
                        format_func=lambda x: column_names.get(x, x),
                        key="satisfaction_question"
                    )
                
                if st.button("対応関係を保存"):
                    if pair_name and importance and satisfaction:
                        if importance != satisfaction:
                            if pair_name in current_pairs:
                                st.error(f"'{pair_name}' は既に使用されています。別の名前を指定してください。")
                            else:
                                st.session_state.config_manager.save_importance_satisfaction_pairs(
                                    pair_name, importance, satisfaction
                                )
                                st.success("対応関係を保存しました")
                                st.rerun()
                        else:
                            st.error("重要度と満足度には異なる質問を選択してください")
                    else:
                        st.warning("名前、重要度、満足度の質問をすべて入力してください")
            else:
                st.info("データを読み込むと、重要度-満足度分析の設定が可能になります。")

        with st.expander("値グループ化の設定"):
            if hasattr(st.session_state.data_processor, 'dfs') and st.session_state.data_processor.dfs:
                # 列名のマッピングを取得
                column_names = st.session_state.config_manager.config.get('column_names', {})
                
                # 既存の値グループの一覧表示
                if value_groups := st.session_state.config_manager.config.get('value_groups', {}):
                    st.write("登録済み値グループ一覧")
                    
                    # グループごとに1行で表示
                    selected_value_groups = []
                    for column, groups in value_groups.items():
                        st.write(f"📊 {column_names.get(column, column)}")
                        for range_str, label in groups.items():
                            col1, col2, col3 = st.columns([0.1, 0.7, 0.2])
                            with col1:
                                if st.checkbox("", key=f"delete_value_group_{column}_{range_str}"):
                                    selected_value_groups.append((column, range_str))
                            with col2:
                                st.caption(f"{range_str}: {label}")
                    
                    # 削除機能
                    if selected_value_groups:
                        if st.button("選択した値グループを削除"):
                            for column, range_str in selected_value_groups:
                                if column in st.session_state.config_manager.config['value_groups']:
                                    del st.session_state.config_manager.config['value_groups'][column][range_str]
                                    if not st.session_state.config_manager.config['value_groups'][column]:
                                        del st.session_state.config_manager.config['value_groups'][column]
                            st.session_state.config_manager.save_config()
                            st.success(f"選択した値グループを削除しました")
                            st.rerun()

                # 新規値グループの追加
                st.write("新規値グループの追加")
                
                # 数値列の選択（複数選択可能）
                numeric_columns = [col for col in st.session_state.data_processor.dfs[0].columns 
                                if pd.api.types.is_numeric_dtype(st.session_state.data_processor.dfs[0][col])]
                selected_columns = st.multiselect(
                    "対象の列を選択:",
                    numeric_columns,
                    format_func=lambda x: column_names.get(x, x),
                    key="value_group_columns"
                )

                if selected_columns:
                    # 選択された列の型チェック
                    df = st.session_state.data_processor.dfs[0]
                    is_integer_type = all(
                        df[col].dtype in ['int64'] or df[col].apply(lambda x: float(x).is_integer()).all()
                        for col in selected_columns
                    )
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        if is_integer_type:
                            min_value = st.number_input(
                                "最小値:",
                                value=int(min(df[selected_columns].min())),
                                step=1,
                                key="value_group_min"
                            )
                        else:
                            min_value = st.number_input(
                                "最小値:",
                                value=float(min(df[selected_columns].min())),
                                key="value_group_min"
                            )
                    with col2:
                        if is_integer_type:
                            max_value = st.number_input(
                                "最大値:",
                                value=int(max(df[selected_columns].max())),
                                step=1,
                                key="value_group_max"
                            )
                        else:
                            max_value = st.number_input(
                                "最大値:",
                                value=float(max(df[selected_columns].max())),
                                key="value_group_max"
                            )

                    group_label = st.text_input(
                        "グループラベル:",
                        help="例: 低群、中群、高群など",
                        key="value_group_label"
                    )

                    if st.button("値グループを保存", key="save_value_group"):
                        if min_value < max_value and group_label:
                            # データの最小値と最大値を確認
                            data_min = min(df[selected_columns].min())
                            data_max = max(df[selected_columns].max())
                            
                            if min_value < data_min:
                                st.error(f"エラー: 指定された最小値（{min_value}）がデータの最小値（{data_min}）より小さいため保存できません。")
                            elif max_value < data_max:
                                st.error(f"エラー: 指定された最大値（{max_value}）がデータの最大値（{data_max}）より小さいため保存できません。")
                            else:
                                range_str = f"{min_value}-{max_value}"
                                for col in selected_columns:
                                    if 'value_groups' not in st.session_state.config_manager.config:
                                        st.session_state.config_manager.config['value_groups'] = {}
                                    if col not in st.session_state.config_manager.config['value_groups']:
                                        st.session_state.config_manager.config['value_groups'][col] = {}
                                    st.session_state.config_manager.config['value_groups'][col][range_str] = group_label
                                st.session_state.config_manager.save_config()
                                st.success("値グループを保存しました")
                                st.rerun()  # フォームクリアのためにページを再読み込み
                        else:
                            st.warning("最小値、最大値、およびグループラベルを正しく入力してください")
            else:
                st.info("データを読み込むと、値グループ化の設定が可能になります。")

    elif st.session_state.current_menu == "4.集計":
        st.markdown("## 4. 集計")
        st.markdown("---")
        st.session_state.visualizer.display_numerical_tables(
            st.session_state.data_processor.dfs,
            st.session_state.config_manager
        )

    elif st.session_state.current_menu == "5.可視化":
        st.markdown("## 5. 可視化")
        st.markdown("---")
        st.session_state.visualizer.display_dashboard(
            st.session_state.data_processor.dfs,
            st.session_state.config_manager
        )

    elif st.session_state.current_menu == "6.PDF出力":
        st.markdown("## 6. PDF出力")
        st.markdown("---")
        
        # タブの作成
        tab1, tab2 = st.tabs(["📋 帳票テンプレート管理", "⚙️ フォント設定"])

        # 帳票テンプレート管理タブ
        with tab1:
            st.markdown("### 帳票テンプレート管理")
            
            try:
                # テンプレート作成フォーム
                with st.form("template_creation_form"):
                    # 基本情報
                    template_name = st.text_input("テンプレート名", help="例: 基本分析レポート")
                    template_description = st.text_area("説明", help="レポートの概要や用途を記入してください")
                    
                    # データセット選択
                    if hasattr(st.session_state.data_processor, 'dfs') and st.session_state.data_processor.dfs:
                        dataset_options = [f"データセット {i+1}" for i in range(len(st.session_state.data_processor.dfs))]
                        selected_dataset = st.selectbox("分析対象のデータセット", dataset_options)
                    
                    # 絞り込み条件
                    st.subheader("データ絞り込み条件")
                    filters = {}
                    if hasattr(st.session_state.data_processor, 'dfs') and st.session_state.data_processor.dfs:
                        df = st.session_state.data_processor.dfs[0]
                        attributes = st.session_state.config_manager.config.get('attributes', [])
                        
                        for attr in attributes:
                            unique_values = df[attr].unique().tolist()
                            selected_values = st.multiselect(
                                f"{attr}による絞り込み:",
                                unique_values,
                                default=unique_values,
                                help=f"{attr}の値で絞り込む場合は選択してください"
                            )
                            if selected_values and len(selected_values) < len(unique_values):
                                filters[attr] = selected_values
                    
                    # 出力セクション設定
                    st.subheader("出力セクション設定")
                    graph_type = st.selectbox(
                        "グラフ種類",
                        ["相関係数ヒートマップ", "回答の分布", "重要度-満足度分析"]
                    )
                    
                    analysis_unit = st.radio(
                        "分析単位",
                        ["質問ごと", "質問グループごと"]
                    )
                    
                    # 保存ボタン
                    submitted = st.form_submit_button("テンプレートを保存")
                    
                    if submitted:
                        if template_name:
                            # テンプレートの保存
                            new_template = {
                                "title": template_name,
                                "description": template_description,
                                "dataset": selected_dataset if 'selected_dataset' in locals() else "データセット 1",
                                "filters": filters,
                                "sections": [
                                    {
                                        "type": graph_type.replace("ヒートマップ", "").replace("分析", ""),
                                        "title": graph_type,
                                        "description": "",
                                        "options": {
                                            "analysis_unit": analysis_unit
                                        }
                                    }
                                ]
                            }
                            
                            # 設定の保存
                            templates = st.session_state.config_manager.config.get('pdf_settings', {}).get('templates', {})
                            templates[template_name] = new_template
                            st.session_state.config_manager.config['pdf_settings']['templates'] = templates
                            st.session_state.config_manager.save_config()
                            st.success("テンプレートを保存しました")
                            st.rerun()
                        else:
                            st.error("テンプレート名を入力してください")

                # 登録済みテンプレート
                st.markdown("### 登録済みテンプレート")
                templates = st.session_state.config_manager.config.get('pdf_settings', {}).get('templates', {})
                
                if templates:
                    st.write("登録済みテンプレート:")
                    for template_name, template_data in templates.items():
                        with st.expander(f"📄 {template_name}: {template_data['title']}", expanded=False):
                            st.write(f"説明: {template_data.get('description', '')}")
                            
                            # フィルター設定の表示
                            if filters := template_data.get('filters', {}):
                                st.write("データ絞り込み条件:")
                                for attr, values in filters.items():
                                    st.write(f"- {attr}: {', '.join(values)}")
                            
                            # セクション一覧
                            st.write("出力内容:")
                            for section in template_data.get('sections', []):
                                st.write(f"- {section['title']}")
                                if description := section.get('description'):
                                    st.caption(description)
                            
                            # PDFプレビューボタン
                            col1, col2 = st.columns([1, 4])
                            with col1:
                                if st.button("PDF出力", key=f"pdf_{template_name}"):
                                    if not hasattr(st.session_state.data_processor, 'dfs') or not st.session_state.data_processor.dfs:
                                        st.error("データが読み込まれていません。先にデータをアップロードしてください。")
                                    else:
                                        st.session_state.pdf_generator = PDFGenerator(st.session_state.config_manager)
                                        try:
                                            output_path = st.session_state.pdf_generator.generate_pdf(
                                                st.session_state.data_processor.dfs,
                                                st.session_state.config_manager,
                                                st.session_state.visualizer,
                                                template_name
                                            )
                                            if output_path and os.path.exists(output_path):
                                                with open(output_path, "rb") as pdf_file:
                                                    st.download_button(
                                                        label="PDFをダウンロード",
                                                        data=pdf_file,
                                                        file_name=f"{template_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf",
                                                        mime="application/pdf"
                                                    )
                                            else:
                                                st.error("PDFの生成に失敗しました")
                                        except Exception as e:
                                            st.error(f"PDF生成中にエラーが発生しました: {str(e)}")
            except Exception as e:
                st.error(f"テンプレート一覧の表示中にエラーが発生しました: {str(e)}")
                
                if templates:
                    st.write("登録済みテンプレート:")
                for template_name, template_data in templates.items():
                    with st.expander(f"📄 {template_name}: {template_data['title']}", expanded=False):
                        st.write(f"説明: {template_data.get('description', '')}")
                        
                        # フィルター設定の表示
                        if filters := template_data.get('filters', {}):
                            st.write("データ絞り込み条件:")
                            for attr, values in filters.items():
                                st.write(f"- {attr}: {', '.join(values)}")
                        
                        # セクション一覧
                        st.write("出力内容:")
                        for section in template_data.get('sections', []):
                            st.write(f"- {section['title']}")
                            if description := section.get('description'):
                                st.caption(description)
                        
                        # PDFプレビューボタン
                        col1, col2 = st.columns([1, 4])
                        with col1:
                            if st.button("PDF出力", key=f"pdf_{template_name}"):
                                st.session_state.pdf_generator = PDFGenerator(st.session_state.config_manager)
                                try:
                                    output_path = st.session_state.pdf_generator.generate_pdf(
                                        st.session_state.data_processor.dfs,
                                        st.session_state.config_manager,
                                        st.session_state.visualizer,
                                        template_name
                                    )
                                    if output_path and os.path.exists(output_path):
                                        with open(output_path, "rb") as pdf_file:
                                            st.download_button(
                                                label="PDFをダウンロード",
                                                data=pdf_file,
                                                file_name=f"{template_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf",
                                                mime="application/pdf"
                                            )
                                    else:
                                        st.error("PDFの生成に失敗しました")
                                except Exception as e:
                                    st.error(f"PDF生成中にエラーが発生しました: {str(e)}")
            
            # 新規テンプレート作成
            st.markdown("### 新規テンプレート作成")
            with st.form("new_template_form"):
                # 基本情報
                template_name = st.text_input("テンプレート名", placeholder="例: 帳票1, 帳票2")
                title = st.text_input("タイトル", placeholder="例: 基本分析レポート")
                description = st.text_area("説明文", placeholder="レポートの概要を入力してください")
                
                # データ絞り込み条件
                st.write("データ絞り込み条件")
                filters = {}
                if hasattr(st.session_state.data_processor, 'dfs') and st.session_state.data_processor.dfs:
                    df = st.session_state.data_processor.dfs[0]
                    attributes = st.session_state.config_manager.config.get('attributes', [])
                    
                    # 存在する属性のみを処理
                    valid_attributes = [attr for attr in attributes if attr in df.columns]
                    
                    if valid_attributes:
                        for attr in valid_attributes:
                            try:
                                unique_values = sorted(df[attr].dropna().unique().tolist())
                                selected_values = st.multiselect(
                                    f"{attr}で絞り込み",
                                    ["全て"] + unique_values,
                                    default=["全て"]
                                )
                                if selected_values and selected_values != ["全て"]:
                                    filters[attr] = selected_values
                            except Exception as e:
                                st.error(f"属性 '{attr}' の処理中にエラーが発生しました: {str(e)}")
                    else:
                        st.info("利用可能な属性がありません。先に属性設定を行ってください。")
                
                # セクション設定
                st.write("出力するセクション")
                sections = []
                
                # 数値表セクション
                if st.checkbox("数値表を含める", value=True):
                    numeric_section = {
                        "type": "数値表",
                        "title": "属性別平均値一覧",
                        "description": st.text_input("数値表の説明", placeholder="数値表の説明を入力してください"),
                        "options": {
                            "show_group_analysis": st.checkbox("グループ分析を表示", value=True),
                            "show_question_analysis": st.checkbox("質問別分析を表示", value=True)
                        }
                    }
                    sections.append(numeric_section)
                
                # 相関分析セクション
                if st.checkbox("相関分析を含める"):
                    correlation_section = {
                        "type": "相関分析",
                        "title": "相関分析",
                        "description": st.text_input("相関分析の説明", placeholder="相関分析の説明を入力してください"),
                        "options": {
                            "mode": st.selectbox(
                                "分析モード",
                                ["質問間の相関", "グループ間の相関"]
                            ),
                            "group": "すべての質問"
                        }
                    }
                    sections.append(correlation_section)
                
                # 重要度-満足度分析セクション
                if st.checkbox("重要度-満足度分析を含める"):
                    is_section = {
                        "type": "重要度満足度",
                        "title": "重要度-満足度分析",
                        "description": st.text_input("重要度-満足度分析の説明", placeholder="重要度-満足度分析の説明を入力してください"),
                        "options": {}
                    }
                    sections.append(is_section)
                
                # 保存ボタン
                if st.form_submit_button("テンプレートを保存"):
                    if template_name and title:
                        if 'pdf_settings' not in st.session_state.config_manager.config:
                            st.session_state.config_manager.config['pdf_settings'] = {'templates': {}}
                        elif 'templates' not in st.session_state.config_manager.config['pdf_settings']:
                            st.session_state.config_manager.config['pdf_settings']['templates'] = {}
                        
                        st.session_state.config_manager.config['pdf_settings']['templates'][template_name] = {
                            "title": title,
                            "description": description,
                            "filters": filters,
                            "sections": sections
                        }
                        st.session_state.config_manager.save_config()
                        st.success("テンプレートを保存しました")
                        st.rerun()
                    else:
                        st.error("テンプレート名とタイトルは必須です")
        
        # フォント設定タブ
        with tab2:
            st.markdown("### 日本語フォントの設定")
            
            # フォントファイルのアップロード
            font_file = st.file_uploader(
                "日本語フォントファイル (.ttc/.ttf) をアップロード:",
                type=['ttc', 'ttf'],
                help="NotoSansCJK、IPAフォント、MSゴシック等の日本語フォントファイルをアップロードしてください。",
                key="font_uploader"
            )
            
            if font_file is not None:
                try:
                    # fontsディレクトリの作成
                    if not os.path.exists('fonts'):
                        os.makedirs('fonts')
                    
                    # フォントファイルの保存
                    font_filename = font_file.name
                    font_path = os.path.join('fonts', font_filename)
                    
                    # 既存のフォントファイルを削除
                    if os.path.exists(font_path):
                        os.remove(font_path)
                    
                    # 新しいフォントファイルを保存
                    with open(font_path, 'wb') as f:
                        f.write(font_file.getvalue())
                    
                    # 設定の更新
                    st.session_state.config_manager.config['pdf_font'] = {
                        'filename': font_filename,
                        'path': font_path
                    }
                    st.session_state.config_manager.save_config()
                    st.success(f"フォントファイル '{font_filename}' を保存しました")
                except Exception as e:
                    st.error(f"フォントファイルの保存中にエラーが発生しました: {str(e)}")
                    if os.path.exists(font_path):
                        os.remove(font_path)
            
            # 現在のフォント状態を確認
            current_font = st.session_state.config_manager.config.get('pdf_font', {})
            if current_font and os.path.exists(current_font.get('path', '')):
                st.info(f"日本語フォント '{current_font['filename']}' が利用可能です")
            else:
                st.warning("日本語フォントがアップロードされていません。PDFの日本語が正しく表示されない可能性があります。")
        
        # PDF設定の編集
        with st.expander("PDF出力設定", expanded=True):
            st.write("出力内容の選択")
            
            # 新規設定の作成
            settings_name = st.text_input("設定名", value="新規設定")
            
            # セクションの選択
            st.write("### セクションの選択")
            
            # 数値表の設定
            if st.checkbox("数値表を含める", value=True):
                st.write("数値表の設定：")
                col1, col2 = st.columns(2)
                with col1:
                    show_group = st.checkbox("グループ分析を表示", value=True)
                with col2:
                    show_question = st.checkbox("質問別分析を表示", value=True)
            
            # 相関分析の設定
            if st.checkbox("相関分析を含める", value=True):
                st.write("相関分析の設定：")
                correlation_mode = st.selectbox(
                    "分析モード",
                    ["質問間の相関", "グループ間の相関"],
                    index=0
                )
                if correlation_mode == "グループ間の相関":
                    correlation_group = st.selectbox(
                        "対象グループ",
                        ["すべての質問"] + list(st.session_state.config_manager.config.get('question_groups', {}).keys())
                    )
                else:
                    correlation_group = "すべての質問"
            
            # 重要度-満足度分析の設定
            include_is = st.checkbox("重要度-満足度分析を含める", value=True)
            
            # 設定の保存ボタン
            if st.button("設定を保存"):
                sections = []
                
                # 数値表のセクション
                if st.session_state.get('show_numeric', True):
                    sections.append({
                        "type": "数値表",
                        "title": "属性別平均値一覧",
                        "options": {
                            "show_group_analysis": show_group,
                            "show_question_analysis": show_question
                        }
                    })
                
                # 相関分析のセクション
                if st.session_state.get('show_correlation', True):
                    sections.append({
                        "type": "相関分析",
                        "title": "質問間の相関分析",
                        "options": {
                            "mode": correlation_mode,
                            "group": correlation_group
                        }
                    })
                
                # 重要度-満足度分析のセクション
                if include_is:
                    sections.append({
                        "type": "重要度満足度",
                        "title": "重要度-満足度分析",
                        "options": {}
                    })
                
                # 設定の保存
                st.session_state.config_manager.config['pdf_settings'][settings_name] = {
                    "title": settings_name,
                    "sections": sections
                }
                st.session_state.config_manager.save_config()
                st.success(f"設定 '{settings_name}' を保存しました")
        
        # 保存済み設定の表示と選択
        saved_settings = st.session_state.config_manager.config.get('pdf_settings', {})
        if saved_settings:
            st.write("### 保存済み設定")
            selected_setting = st.selectbox(
                "使用する設定を選択",
                options=list(saved_settings.keys()),
                format_func=lambda x: f"{x} ({len(saved_settings[x]['sections'])}セクション)"
            )
            
            # PDF生成ボタン
            if st.button("PDF出力"):
                pdf_generator = PDFGenerator(st.session_state.config_manager)
                pdf_path = pdf_generator.generate_pdf(
                    st.session_state.data_processor.dfs,
                    st.session_state.config_manager,
                    st.session_state.visualizer,
                    settings_name=selected_setting
                )
                st.success(f"PDFを生成しました: {pdf_path}")

if __name__ == "__main__":
    main()
