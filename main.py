import streamlit as st
import pandas as pd
import json
from utils.data_processor import DataProcessor
from utils.config_manager import ConfigManager
from utils.visualization import Visualizer
from utils.pdf_generator import PDFGenerator

st.set_page_config(layout="wide", page_title="意識調査データ分析ダッシュボード")

def main():
    st.title("意識調査データ分析ダッシュボード")

    # Initialize session state
    if 'data_processor' not in st.session_state:
        st.session_state.data_processor = DataProcessor()
    if 'config_manager' not in st.session_state:
        st.session_state.config_manager = ConfigManager()
    if 'visualizer' not in st.session_state:
        st.session_state.visualizer = Visualizer()

    # File upload section
    st.header("1. データアップロード")
    st.write("時期の古いものから順にしてください")
    
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
                st.success(f"{len(valid_files)}件のデータを読み込みました")
            else:
                st.warning("有効なデータがありません。日付とファイルの両方を指定してください。")

    # Data analysis section
    if hasattr(st.session_state.data_processor, 'dfs'):
        st.header("2. データ分析")
        
        # Display raw data and analysis
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

        # Configuration section
        st.header("3. 設定")
        
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
                attributes = st.multiselect("属性として扱う列を選択:",
                                       st.session_state.data_processor.dfs[0].columns)
                if st.button("属性を保存"):
                    st.session_state.config_manager.save_attributes(attributes)
                    st.success("属性の設定を保存しました")
            else:
                st.info("データを読み込むと、属性の設定が可能になります。")

        # Question grouping
        with st.expander("質問グループの設定", expanded=True):
            if hasattr(st.session_state.data_processor, 'dfs') and st.session_state.data_processor.dfs:
                # 列名のマッピングを取得
                column_names = st.session_state.config_manager.config.get('column_names', {})
                
                # 既存の質問グループの一覧表示と削除機能
                if question_groups := st.session_state.config_manager.config.get('question_groups', {}):
                    st.write("登録済み質問グループ一覧")
                    
                    for group_name, questions in list(question_groups.items()):
                        col1, col2 = st.columns([5, 1])
                        with col1:
                            st.write(f"📁 {group_name}")
                            st.write(f"質問項目: {', '.join([column_names.get(q, q) for q in questions])}")
                        with col2:
                            if st.button("削除", key=f"delete_{group_name}"):
                                del st.session_state.config_manager.config['question_groups'][group_name]
                                st.session_state.config_manager.save_config()
                                st.success(f"グループ '{group_name}' を削除しました")
                                st.experimental_rerun()
                
                # 新規グループの追加
                st.write("新規グループの追加")
                group_name = st.text_input("グループ名:")
                questions = st.multiselect(
                    "グループに含める質問:",
                    st.session_state.data_processor.dfs[0].columns,
                    format_func=lambda x: column_names.get(x, x)
                )
                if st.button("グループを保存"):
                    st.session_state.config_manager.save_question_group(group_name, questions)
                    st.success("質問グループを保存しました")
            else:
                st.info("データを読み込むと、質問グループの設定が可能になります。")

        # Visualization section
        st.header("4. 可視化")
        
        tab1, tab2 = st.tabs(["数値表", "ダッシュボード"])
        
        with tab1:
            st.session_state.visualizer.display_numerical_tables(
                st.session_state.data_processor.dfs,
                st.session_state.config_manager
            )
            
        with tab2:
            st.session_state.visualizer.display_dashboard(
                st.session_state.data_processor.dfs,
                st.session_state.config_manager
            )

        # PDF Export
        st.header("5. PDF出力")
        if st.button("PDF出力"):
            pdf_generator = PDFGenerator()
            pdf_path = pdf_generator.generate_pdf(
                st.session_state.data_processor.dfs,
                st.session_state.config_manager,
                st.session_state.visualizer
            )
            st.success(f"PDFを生成しました: {pdf_path}")

if __name__ == "__main__":
    main()
