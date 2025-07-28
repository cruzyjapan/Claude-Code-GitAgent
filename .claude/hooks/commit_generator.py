"""
コミットメッセージ生成モジュール（修正版）
"""
from typing import Dict, List, Any
import re

class CommitMessageGenerator:
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.language = config['system']['language']
        self.templates = config['message_templates'][self.language]
    
    def generate(self, analysis: Dict[str, Any]) -> str:
        """コミットメッセージを生成"""
        # 変更タイプを判定
        change_type = self._determine_change_type(analysis)
        
        # 作業内容を分析してタイトルを生成
        title = self._generate_smart_title(analysis, change_type)
        
        # 詳細を生成（何をしたかの要約を含む）
        details = self._generate_detailed_summary(analysis)
        
        
        # テンプレートを適用
        template = self.templates.get(change_type, self.templates['feat'])
        
        # 詳細が空の場合、最低限の情報を追加
        if not details:
            details = self._generate_fallback_details(analysis)
        
        return template.format(
            summary=title,
            details=details
        ).strip()
    
    def _determine_change_type(self, analysis: Dict[str, Any]) -> str:
        """変更タイプを判定"""
        user_request = analysis.get('user_request', '').lower()
        operations = analysis.get('operations', [])
        
        # バグ修正キーワードの検出
        bug_keywords = ['バグ', 'bug', 'fix', '修正', 'エラー', 'error']
        if any(keyword in user_request for keyword in bug_keywords):
            return 'fix'
        
        # リファクタリングキーワードの検出
        refactor_keywords = ['リファクタリング', 'refactor', '整理', 'cleanup']
        if any(keyword in user_request for keyword in refactor_keywords):
            return 'refactor'
        
        # ドキュメント更新の検出
        doc_files = [op for op in operations if self._is_doc_file(op.get('file_path', ''))]
        if doc_files and len(doc_files) == len(operations):
            return 'docs'
        
        return 'feat'
    
    def _generate_smart_title(self, analysis: Dict[str, Any], change_type: str) -> str:
        """作業内容を分析して意味のあるタイトルを生成"""
        operations = analysis.get('operations', [])
        files_changed = analysis.get('files_changed', {})
        user_request = analysis.get('user_request', '')
        
        # ファイルパスから作業内容を推測
        all_files = self._get_all_changed_files(operations, files_changed)
        
        # ファイルパスを分析して作業内容を特定
        work_summary = self._analyze_work_content(all_files, operations)
        
        if work_summary:
            return work_summary
        
        # ユーザーリクエストから生成
        if user_request:
            return self._extract_main_action(user_request)
        
        # 従来の方法にフォールバック
        return self._generate_title(analysis, change_type)
    
    def _analyze_work_content(self, file_paths: List[str], operations: List[Dict]) -> str:
        """ファイルパスと操作から作業内容を分析"""
        if not file_paths:
            return ""
        
        # 特定のパターンを検出
        patterns = {
            'git_auto_commit': 'Git自動コミットシステム',
            'transcript_analyzer': 'トランスクリプト解析',
            'commit_generator': 'コミットメッセージ生成',
            'test': 'テスト',
            'debug': 'デバッグ',
            'fix': '修正',
            'improve': '改善',
            'update': '更新',
            'add': '追加',
            'README': 'README',
            'config': '設定',
            'doc': 'ドキュメント',
            'demo': 'デモサイト',
            'index.html': 'HTMLファイル',
            'styles.css': 'スタイルシート',
            'script.js': 'JavaScript'
        }
        
        # ファイルパスから主要な作業を特定
        work_types = set()
        for path in file_paths:
            path_lower = path.lower()
            for pattern, work_type in patterns.items():
                if pattern.lower() in path_lower:
                    work_types.add(work_type)
        
        # 操作タイプを取得
        action_types = set()
        for op in operations:
            action = op.get('action', '')
            if action:
                action_types.add(action)
        
        # タイトルを構築
        if self.language == 'ja':
            if work_types:
                work_str = '、'.join(sorted(work_types)[:2])  # 最大2つまで
                if len(action_types) == 1 and '作成' in action_types:
                    return f"{work_str}を作成"
                elif len(action_types) == 1 and '編集' in action_types:
                    return f"{work_str}を改善"
                elif '修正' in work_types or 'fix' in work_types:
                    return f"{work_str}の問題を修正"
                else:
                    return f"{work_str}を更新"
            elif len(file_paths) == 1:
                # 単一ファイルで特定のパターンが見つからない場合
                file_name = file_paths[0].split('/')[-1]
                if len(action_types) == 1 and '作成' in action_types:
                    return f"{file_name}を作成"
                else:
                    return f"{file_name}を更新"
        else:
            if work_types:
                work_str = ', '.join(sorted(work_types)[:2])
                if len(action_types) == 1 and 'create' in str(action_types):
                    return f"Create {work_str}"
                elif len(action_types) == 1 and 'edit' in str(action_types):
                    return f"Improve {work_str}"
                elif 'fix' in work_types:
                    return f"Fix {work_str} issues"
                else:
                    return f"Update {work_str}"
        
        return ""
    
    def _generate_title(self, analysis: Dict[str, Any], change_type: str) -> str:
        """タイトルを生成"""
        operations = analysis.get('operations', [])
        files_changed = analysis.get('files_changed', {})
        user_request = analysis.get('user_request', '')
        
        # ユーザーリクエストから主要な動詞・目的を抽出
        if user_request:
            title = self._extract_main_action(user_request)
            if title:
                return self._truncate_title(title)
        
        # 操作内容から自動生成
        if operations:
            return self._generate_title_from_operations(operations)
        
        # ファイル変更から生成
        return self._generate_title_from_files(files_changed)
    
    def _extract_main_action(self, request: str) -> str:
        """ユーザーリクエストから主要なアクションを抽出"""
        # 日本語パターン
        if self.language == 'ja':
            patterns = [
                r'(.+?)を(作成|追加|実装|修正|削除|更新)',
                r'(.+?)の(作成|追加|実装|修正|削除|更新)',
                r'(作成|追加|実装|修正|削除|更新)(.+?)',
            ]
        else:
            patterns = [
                r'(create|add|implement|fix|delete|update|build)\s+(.+)',
                r'(.+?)\s+(creation|addition|implementation|fix|deletion|update)',
            ]
        
        for pattern in patterns:
            match = re.search(pattern, request, re.IGNORECASE)
            if match:
                return match.group(0)[:50]
        
        return request[:50]
    
    def _generate_title_from_operations(self, operations: List[Dict]) -> str:
        """操作内容からタイトルを生成"""
        if not operations:
            return "ファイル更新" if self.language == 'ja' else "Update files"
        
        # ファイルタイプごとに分類
        file_types = {}
        file_names = []
        for op in operations:
            file_path = op.get('file_path', '')
            if file_path:
                file_names.append(file_path.split('/')[-1])
                ext = file_path.split('.')[-1] if '.' in file_path else 'file'
                file_types[ext] = file_types.get(ext, 0) + 1
        
        # 操作の種類と数をカウント
        action_counts = {}
        for op in operations:
            action = op.get('action', '')
            action_counts[action] = action_counts.get(action, 0) + 1
        
        # 主要な操作を特定
        main_action = max(action_counts.items(), key=lambda x: x[1]) if action_counts else ('', 0)
        
        # より詳細なタイトルを生成
        if self.language == 'ja':
            # 特定のファイルタイプの処理
            if len(file_types) == 1 and list(file_types.keys())[0] == 'md':
                if len(file_names) == 1:
                    return f"{file_names[0]}を{main_action[0]}"
                else:
                    return f"ドキュメント{main_action[1]}個を{main_action[0]}"
            elif 'test' in ' '.join(file_names).lower():
                return f"テストファイル{sum(action_counts.values())}個を{main_action[0]}"
            elif all(k in ['py', 'js', 'ts', 'jsx', 'tsx'] for k in file_types.keys()):
                return f"ソースコード{sum(action_counts.values())}個を{main_action[0]}"
            elif len(action_counts) == 1 and main_action[1] == 1:
                return f"{file_names[0]}を{main_action[0]}"
            elif len(action_counts) == 1:
                return f"{main_action[1]}個のファイルを{main_action[0]}"
            else:
                return f"複数ファイルの更新 ({', '.join(action_counts.keys())})"
        else:
            if len(file_types) == 1 and list(file_types.keys())[0] == 'md':
                if len(file_names) == 1:
                    return f"{main_action[0].title()} {file_names[0]}"
                else:
                    return f"{main_action[0].title()} {main_action[1]} documentation files"
            elif 'test' in ' '.join(file_names).lower():
                return f"{main_action[0].title()} {sum(action_counts.values())} test files"
            elif all(k in ['py', 'js', 'ts', 'jsx', 'tsx'] for k in file_types.keys()):
                return f"{main_action[0].title()} {sum(action_counts.values())} source files"
            elif len(action_counts) == 1 and main_action[1] == 1:
                return f"{main_action[0].title()} {file_names[0]}"
            elif len(action_counts) == 1:
                return f"{main_action[0].title()} {main_action[1]} files"
            else:
                return f"Update multiple files ({', '.join(action_counts.keys())})"
    
    def _generate_title_from_files(self, files_changed: Dict[str, List[str]]) -> str:
        """ファイル変更からタイトルを生成"""
        total_changes = sum(len(files) for files in files_changed.values())
        
        if self.language == 'ja':
            return f"{total_changes}個のファイルを更新"
        else:
            return f"Update {total_changes} files"
    
    def _generate_detailed_summary(self, analysis: Dict[str, Any]) -> str:
        """詳細な要約を生成（何をしたかを含む）"""
        details = []
        
        # 最初にすべての変数を定義（エラー防止）
        try:
            operations = analysis.get('operations', [])
            files_changed = analysis.get('files_changed', {})
            all_files = self._get_all_changed_files(operations, files_changed)
        except Exception as e:
            print(f"ERROR in variable initialization: {e}")
            operations = []
            files_changed = {}
            all_files = []
        
        # デバッグ情報
        
        # 常に実施した作業の詳細を出力
        details.append("実施した作業の詳細:")
        details.append("")
        
        # operationsが空の場合、files_changedから詳細を生成
        if not operations and any(files_changed.values()):
            for change_type, files in files_changed.items():
                if files:
                    for file_path in files:
                        file_name = file_path.split('/')[-1]
                        if change_type == 'added':
                            details.append(f"■ {file_name} - 新規作成")
                            # ファイルタイプから詳細を推測
                            if file_path.endswith('.html'):
                                details.append("  - HTMLファイルを新規作成")
                                details.append("  - Webページの構築")
                            elif file_path.endswith('.py'):
                                details.append("  - Pythonスクリプトを新規作成")
                                if 'commit_generator' in file_path:
                                    details.append("  - Git自動コミットシステムの機能")
                                elif 'transcript_analyzer' in file_path:
                                    details.append("  - トランスクリプト解析機能")
                            details.append("")
                        elif change_type == 'modified':
                            details.append(f"■ {file_name} - 更新")
                            if 'commit_generator' in file_path:
                                details.append("  - Git自動コミットシステムの改善")
                                details.append("  - 詳細生成ロジックの強化")
                                details.append("  - より包括的なコミットメッセージ生成")
                            elif 'transcript_analyzer' in file_path:
                                details.append("  - トランスクリプト解析機能の改善")
                                details.append("  - より多くのツール操作を追跡")
                            elif 'git_auto_commit' in file_path:
                                details.append("  - Git自動コミットのメイン処理を改善")
                                details.append("  - デバッグ情報の追加")
                            details.append("")
        
        # すべてのツール操作を記録（ファイル操作以外も含む）
        for i, op in enumerate(operations):
            tool = op.get('tool', '')
            file_path = op.get('file_path', '')
            action = op.get('action', '')
            change_details = op.get('change_details', {})
            
            
            # ファイル操作の詳細
            if tool in ['Write', 'Edit', 'MultiEdit'] and file_path:
                # ファイル名と操作内容
                file_name = file_path.split('/')[-1]
                details.append(f"■ {file_name} - {action}")
                
                # トランスクリプト解析からの詳細情報を使用
                if change_details:
                    if 'type' in change_details:
                        details.append(f"  - {change_details['type']}ファイル")
                    if 'features' in change_details:
                        for feature in change_details['features']:
                            details.append(f"  - {feature}")
                    if 'lines_added' in change_details:
                        details.append(f"  - {change_details['lines_added']}行追加")
                    if 'edit_count' in change_details:
                        details.append(f"  - {change_details['edit_count']}箇所の編集")
                    if 'change_type' in change_details:
                        details.append(f"  - 変更タイプ: {change_details['change_type']}")
                
                # フォールバック: 従来の解析方法
                if not change_details:
                    if tool == 'Write':
                        content = op.get('details', {}).get('content', '')
                        file_details = self._analyze_file_content(file_path, content)
                        details.extend([f"  {d}" for d in file_details])
                    elif tool in ['Edit', 'MultiEdit']:
                        # 編集内容から変更の詳細を生成
                        edit_details = self._analyze_edit_content(file_path, op.get('details', {}), tool)
                        details.extend([f"  {d}" for d in edit_details])
                
                details.append("")
            
            # その他のツール操作も記録
            elif tool in ['Read', 'Bash', 'WebFetch', 'TodoWrite', 'Glob', 'Grep']:
                details.append(f"○ {action}: {tool}")
                if tool == 'Read':
                    details.append(f"  - ファイル読み込み: {file_path}")
                elif tool == 'Bash':
                    command = op.get('details', {}).get('command', '')
                    details.append(f"  - コマンド: {command[:100]}..." if len(command) > 100 else f"  - コマンド: {command}")
                elif tool == 'Glob':
                    pattern = op.get('details', {}).get('pattern', '')
                    details.append(f"  - パターン: {pattern}")
                elif tool == 'Grep':
                    pattern = op.get('details', {}).get('pattern', '')
                    details.append(f"  - 検索: {pattern[:50]}..." if len(pattern) > 50 else f"  - 検索: {pattern}")
                details.append("")
        
        # ファイル変更がある場合は必ず記録
        if any(files_changed.values()):
            details.append("変更されたファイル:")
            for change_type, files in files_changed.items():
                if files:
                    details.append(f"- {change_type}: {', '.join(files)}")
            details.append("")
        
        # ファイルタイプごとの詳細を生成
        details.extend(self._generate_file_type_details(all_files, operations, analysis.get('user_request', '')))
        
        # 最大限の詳細を記録するため、すべての情報源から詳細を生成
        
        # 1. 作業内容ごとの詳細を生成
        work_details = self._generate_work_specific_details(analysis.get('user_request', ''), analysis, all_files)
        if work_details:
            details.extend(work_details)
        
        # 2. 操作の詳細情報を生成
        operation_details = self._generate_operation_details(operations)
        if operation_details:
            details.extend(operation_details)
        
        # 3. アシスタントの作業内容を詳細に記録
        if operations or all_files:
            details.append("Claude Codeが実行した作業:")
            details.append(f"- 合計 {len(operations)} 個の操作を実行")
            details.append(f"- 対象ファイル数: {len(all_files)}")
            
            # 4. 実行した主な作業を列挙
            work_types = set()
            for f in all_files:
                if 'git_auto_commit' in f or 'commit_generator' in f:
                    work_types.add("Git自動コミットシステムの改善")
                if 'transcript_analyzer' in f:
                    work_types.add("トランスクリプト解析機能の改善")
                if 'test' in f.lower():
                    work_types.add("テスト関連ファイルの作成/更新")
                if f.endswith('.html'):
                    work_types.add("HTMLファイルの作成/更新")
                if f.endswith('.py'):
                    work_types.add("Pythonスクリプトの作成/更新")
            
            for work in work_types:
                details.append(f"- {work}")
            
            details.append("")
        
        # 5. ユーザーリクエストから具体的な作業内容を抽出
        user_request = analysis.get('user_request', '')
        if user_request:
            details.append(f"ユーザーリクエスト: {user_request}")
            specific_details = self._extract_specific_details(user_request, analysis)
            if specific_details:
                details.append(specific_details)
            details.append("")
        
        # 6. アシスタントの回答要約を追加（ファイル作成後の説明を含む）
        assistant_summary = self._summarize_assistant_responses(analysis.get('assistant_responses', []))
        if assistant_summary:
            # セクションタイトルを追加しない（既に含まれている場合が多いため）
            details.append(assistant_summary)
            details.append("")
        
        
        # 7. ファイル変更一覧を必ず含める
        files_section = self._format_file_changes(analysis.get('files_changed', {}))
        if files_section:
            details.append(files_section)
        else:
            # ファイル変更が検出されない場合も操作から生成
            details.append("変更ファイル:")
            for op in operations:
                if op.get('file_path'):
                    action = op.get('action', '')
                    file_path = op.get('file_path', '')
                    details.append(f"- {action}: {file_path}")
        
        # 結果を結合（空行の重複を避ける）
        result = []
        for line in details:
            if line or (result and result[-1]):  # 空行の連続を避ける
                result.append(line)
        
        return '\n'.join(result)
    
    def _generate_work_summary(self, analysis: Dict[str, Any]) -> str:
        """作業内容の要約を生成"""
        operations = analysis.get('operations', [])
        files_changed = analysis.get('files_changed', {})
        
        # 変更されたファイルから作業内容を分析
        all_files = self._get_all_changed_files(operations, files_changed)
        
        # 作業内容を特定
        work_items = []
        
        # パターンマッチングで具体的な作業を特定
        if any('git_auto_commit' in f for f in all_files):
            if any('test' in f for f in all_files):
                work_items.append('Git自動コミットシステムのテストファイルを作成・更新')
            else:
                work_items.append('Git自動コミットシステムの実装を改善')
        
        if any('transcript_analyzer' in f for f in all_files):
            work_items.append('トランスクリプト解析機能を改善（ツール名マッピング修正、ステージング検出改善）')
        
        if any('commit_generator' in f for f in all_files):
            work_items.append('コミットメッセージ生成ロジックを改善（作業内容の要約、詳細な記述）')
        
        if any('test' in f for f in all_files) and not any(item for item in work_items if 'テスト' in item):
            work_items.append('動作確認用テストファイルを作成')
        
        if any('debug' in f for f in all_files):
            work_items.append('デバッグ用ファイルを作成して問題を調査')
        
        # テストモックページの作業を検出
        if any('test-mock' in f for f in all_files):
            work_items.append('完全なダミーページ（test-mock.html）を作成')
            work_items.append('レスポンシブデザインを実装')
            work_items.append('日本語コンテンツで構成')
        
        # README関連の作業を検出
        if any('README' in f for f in all_files):
            readme_files = [f for f in all_files if 'README' in f]
            user_request = analysis.get('user_request', '')
            if len(all_files) == 1:  # READMEのみの更新
                # 変更タイプから作業内容を推測
                if files_changed.get('added') and 'README' in str(files_changed.get('added')):
                    work_items.append('プロジェクトREADMEを作成')
                else:
                    if 'GitHub' in user_request or 'リリース' in user_request:
                        work_items.append('READMEをGitHubリリース用に更新')
                    else:
                        work_items.append('プロジェクトREADMEを更新（最新の構造・機能を反映）')
        
        # その他の単一ファイル更新を検出
        if len(all_files) == 1 and not work_items:
            file_name = all_files[0]
            if '.py' in file_name:
                work_items.append('Pythonスクリプトを更新')
            elif '.js' in file_name:
                work_items.append('JavaScriptファイルを更新')
            elif '.css' in file_name:
                work_items.append('スタイルシートを更新')
            elif '.html' in file_name:
                work_items.append('HTMLファイルを更新')
            elif '.json' in file_name:
                work_items.append('設定ファイルを更新')
            elif '.md' in file_name:
                work_items.append('ドキュメントを更新')
        
        # 要約を構築
        if work_items:
            if self.language == 'ja':
                summary = "実施した作業:\n"
                for item in work_items:
                    summary += f"- {item}\n"
                return summary.strip()
            else:
                summary = "Work performed:\n"
                for item in work_items:
                    summary += f"- {item}\n"
                return summary.strip()
        
        return ""
    
    def _generate_details(self, analysis: Dict[str, Any]) -> str:
        """詳細セクションを生成"""
        details = []
        
        # 操作詳細
        operations = analysis.get('operations', [])
        if operations:
            details.append(self._format_operations(operations))
        
        # ファイル変更一覧
        if self.config['analysis']['include_file_changes']:
            files_section = self._format_file_changes(analysis.get('files_changed', {}))
            if files_section:
                details.append(files_section)
        
        return '\n\n'.join(details)
    
    def _format_operations(self, operations: List[Dict]) -> str:
        """操作内容をフォーマット"""
        if not operations:
            return ""
        
        if self.language == 'ja':
            header = "実行した操作:"
            bullet = "- "
        else:
            header = "Operations performed:"
            bullet = "- "
        
        formatted = [header]
        
        # ファイルごとにグループ化
        file_operations = {}
        for op in operations:
            file_path = op.get('file_path', '')
            action = op.get('action', '')
            if file_path:
                if file_path not in file_operations:
                    file_operations[file_path] = []
                file_operations[file_path].append(action)
        
        # フォーマット出力
        for file_path, actions in file_operations.items():
            file_name = file_path.split('/')[-1]
            if len(actions) == 1:
                formatted.append(f"{bullet}{actions[0]}: {file_name}")
            else:
                actions_str = ', '.join(actions)
                formatted.append(f"{bullet}{file_name}: {actions_str}")
        
        # ファイルタイプの概要を追加
        extensions = {}
        for file_path in file_operations.keys():
            if '.' in file_path:
                ext = file_path.split('.')[-1]
                extensions[ext] = extensions.get(ext, 0) + 1
        
        if extensions and len(extensions) > 1:
            ext_summary = ', '.join([f"{count} {ext}" for ext, count in extensions.items()])
            if self.language == 'ja':
                formatted.append(f"\nファイルタイプ: {ext_summary}")
            else:
                formatted.append(f"\nFile types: {ext_summary}")
        
        return '\n'.join(formatted)
    
    def _format_file_changes(self, files_changed: Dict[str, List[str]]) -> str:
        """ファイル変更をフォーマット"""
        if not any(files_changed.values()):
            return ""
        
        if self.language == 'ja':
            labels = {'added': '追加', 'modified': '変更', 'deleted': '削除'}
            header = "変更ファイル:"
        else:
            labels = {'added': 'Added', 'modified': 'Modified', 'deleted': 'Deleted'}
            header = "Changed files:"
        
        formatted = [header]
        for change_type, files in files_changed.items():
            if files:
                label = labels.get(change_type, change_type)
                formatted.append(f"- {label}: {', '.join(files)}")
        
        return '\n'.join(formatted)
    
    def _is_doc_file(self, file_path: str) -> bool:
        """ドキュメントファイルかどうかを判定"""
        doc_extensions = ['.md', '.txt', '.rst', '.doc', '.docx']
        return any(file_path.endswith(ext) for ext in doc_extensions)
    
    def _truncate_title(self, title: str) -> str:
        """タイトルを指定文字数で切り詰める"""
        max_length = self.config['system']['max_title_length']
        if len(title) <= max_length:
            return title
        return title[:max_length-3] + "..."
    
    def _get_all_changed_files(self, operations: List[Dict], files_changed: Dict[str, List[str]]) -> List[str]:
        """全ての変更ファイルを取得"""
        all_files = []
        for op in operations:
            if op.get('file_path'):
                all_files.append(op['file_path'])
        all_files.extend(files_changed.get('added', []))
        all_files.extend(files_changed.get('modified', []))
        return list(set(all_files))  # 重複を除去
    
    def _extract_specific_details(self, user_request: str, analysis: Dict[str, Any]) -> str:
        """ユーザーリクエストから具体的な作業詳細を抽出"""
        # この実装は元のコードから省略
        return ""
    
    def _generate_file_type_details(self, all_files: List[str], operations: List[Dict], user_request: str) -> List[str]:
        """ファイルタイプごとの詳細を生成"""
        # この実装は元のコードから省略  
        return []
    
    def _generate_work_specific_details(self, user_request: str, analysis: Dict[str, Any], all_files: List[str]) -> List[str]:
        """作業内容に応じた詳細を生成"""
        # この実装は元のコードから省略
        return []
    
    def _generate_operation_details(self, operations: List[Dict]) -> List[str]:
        """操作の詳細情報を生成"""
        # この実装は元のコードから省略
        return []
    
    def _analyze_file_content(self, file_path: str, content: str) -> List[str]:
        """ファイル内容を解析して詳細を生成"""
        # この実装は元のコードから省略
        return []
    
    def _analyze_edit_content(self, file_path: str, details: Dict, tool: str) -> List[str]:
        """編集内容を解析して詳細を生成"""
        # この実装は元のコードから省略
        return []
    
    def _generate_fallback_details(self, analysis: Dict[str, Any]) -> str:
        """詳細が生成されなかった場合のフォールバック"""
        # この実装は元のコードから省略
        return ""
    
    def _summarize_assistant_responses(self, responses: List[str]) -> str:
        """アシスタントの回答内容を要約"""
        if not responses:
            return ""
        
        summary_lines = []
        
        for response in responses:
            # 「作成した内容：」や「実施した改善内容：」などのセクションを探す
            if "作成した内容" in response or "実施した" in response or "完了しました" in response:
                lines = response.split('\n')
                capture = False
                for line in lines:
                    # セクション開始を検出
                    if any(keyword in line for keyword in ["作成した内容", "実施した", "内容："]):
                        capture = True
                        summary_lines.append(line.strip())
                        continue
                    
                    # セクション内容をキャプチャ
                    if capture:
                        # 空行で区切られるまで
                        if line.strip() == "":
                            if len(summary_lines) > 1:  # 内容がある場合のみ空行追加
                                summary_lines.append("")
                        elif line.strip().startswith(('#', '-', '•', '・', '1.', '2.', '3.')):
                            summary_lines.append(line.strip())
                        elif "：" in line or ":" in line:
                            summary_lines.append(line.strip())
        
        if summary_lines:
            # 重複を削除しつつ順序を保持
            seen = set()
            unique_lines = []
            for line in summary_lines:
                if line not in seen or line == "":  # 空行は重複チェックしない
                    seen.add(line)
                    unique_lines.append(line)
            
            return '\n'.join(unique_lines)
        
        return ""