#!/usr/bin/env python3
"""
Claude Code Git自動連携システム
"""
import sys
import json
import subprocess
import os
from pathlib import Path
from transcript_analyzer import TranscriptAnalyzer
from commit_generator import CommitMessageGenerator

def main():
    """メイン処理"""
    try:
        # 1. 入力データ読み込み
        input_data = json.load(sys.stdin)
        
        # 2. 設定読み込み
        config = load_config()
        
        # 3. Git変更確認
        if not has_git_changes():
            print("No changes detected. Skipping commit.")
            return 0
        
        # 4. 変更ファイルを事前に取得（git addの前）
        pre_add_changes = get_unstaged_changes()
        
        # 5. トランスクリプト解析
        analyzer = TranscriptAnalyzer(config)
        transcript_path = input_data.get('transcript_path')
        operations = analyzer.analyze(transcript_path)
        
        # 事前に取得した変更を解析結果に追加
        if pre_add_changes:
            # デバッグ: 変更ファイルをログ出力
            print(f"Pre-add changes detected: {pre_add_changes}")
            
            # 解析結果に変更ファイルがない場合、または空の場合は上書き
            if not operations.get('files_changed') or not any(operations['files_changed'].values()):
                operations['files_changed'] = pre_add_changes
                print(f"Updated operations with pre-add changes")
        
        # 6. コミットメッセージ生成
        generator = CommitMessageGenerator(config)
        # operationsはanalysis辞書なので、そのまま渡す
        commit_message = generator.generate(operations)
        
        # 7. Git操作実行
        success = execute_git_operations(commit_message, config)
        
        if success:
            return 0
        else:
            print("\nGit操作に失敗しました。上記の対処方法を確認してください。")
            return 1
        
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1

def load_config():
    """設定ファイル読み込み"""
    config_path = Path(__file__).parent / "git_config.json"
    with open(config_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def has_git_changes():
    """Git変更検出"""
    result = subprocess.run(['git', 'status', '--porcelain'], 
                           capture_output=True, text=True)
    return bool(result.stdout.strip())

def get_unstaged_changes():
    """ステージング前の変更ファイルを取得"""
    result = subprocess.run(['git', 'status', '--porcelain'], 
                           capture_output=True, text=True)
    
    files = {'added': [], 'modified': [], 'deleted': []}
    for line in result.stdout.strip().split('\n'):
        if line:
            status = line[:2].strip()
            file_path = line[2:].strip()  # 3文字目以降（スペースを除去）
            # フォルダの場合は中のファイルも取得
            if file_path.endswith('/'):
                # フォルダ内のファイルを取得
                folder_files = subprocess.run(['git', 'ls-files', '--others', '--exclude-standard', file_path], 
                                            capture_output=True, text=True)
                for f in folder_files.stdout.strip().split('\n'):
                    if f:
                        files['added'].append(f)
            else:
                if status in ['??', 'A']:
                    files['added'].append(file_path)
                elif status in ['M', 'AM']:
                    files['modified'].append(file_path)
                elif status == 'D':
                    files['deleted'].append(file_path)
    return files

def execute_git_operations(commit_message, config):
    """Git操作実行"""
    branch = config['system']['target_branch']
    
    try:
        # git add
        result = subprocess.run(['git', 'add', '-A'], capture_output=True, text=True)
        if result.returncode != 0:
            print(f"ERROR: git add failed")
            print(f"STDERR: {result.stderr}")
            print("\n対処方法:")
            print("- ファイルのアクセス権限を確認してください")
            print("- .gitignoreの設定を確認してください")
            return False
        
        # git commit
        result = subprocess.run(['git', 'commit', '-m', commit_message], capture_output=True, text=True)
        if result.returncode != 0:
            print(f"ERROR: git commit failed")
            print(f"STDERR: {result.stderr}")
            print("\n対処方法:")
            if "nothing to commit" in result.stdout:
                print("- 変更がありません。正常な動作です。")
            elif "Please tell me who you are" in result.stderr:
                print("- Gitのユーザー設定が必要です:")
                print('  git config --global user.email "you@example.com"')
                print('  git config --global user.name "Your Name"')
            else:
                print("- pre-commitフックが失敗している可能性があります")
                print("- コミットメッセージの形式を確認してください")
            return False
        
        print(f"✓ コミット成功: {commit_message.split('\\n')[0][:80]}...")
        
        # git push (auto_pushが有効な場合)
        if config['system']['auto_push']:
            print(f"Pushing to {branch}...")
            result = subprocess.run(['git', 'push', 'origin', branch], capture_output=True, text=True)
            if result.returncode != 0:
                print(f"ERROR: git push failed")
                print(f"STDERR: {result.stderr}")
                print("\n対処方法:")
                if "rejected" in result.stderr:
                    print("- リモートに新しい変更があります。まずpullしてください:")
                    print(f"  git pull origin {branch}")
                elif "Could not read from remote repository" in result.stderr:
                    print("- リモートリポジトリへのアクセス権限を確認してください")
                    print("- SSH鍵またはアクセストークンの設定を確認してください")
                elif "does not exist" in result.stderr:
                    print(f"- リモートブランチ '{branch}' が存在しません")
                    print(f"  git push -u origin {branch}")
                else:
                    print("- ネットワーク接続を確認してください")
                    print("- リモートリポジトリのURLを確認してください:")
                    print("  git remote -v")
                return False
            
            print(f"✓ プッシュ成功: origin/{branch}")
        
        return True
        
    except Exception as e:
        print(f"ERROR: 予期しないエラーが発生しました: {e}")
        print("\n対処方法:")
        print("- Gitがインストールされているか確認してください")
        print("- 現在のディレクトリがGitリポジトリか確認してください")
        return False

if __name__ == "__main__":
    sys.exit(main())