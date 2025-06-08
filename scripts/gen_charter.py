#!/usr/bin/env python3
"""
CLI script to generate a project charter by prompting user with questions.
Saves result as charter_YYYYMMDD.yaml in data/charters/
"""

import argparse
import yaml
from datetime import datetime
from pathlib import Path
import sys
import os

# Add the project root to the path so we can import modules
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def load_questions(questions_file):
    """Load questions from YAML file"""
    with open(questions_file, 'r', encoding='utf-8') as f:
        data = yaml.safe_load(f)
    return data['questions']


def prompt_user(question):
    """Prompt user for a single question and return the answer"""
    print(f"\n📝 {question['prompt']}")
    
    if question['id'] in ['outcomes', 'scope.in', 'scope.out', 'constraints.tools', 'success_metrics']:
        print("   複数項目の場合は改行で区切って入力してください。空行で終了します。")
        items = []
        while True:
            item = input("   - ").strip()
            if not item:
                break
            items.append(item)
        return items
    
    elif question['id'] == 'stakeholders':
        print("   関係者を入力してください。空行で終了します。")
        stakeholders = []
        while True:
            name = input("   名前: ").strip()
            if not name:
                break
            role = input("   役割: ").strip()
            stakeholders.append({"name": name, "role": role})
        return stakeholders
    
    elif question['id'] == 'milestones':
        print("   マイルストーンを入力してください。空行で終了します。")
        milestones = []
        while True:
            date = input("   日付 (YYYY-MM-DD): ").strip()
            if not date:
                break
            title = input("   タイトル: ").strip()
            milestones.append({"date": date, "title": title})
        return milestones
    
    elif question['id'] == 'risks':
        print("   リスクと対策を入力してください。空行で終了します。")
        risks = []
        while True:
            risk = input("   リスク: ").strip()
            if not risk:
                break
            mitigation = input("   対策: ").strip()
            risks.append({"risk": risk, "mitigation": mitigation})
        return risks
    
    else:
        # Single string input
        return input("   ➤ ").strip()


def set_nested_value(data, key_path, value):
    """Set a nested dictionary value using dot notation (e.g., 'scope.in')"""
    keys = key_path.split('.')
    current = data
    
    for key in keys[:-1]:
        if key not in current:
            current[key] = {}
        current = current[key]
    
    current[keys[-1]] = value


def collect_answers(questions):
    """Collect answers from user for all questions"""
    print("🌟 Kai VPM プロジェクトチャーター生成")
    print("=" * 50)
    
    charter_data = {}
    
    for question in questions:
        answer = prompt_user(question)
        if answer:  # Only set if answer is not empty
            set_nested_value(charter_data, question['id'], answer)
    
    return charter_data


def generate_filename():
    """Generate filename with current date"""
    today = datetime.now().strftime("%Y%m%d")
    return f"charter_{today}.yaml"


def save_charter(charter_data, output_dir, dry_run=False):
    """Save charter data to YAML file"""
    filename = generate_filename()
    filepath = output_dir / filename
    
    if dry_run:
        print("\n" + "=" * 50)
        print("🔍 DRY RUN - 以下の内容が保存されます:")
        print("=" * 50)
        print(yaml.dump(charter_data, default_flow_style=False, allow_unicode=True))
        print(f"📍 保存先: {filepath}")
        return None
    else:
        with open(filepath, 'w', encoding='utf-8') as f:
            yaml.dump(charter_data, f, default_flow_style=False, allow_unicode=True)
        
        print(f"\n✅ チャーターが保存されました: {filepath}")
        return filepath


def main():
    parser = argparse.ArgumentParser(description="Generate project charter from questions")
    parser.add_argument("--dry-run", action="store_true", 
                        help="Print result instead of saving to file")
    args = parser.parse_args()
    
    # File paths
    project_root = Path(__file__).parent.parent
    questions_file = project_root / "data" / "charter_questions.yaml"
    output_dir = project_root / "data" / "charters"
    
    # Validate files exist
    if not questions_file.exists():
        print(f"❌ Questions file not found: {questions_file}")
        sys.exit(1)
    
    # Ensure output directory exists
    output_dir.mkdir(parents=True, exist_ok=True)
    
    try:
        # Load questions and collect answers
        questions = load_questions(questions_file)
        charter_data = collect_answers(questions)
        
        # Save or print result
        save_charter(charter_data, output_dir, dry_run=args.dry_run)
        
    except KeyboardInterrupt:
        print("\n\n❌ 中断されました")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ エラーが発生しました: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()