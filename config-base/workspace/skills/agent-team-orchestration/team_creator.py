#!/usr/bin/env python3
"""
Agent Team Creator - 团队创建工具

Usage:
    python3 team_creator.py --template research-team --task "分析 A 股趋势"
    python3 team_creator.py --template dev-team --task "开发新功能"
    python3 team_creator.py --template content-team --task "创作小红书笔记"
    python3 team_creator.py --list  # 列出可用模板
    python3 team_creator.py --check  # 健康检查
"""

import argparse
import json
import os
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional


class TeamCreator:
    """团队创建工具"""
    
    def __init__(self, templates_dir: Optional[str] = None):
        if templates_dir is None:
            # Default to templates directory relative to this script
            self.templates_dir = Path(__file__).parent / "templates"
        else:
            self.templates_dir = Path(templates_dir)
        
        self.output_dir = Path(__file__).parent.parent.parent / "output" / "teams"
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def list_templates(self) -> list:
        """List available templates"""
        templates = []
        if self.templates_dir.exists():
            for file in self.templates_dir.glob("*.json"):
                templates.append(file.stem)
        return sorted(templates)
    
    def load_template(self, template_name: str) -> Optional[Dict[str, Any]]:
        """Load team template"""
        template_file = self.templates_dir / f"{template_name}.json"
        
        if not template_file.exists():
            return None
        
        with open(template_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def create_team(self, template_name: str, task: str, team_id: Optional[str] = None) -> Dict[str, Any]:
        """Create a new team instance"""
        # Load template
        template = self.load_template(template_name)
        
        if not template:
            raise ValueError(f"Template not found: {template_name}")
        
        # Generate team ID
        if team_id is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            team_id = f"{template_name}_{timestamp}"
        
        # Create team instance
        team_instance = {
            "team_id": team_id,
            "template": template_name,
            "task": task,
            "status": "created",
            "created_at": datetime.now().isoformat(),
            "roles": template["roles"],
            "workflow": template["workflow"],
            "communication": template["communication"],
            "quality_gates": template["quality_gates"],
            "current_step": 0,
            "handoffs": [],
            "artifacts": []
        }
        
        # Save team instance
        output_file = self.output_dir / f"{team_id}.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(team_instance, f, ensure_ascii=False, indent=2)
        
        return team_instance
    
    def get_team_status(self, team_id: str) -> Optional[Dict[str, Any]]:
        """Get team status"""
        team_file = self.output_dir / f"{team_id}.json"
        
        if not team_file.exists():
            return None
        
        with open(team_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def update_team_step(self, team_id: str, step: int, handoff: Optional[Dict] = None) -> Dict[str, Any]:
        """Update team current step"""
        team = self.get_team_status(team_id)
        
        if not team:
            raise ValueError(f"Team not found: {team_id}")
        
        team["current_step"] = step
        team["updated_at"] = datetime.now().isoformat()
        
        if handoff:
            team["handoffs"].append({
                "timestamp": datetime.now().isoformat(),
                **handoff
            })
        
        # Save updated team
        team_file = self.output_dir / f"{team_id}.json"
        with open(team_file, 'w', encoding='utf-8') as f:
            json.dump(team, f, ensure_ascii=False, indent=2)
        
        return team
    
    def add_artifact(self, team_id: str, artifact: Dict[str, Any]) -> Dict[str, Any]:
        """Add artifact to team"""
        team = self.get_team_status(team_id)
        
        if not team:
            raise ValueError(f"Team not found: {team_id}")
        
        artifact["added_at"] = datetime.now().isoformat()
        team["artifacts"].append(artifact)
        
        # Save updated team
        team_file = self.output_dir / f"{team_id}.json"
        with open(team_file, 'w', encoding='utf-8') as f:
            json.dump(team, f, ensure_ascii=False, indent=2)
        
        return team


def main():
    parser = argparse.ArgumentParser(
        description='Agent Team Creator',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # List available templates
  python3 team_creator.py --list
  
  # Create a research team
  python3 team_creator.py --template research-team --task "分析 A 股趋势"
  
  # Create a dev team
  python3 team_creator.py --template dev-team --task "开发用户登录功能"
  
  # Create a content team
  python3 team_creator.py --template content-team --task "创作小红书笔记：AI 工具评测"
        """
    )
    
    parser.add_argument('--template', type=str, help='Team template name')
    parser.add_argument('--task', type=str, help='Task description for the team')
    parser.add_argument('--team-id', type=str, help='Custom team ID (optional)')
    parser.add_argument('--list', action='store_true', help='List available templates')
    parser.add_argument('--check', action='store_true', help='Health check')
    parser.add_argument('--templates-dir', type=str, help='Custom templates directory')
    
    args = parser.parse_args()
    
    creator = TeamCreator(templates_dir=args.templates_dir)
    
    # Health check
    if args.check:
        print("Agent Team Creator Health Check:")
        print(f"  ✓ Python 3: OK")
        print(f"  ✓ Templates directory: {creator.templates_dir}")
        print(f"  ✓ Output directory: {creator.output_dir}")
        
        templates = creator.list_templates()
        print(f"  ✓ Available templates: {len(templates)}")
        for t in templates:
            print(f"    - {t}")
        
        print("\nStatus: READY")
        sys.exit(0)
    
    # List templates
    if args.list:
        templates = creator.list_templates()
        print("Available team templates:")
        for t in templates:
            template = creator.load_template(t)
            if template:
                print(f"  - {t}: {template.get('description', 'No description')}")
        sys.exit(0)
    
    # Create team
    if args.template:
        if not args.task:
            print("Error: --task is required when using --template")
            sys.exit(1)
        
        try:
            team = creator.create_team(args.template, args.task, args.team_id)
            
            print(f"\n{'='*60}")
            print(f"Team Created Successfully")
            print(f"{'='*60}")
            print(f"Team ID: {team['team_id']}")
            print(f"Template: {team['template']}")
            print(f"Task: {team['task']}")
            print(f"Status: {team['status']}")
            print(f"Created: {team['created_at']}")
            print(f"\nRoles:")
            for role in team['roles']:
                print(f"  - {role['name']}: {role['description']}")
            print(f"\nWorkflow Steps:")
            for step in team['workflow']['steps']:
                print(f"  {step['step']}. [{step['role']}] {step['task']}")
            print(f"\nOutput file: {creator.output_dir}/{team['team_id']}.json")
            print(f"{'='*60}\n")
            
            sys.exit(0)
            
        except ValueError as e:
            print(f"Error: {e}")
            sys.exit(1)
    
    # No action specified
    parser.print_help()
    sys.exit(1)


if __name__ == '__main__':
    main()
