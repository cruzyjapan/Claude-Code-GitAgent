"""
トランスクリプト解析モジュール
"""
import json
import re
from pathlib import Path
from typing import Dict, List, Any

class TranscriptAnalyzer:
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.tool_patterns = {
            'write': r'Write\s+(.+)',
            'edit': r'Edit\s+(.+)',
            'delete': r'Delete\s+(.+)',
            'create': r'Create\s+(.+)'
        }
    
    def analyze(self, transcript_path: str) -> Dict[str, Any]:
        """トランスクリプト解析メイン処理"""
        if not transcript_path or not Path(transcript_path).exists():
            return self._get_fallback_analysis()
        
        with open(transcript_path, 'r', encoding='utf-8') as f:
            transcript_lines = [json.loads(line) for line in f]
        
        # 最後のユーザーメッセージから現在までの操作を抽出
        last_user_idx = self._find_last_user_message(transcript_lines)
        recent_operations = transcript_lines[last_user_idx:]
        
        return {
            'user_request': self._extract_user_request(transcript_lines, last_user_idx),
            'operations': self._extract_operations(recent_operations),
            'files_changed': self._get_changed_files(),
            'summary': self._generate_summary(recent_operations),
            'assistant_responses': self._extract_assistant_responses(recent_operations)
        }
    
    def _find_last_user_message(self, transcript: List[Dict]) -> int:
        """最後のユーザーメッセージのインデックスを取得"""
        for i in range(len(transcript) - 1, -1, -1):
            if transcript[i].get('role') == 'user':
                return i
        return 0
    
    def _extract_user_request(self, transcript: List[Dict], user_idx: int) -> str:
        """ユーザーリクエスト内容を抽出"""
        if user_idx < len(transcript):
            # 文字数制限を増やして、より詳細な内容を取得
            return transcript[user_idx].get('content', '')[:1000]
        return ""
    
    def _extract_assistant_responses(self, operations: List[Dict]) -> List[str]:
        """アシスタントの回答内容を抽出"""
        responses = []
        for item in operations:
            if item.get('role') == 'assistant' and item.get('content'):
                content = item['content']
                # ツール使用のみのメッセージは除外
                if not content.startswith('<function_calls>'):
                    # ファイル作成後の説明を優先的に抽出
                    if any(keyword in content for keyword in [
                        "作成しました", "作成した内容", "実施した", "改善内容",
                        "完了しました", "以下の", "##", "###", "内容："
                    ]):
                        # 重要な説明は全文を保持（最大2000文字）
                        responses.append(content[:2000])
                    elif len(content) > 50:  # その他の回答は短縮版
                        responses.append(content[:500])
        return responses
    
    def _extract_operations(self, operations: List[Dict]) -> List[Dict]:
        """操作内容を抽出・分類"""
        extracted = []
        for item in operations:
            if item.get('role') == 'assistant' and 'tool_calls' in item:
                for tool_call in item['tool_calls']:
                    tool_name = tool_call.get('function', {}).get('name', '')
                    # すべてのツール操作を記録（より詳細な解析のため）
                    if tool_name in ['Write', 'Edit', 'Delete', 'MultiEdit', 'NotebookEdit', 'NotebookWrite',
                                   'Read', 'Bash', 'WebFetch', 'WebSearch', 'TodoWrite', 'Glob', 'Grep', 'LS']:
                        operation = self._parse_tool_operation(tool_call)
                        # 操作に詳細情報を追加
                        operation['timestamp'] = item.get('timestamp', '')
                        operation['context'] = self._extract_operation_context(tool_call, item)
                        extracted.append(operation)
        return extracted
    
    def _parse_tool_operation(self, tool_call: Dict) -> Dict:
        """ツール操作をパース（詳細版）"""
        function_name = tool_call.get('function', {}).get('name', '')
        arguments = json.loads(tool_call.get('function', {}).get('arguments', '{}'))
        
        # ファイルパスの取得（ツールによって異なる）
        file_path = ''
        if function_name in ['Write', 'Edit', 'Delete', 'MultiEdit', 'Read']:
            file_path = arguments.get('file_path', '')
        elif function_name in ['NotebookEdit', 'NotebookWrite', 'NotebookRead']:
            file_path = arguments.get('notebook_path', '')
        elif function_name == 'Bash':
            # Bashコマンドからファイルパスを抽出
            command = arguments.get('command', '')
            if 'git' in command:
                file_path = 'Git操作'
            else:
                file_path = command[:50] + '...' if len(command) > 50 else command
        elif function_name == 'Glob':
            file_path = f"Pattern: {arguments.get('pattern', '')}"
        elif function_name == 'Grep':
            file_path = f"Search: {arguments.get('pattern', '')[:30]}..."
        
        # 詳細な変更内容を抽出
        change_details = self._extract_change_details(function_name, arguments)
        
        return {
            'tool': function_name,
            'file_path': file_path,
            'action': self._determine_action(function_name, arguments),
            'details': arguments,
            'summary': self._generate_operation_summary(function_name, arguments),
            'change_details': change_details
        }
    
    def _determine_action(self, tool_name: str, args: Dict) -> str:
        """操作種別を判定"""
        if self.config['system']['language'] == 'ja':
            action_map = {
                'Write': '作成',
                'Edit': '編集',
                'Delete': '削除',
                'MultiEdit': '複数編集',
                'NotebookEdit': 'ノートブック編集',
                'NotebookWrite': 'ノートブック作成',
                'Read': '読み込み',
                'Bash': 'コマンド実行',
                'WebFetch': 'Web取得',
                'WebSearch': 'Web検索',
                'TodoWrite': 'TODO更新'
            }
        else:
            action_map = {
                'Write': 'create',
                'Edit': 'edit',
                'Delete': 'delete',
                'MultiEdit': 'multi-edit',
                'NotebookEdit': 'notebook-edit',
                'NotebookWrite': 'notebook-create',
                'Read': 'read',
                'Bash': 'command',
                'WebFetch': 'web-fetch',
                'WebSearch': 'web-search',
                'TodoWrite': 'todo-update'
            }
        return action_map.get(tool_name, tool_name)
    
    def _get_changed_files(self) -> Dict[str, List[str]]:
        """変更ファイル一覧を取得"""
        import subprocess
        # ステージングされたファイルを取得
        result = subprocess.run(['git', 'diff', '--cached', '--name-status'], 
                               capture_output=True, text=True)
        
        files = {'added': [], 'modified': [], 'deleted': []}
        for line in result.stdout.strip().split('\n'):
            if line:
                parts = line.split('\t')
                if len(parts) >= 2:
                    status, file_path = parts[0], parts[1]
                    if status == 'A':
                        files['added'].append(file_path)
                    elif status == 'M':
                        files['modified'].append(file_path)
                    elif status == 'D':
                        files['deleted'].append(file_path)
        return files
    
    def _generate_summary(self, operations: List[Dict]) -> str:
        """操作サマリーを生成"""
        operation_count = len([op for op in operations if op.get('role') == 'assistant'])
        if self.config['system']['language'] == 'ja':
            return f"{operation_count}個の操作を実行"
        else:
            return f"Executed {operation_count} operations"
    
    def _generate_operation_summary(self, tool_name: str, args: Dict) -> str:
        """操作の要約を生成"""
        if tool_name == 'Write':
            content = args.get('content', '')
            if '<html' in content.lower():
                return 'HTMLファイル作成'
            elif 'def ' in content or 'class ' in content:
                return 'Pythonコード作成'
            elif '{' in content and '}' in content:
                return 'JSON/設定ファイル作成'
        elif tool_name == 'Edit' or tool_name == 'MultiEdit':
            old_str = args.get('old_string', '')
            new_str = args.get('new_string', '')
            if len(old_str) > 100:
                return '大規模な変更'
            else:
                return '部分的な変更'
        elif tool_name == 'Bash':
            command = args.get('command', '')
            if 'git' in command:
                if 'commit' in command:
                    return 'Gitコミット'
                elif 'push' in command:
                    return 'Gitプッシュ'
                elif 'status' in command:
                    return 'Git状態確認'
                else:
                    return 'Git操作'
            elif 'npm' in command or 'pip' in command:
                return 'パッケージ管理'
            else:
                return 'システムコマンド'
        return ''
    
    def _get_fallback_analysis(self) -> Dict[str, Any]:
        """トランスクリプトが取得できない場合のフォールバック"""
        files_changed = self._get_changed_files()
        
        # ファイル変更から操作を推測
        operations = []
        for file in files_changed.get('added', []):
            operations.append({
                'tool': 'Write',
                'file_path': file,
                'action': '作成' if self.config['system']['language'] == 'ja' else 'create',
                'details': {'file_path': file}
            })
        for file in files_changed.get('modified', []):
            operations.append({
                'tool': 'Edit',
                'file_path': file,
                'action': '編集' if self.config['system']['language'] == 'ja' else 'edit',
                'details': {'file_path': file}
            })
        for file in files_changed.get('deleted', []):
            operations.append({
                'tool': 'Delete',
                'file_path': file,
                'action': '削除' if self.config['system']['language'] == 'ja' else 'delete',
                'details': {'file_path': file}
            })
        
        # ファイルタイプから作業内容を推測
        all_files = files_changed.get('added', []) + files_changed.get('modified', [])
        if all(file.endswith('.md') for file in all_files if file):
            user_request = 'ドキュメントの作成・更新'
        elif all(file.endswith('.test.') or 'test' in file for file in all_files if file):
            user_request = 'テストコードの作成・更新'
        else:
            user_request = 'ファイルの作成・更新'
        
        return {
            'user_request': user_request,
            'operations': operations,
            'files_changed': files_changed,
            'summary': self._generate_summary_from_files(files_changed),
            'assistant_responses': []  # フォールバック時は空リスト
        }
    
    def _generate_summary_from_files(self, files_changed: Dict[str, List[str]]) -> str:
        """ファイル変更からサマリーを生成"""
        added = len(files_changed.get('added', []))
        modified = len(files_changed.get('modified', []))
        deleted = len(files_changed.get('deleted', []))
        
        parts = []
        if self.config['system']['language'] == 'ja':
            if added > 0:
                parts.append(f"{added}個のファイルを追加")
            if modified > 0:
                parts.append(f"{modified}個のファイルを編集")
            if deleted > 0:
                parts.append(f"{deleted}個のファイルを削除")
            return '、'.join(parts) if parts else 'ファイル変更を検出'
        else:
            if added > 0:
                parts.append(f"Added {added} files")
            if modified > 0:
                parts.append(f"Modified {modified} files")
            if deleted > 0:
                parts.append(f"Deleted {deleted} files")
            return ', '.join(parts) if parts else 'File changes detected'
    
    def _extract_operation_context(self, tool_call: Dict, item: Dict) -> Dict:
        """操作のコンテキスト情報を抽出"""
        context = {}
        # 前後のメッセージ内容から文脈を取得
        if 'content' in item:
            content = item.get('content', '')
            if content and not content.startswith('<function_calls>'):
                context['assistant_message'] = content[:200]
        return context
    
    def _extract_change_details(self, tool_name: str, args: Dict) -> Dict:
        """変更内容の詳細を抽出"""
        details = {}
        
        if tool_name == 'Write':
            content = args.get('content', '')
            details['lines_added'] = len(content.split('\n'))
            details['size'] = len(content)
            # ファイルタイプ別の詳細情報
            if '<html' in content.lower():
                details['type'] = 'HTML'
                details['features'] = self._analyze_html_content(content)
            elif 'def ' in content or 'class ' in content:
                details['type'] = 'Python'
                details['features'] = self._analyze_python_content(content)
            elif 'function' in content or 'const ' in content:
                details['type'] = 'JavaScript'
                details['features'] = self._analyze_js_content(content)
        
        elif tool_name in ['Edit', 'MultiEdit']:
            if tool_name == 'Edit':
                old_str = args.get('old_string', '')
                new_str = args.get('new_string', '')
                details['lines_removed'] = len(old_str.split('\n'))
                details['lines_added'] = len(new_str.split('\n'))
                details['change_type'] = self._determine_change_type_from_diff(old_str, new_str)
            else:
                # MultiEditの場合
                edits = args.get('edits', [])
                details['edit_count'] = len(edits)
                details['total_lines_changed'] = sum(len(e.get('old_string', '').split('\n')) + 
                                                   len(e.get('new_string', '').split('\n')) 
                                                   for e in edits)
        
        return details
    
    def _analyze_html_content(self, content: str) -> List[str]:
        """HTML内容を分析"""
        features = []
        if '<form' in content:
            features.append('フォーム要素')
        if '<table' in content:
            features.append('テーブル')
        if '<nav' in content:
            features.append('ナビゲーション')
        if 'style=' in content or '<style>' in content:
            features.append('インラインCSS')
        if '<script>' in content:
            features.append('JavaScript')
        if '@media' in content:
            features.append('レスポンシブデザイン')
        return features
    
    def _analyze_python_content(self, content: str) -> List[str]:
        """Python内容を分析"""
        features = []
        if 'import ' in content:
            imports = re.findall(r'import\s+(\w+)', content)
            features.append(f'インポート: {len(imports)}個')
        if 'class ' in content:
            classes = re.findall(r'class\s+(\w+)', content)
            features.append(f'クラス: {len(classes)}個')
        if 'def ' in content:
            functions = re.findall(r'def\s+(\w+)', content)
            features.append(f'関数: {len(functions)}個')
        return features
    
    def _analyze_js_content(self, content: str) -> List[str]:
        """JavaScript内容を分析"""
        features = []
        if 'function' in content:
            features.append('関数定義')
        if 'addEventListener' in content:
            features.append('イベントリスナー')
        if 'fetch' in content or 'axios' in content:
            features.append('API呼び出し')
        if 'useState' in content or 'useEffect' in content:
            features.append('React Hooks')
        return features
    
    def _determine_change_type_from_diff(self, old_str: str, new_str: str) -> str:
        """差分から変更タイプを判定"""
        if len(new_str) > len(old_str) * 1.5:
            return '大幅な追加'
        elif len(new_str) < len(old_str) * 0.5:
            return '大幅な削除'
        elif 'bug' in new_str.lower() or 'fix' in new_str.lower():
            return 'バグ修正'
        elif 'improve' in new_str.lower() or '改善' in new_str:
            return '機能改善'
        else:
            return '一般的な更新'