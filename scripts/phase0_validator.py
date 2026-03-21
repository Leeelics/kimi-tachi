#!/usr/bin/env python3
"""
Phase 0 完整验证脚本
运行所有检查并生成报告

Usage:
    python scripts/phase0_validator.py [--json] [--output REPORT.md]

Options:
    --json          输出 JSON 格式结果
    --output FILE   将报告保存到文件
"""

import yaml
import glob
import re
import sys
import json
import argparse
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import List, Dict, Optional
from datetime import datetime


@dataclass
class CheckResult:
    name: str
    passed: bool
    message: str
    severity: str  # P0, P1, P2
    category: str  # structure, content, documentation


class Phase0Validator:
    """Phase 0 验证器"""
    
    def __init__(self, base_path: str = "."):
        self.base_path = Path(base_path)
        self.results: List[CheckResult] = []
        self.skills = ["_template", "agent-switcher", "category-router", "kimi-tachi", "todo-enforcer"]
        self.agents = ["kamaji", "shishigami", "nekobasu", "calcifer", "enma", "tasogare", "phoenix"]
        
    def run_all_checks(self) -> bool:
        """运行所有检查"""
        self.check_skill_structure()
        self.check_agent_yaml()
        self.check_anti_patterns()
        self.check_imperative_mood()
        self.check_documentation()
        self.check_character_consistency()
        return all(r.passed for r in self.results if r.severity == "P0")
    
    def check_skill_structure(self):
        """检查 Skill 三级架构"""
        for skill in self.skills:
            skill_file = self.base_path / "skills" / skill / "SKILL.md"
            
            # Check file exists
            if not skill_file.exists():
                self.results.append(CheckResult(
                    f"Skill {skill} exists",
                    False,
                    f"Missing {skill_file}",
                    "P0",
                    "structure"
                ))
                continue
            
            content = skill_file.read_text()
            
            # Check YAML frontmatter
            has_frontmatter = content.startswith("---")
            self.results.append(CheckResult(
                f"{skill}: YAML frontmatter",
                has_frontmatter,
                "OK" if has_frontmatter else "Missing ---",
                "P0",
                "structure"
            ))
            
            # Check required fields in frontmatter
            try:
                # Extract frontmatter
                match = re.match(r'^---\s*\n(.*?)\n---', content, re.DOTALL)
                if match:
                    frontmatter = yaml.safe_load(match.group(1))
                    for field in ["name", "description", "triggers"]:
                        has_field = field in frontmatter if frontmatter else False
                        self.results.append(CheckResult(
                            f"{skill}: frontmatter.{field}",
                            has_field,
                            "OK" if has_field else f"Missing {field}",
                            "P0",
                            "structure"
                        ))
            except Exception as e:
                self.results.append(CheckResult(
                    f"{skill}: frontmatter parse",
                    False,
                    str(e),
                    "P0",
                    "structure"
                ))
            
            # Check L1/L2/L3 in content
            has_l1 = "L1:" in content or "L1" in content
            has_l2 = "L2:" in content or "L2" in content
            has_l3 = "L3:" in content or "L3" in content
            self.results.append(CheckResult(
                f"{skill}: Architecture diagram",
                has_l1 and has_l2 and has_l3,
                f"L1={has_l1}, L2={has_l2}, L3={has_l3}",
                "P1",
                "structure"
            ))
            
            # Check Anti-Patterns section
            has_anti_patterns = "## Anti-Patterns" in content
            self.results.append(CheckResult(
                f"{skill}: Anti-Patterns section",
                has_anti_patterns,
                "OK" if has_anti_patterns else "Missing Anti-Patterns section",
                "P0" if skill != "agent-switcher" else "P1",  # agent-switcher is legacy
                "structure"
            ))
    
    def check_agent_yaml(self):
        """检查 Agent YAML 结构"""
        for agent_name in self.agents:
            agent_file = self.base_path / "agents" / f"{agent_name}.yaml"
            
            if not agent_file.exists():
                self.results.append(CheckResult(
                    f"Agent {agent_name} exists",
                    False,
                    f"Missing {agent_file}",
                    "P0",
                    "structure"
                ))
                continue
            
            try:
                with open(agent_file) as f:
                    data = yaml.safe_load(f)
                
                # Check required fields
                checks = [
                    ("version" in data, "version field", "P0"),
                    ("agent" in data, "agent field", "P0"),
                    ("system_prompt_args" in data.get("agent", {}), "system_prompt_args", "P0"),
                ]
                
                for passed, name, severity in checks:
                    self.results.append(CheckResult(
                        f"{agent_name}: {name}",
                        passed,
                        "OK" if passed else f"Missing {name}",
                        severity,
                        "structure"
                    ))
                
                # Check Anti-Patterns
                spa = data.get("agent", {}).get("system_prompt_args", {})
                role_additional = spa.get("ROLE_ADDITIONAL", "")
                has_anti_patterns = "Anti-Pattern" in role_additional or "絶対にやるな" in role_additional
                self.results.append(CheckResult(
                    f"{agent_name}: Anti-Patterns section",
                    has_anti_patterns,
                    "OK" if has_anti_patterns else "Missing Anti-Patterns",
                    "P0",
                    "content"
                ))
                
                # Check subagents: {} for non-kamaji
                if agent_name != "kamaji":
                    subagents = data.get("subagents")
                    has_empty_subagents = subagents == {}
                    self.results.append(CheckResult(
                        f"{agent_name}: subagents: {{}}",
                        has_empty_subagents,
                        "OK" if has_empty_subagents else f"Got {subagents}",
                        "P0",
                        "structure"
                    ))
                
                # Check for ROLE
                has_role = "ROLE" in spa
                self.results.append(CheckResult(
                    f"{agent_name}: ROLE defined",
                    has_role,
                    "OK" if has_role else "Missing ROLE",
                    "P0",
                    "structure"
                ))
                
            except yaml.YAMLError as e:
                self.results.append(CheckResult(
                    f"{agent_name}: YAML valid",
                    False,
                    str(e),
                    "P0",
                    "structure"
                ))
    
    def check_anti_patterns(self):
        """检查反模式数量和质量"""
        for agent_name in self.agents:
            agent_file = self.base_path / "agents" / f"{agent_name}.yaml"
            
            if not agent_file.exists():
                continue
            
            try:
                with open(agent_file) as f:
                    data = yaml.safe_load(f)
                
                spa = data.get("agent", {}).get("system_prompt_args", {})
                role_additional = spa.get("ROLE_ADDITIONAL", "")
                
                # Count table rows in ROLE_ADDITIONAL - exclude separator lines
                table_rows = len(re.findall(r'\|[^-\n].*\|.*\|.*\|', role_additional))
                
                # Expect at least 4 anti-patterns (excluding header and separator)
                has_enough = table_rows >= 4
                
                self.results.append(CheckResult(
                    f"{agent_name}: Anti-Pattern count",
                    has_enough,
                    f"Found {table_rows} rows (min: 4)",
                    "P1",
                    "content"
                ))
            except Exception as e:
                self.results.append(CheckResult(
                    f"{agent_name}: Anti-Pattern count",
                    False,
                    f"Error: {e}",
                    "P1",
                    "content"
                ))
    
    def check_imperative_mood(self):
        """检查祈使语气"""
        imperative_keywords = [
            "Analyze", "Search", "Implement", "Review", "Explore", 
            "Create", "Check", "Verify", "Report", "Delegate",
            "Synthesize", "Jump", "Follow", "Light", "Take",
            "漫步", "搜索", "实现", "审查", "探索",
            "检查", "验证", "报告", "委派", "综合",
            # shishigami keywords
            "Walk", "Feel", "Predict", "Speak", "Observe", "Listen",
            "漫步", "感受", "预测", "言说", "观察", "倾听",
            # phoenix keywords
            "Remember", "Record", "Connect", "Explain", "Witness",
            "记忆", "记录", "连接", "解释", "见证"
        ]
        descriptive_patterns = [
            r"\bI will\b", r"\bI am\b", r"\bMy job\b",
            r"\bI think\b", r"\bI believe\b"
        ]
        
        for agent_name in self.agents:
            agent_file = self.base_path / "agents" / f"{agent_name}.yaml"
            
            if not agent_file.exists():
                continue
            
            try:
                with open(agent_file) as f:
                    data = yaml.safe_load(f)
                
                spa = data.get("agent", {}).get("system_prompt_args", {})
                role_additional = spa.get("ROLE_ADDITIONAL", "")
                
                # Count imperative keywords in ROLE_ADDITIONAL
                imperative_count = sum(len(re.findall(kw, role_additional)) for kw in imperative_keywords)
                
                # Count descriptive patterns
                descriptive_count = sum(len(re.findall(p, role_additional, re.IGNORECASE)) for p in descriptive_patterns)
                
                # Score: more imperative, less descriptive is better
                score = imperative_count - descriptive_count * 2
                passed = score > 0 or imperative_count >= 3
                
                self.results.append(CheckResult(
                    f"{agent_name}: Imperative mood",
                    passed,
                    f"Imperative: {imperative_count}, Descriptive: {descriptive_count}",
                    "P1",
                    "content"
                ))
            except Exception as e:
                self.results.append(CheckResult(
                    f"{agent_name}: Imperative mood",
                    False,
                    f"Error: {e}",
                    "P1",
                    "content"
                ))
    
    def check_documentation(self):
        """检查文档完整性"""
        required_docs = [
            ("docs/ANTI_PATTERNS.md", "P0"),
            ("docs/AGENTS.md", "P0"),
            ("docs/DOCUMENTATION_INDEX.md", "P1"),
            ("docs/VISION.md", "P1"),
            ("docs/ROADMAP.md", "P1"),
        ]
        
        for doc, severity in required_docs:
            doc_path = self.base_path / doc
            exists = doc_path.exists()
            self.results.append(CheckResult(
                f"Documentation: {Path(doc).name}",
                exists,
                "OK" if exists else "Missing",
                severity,
                "documentation"
            ))
        
        # Check if ANTI_PATTERNS.md has all agents
        anti_patterns_doc = self.base_path / "docs" / "ANTI_PATTERNS.md"
        if anti_patterns_doc.exists():
            content = anti_patterns_doc.read_text()
            for agent in self.agents:
                has_agent = agent in content
                self.results.append(CheckResult(
                    f"ANTI_PATTERNS.md: includes {agent}",
                    has_agent,
                    "OK" if has_agent else f"Missing {agent}",
                    "P1",
                    "documentation"
                ))
    
    def check_character_consistency(self):
        """检查角色一致性"""
        character_metaphors = {
            "kamaji": ["boiler", "worker", "work", "bathhouse"],
            "shishigami": ["forest", "season", "life", "nature"],
            "nekobasu": ["cat", "bus", "speed", "nya"],
            "calcifer": ["fire", "burn", "castle", "flame"],
            "enma": ["judge", "heaven", "hell", "sin"],
            "tasogare": ["twilight", "world", "connect", "dusk"],
            "phoenix": ["eternal", "memory", "rebirth", "time"],
        }
        
        for agent_name, metaphors in character_metaphors.items():
            agent_file = self.base_path / "agents" / f"{agent_name}.yaml"
            
            if not agent_file.exists():
                continue
                
            content = agent_file.read_text().lower()
            
            # Count metaphor usage
            metaphor_count = sum(1 for m in metaphors if m.lower() in content)
            has_metaphors = metaphor_count >= 2
            
            self.results.append(CheckResult(
                f"{agent_name}: Character metaphors",
                has_metaphors,
                f"Found {metaphor_count}/{len(metaphors)} metaphors",
                "P1",
                "content"
            ))
    
    def generate_report(self) -> str:
        """生成 Markdown 检查报告"""
        lines = ["# Phase 0 验证报告", ""]
        lines.append(f"*生成时间: {datetime.now().isoformat()}*")
        lines.append("")
        
        # Summary
        lines.append("## 汇总")
        lines.append("")
        
        total = len(self.results)
        passed = sum(1 for r in self.results if r.passed)
        p0_total = sum(1 for r in self.results if r.severity == "P0")
        p0_passed = sum(1 for r in self.results if r.severity == "P0" and r.passed)
        p1_total = sum(1 for r in self.results if r.severity == "P1")
        p1_passed = sum(1 for r in self.results if r.severity == "P1" and r.passed)
        
        lines.append(f"| 指标 | 数值 |")
        lines.append(f"|------|------|")
        lines.append(f"| 总检查项 | {total} |")
        lines.append(f"| 通过 | {passed} ({passed/total*100:.1f}%) |")
        lines.append(f"| P0 检查项 | {p0_total} |")
        p0_pct = f"{p0_passed/p0_total*100:.1f}%" if p0_total > 0 else "N/A"
        lines.append(f"| P0 通过 | {p0_passed} ({p0_pct}) |")
        lines.append(f"| P1 检查项 | {p1_total} |")
        p1_pct = f"{p1_passed/p1_total*100:.1f}%" if p1_total > 0 else "N/A"
        lines.append(f"| P1 通过 | {p1_passed} ({p1_pct}) |")
        lines.append("")
        
        # Grade
        if p0_passed == p0_total and p1_passed >= p1_total * 0.9:
            grade = "A (优秀)"
        elif p0_passed == p0_total and p1_passed >= p1_total * 0.8:
            grade = "B (良好)"
        elif p0_passed >= p0_total * 0.9 and p1_passed >= p1_total * 0.7:
            grade = "C (及格)"
        else:
            grade = "D (不及格)"
        
        lines.append(f"**总体评级: {grade}**")
        lines.append("")
        
        # Group by category
        lines.append("## 按类别详细结果")
        lines.append("")
        
        categories = ["structure", "content", "documentation"]
        category_names = {
            "structure": "结构验证",
            "content": "内容质量",
            "documentation": "文档完整性"
        }
        
        for category in categories:
            cat_results = [r for r in self.results if r.category == category]
            if not cat_results:
                continue
                
            lines.append(f"### {category_names.get(category, category)}")
            lines.append("")
            
            failed = [r for r in cat_results if not r.passed]
            passed_items = [r for r in cat_results if r.passed]
            
            if failed:
                lines.append("**❌ 失败的检查:**")
                for r in failed:
                    lines.append(f"- [{r.severity}] {r.name}: {r.message}")
                lines.append("")
            
            if passed_items:
                lines.append(f"**✅ 通过的检查 ({len(passed_items)} 项):**")
                for r in passed_items:
                    lines.append(f"- [{r.severity}] {r.name}: {r.message}")
                lines.append("")
        
        # Recommendations
        failed_p0 = [r for r in self.results if not r.passed and r.severity == "P0"]
        if failed_p0:
            lines.append("## 需要修复的 P0 问题")
            lines.append("")
            for r in failed_p0:
                lines.append(f"- [ ] {r.name}: {r.message}")
            lines.append("")
        
        return "\n".join(lines)
    
    def generate_json(self) -> str:
        """生成 JSON 格式结果"""
        return json.dumps({
            "timestamp": datetime.now().isoformat(),
            "results": [asdict(r) for r in self.results],
            "summary": {
                "total": len(self.results),
                "passed": sum(1 for r in self.results if r.passed),
                "failed": sum(1 for r in self.results if not r.passed),
                "p0_passed": sum(1 for r in self.results if r.severity == "P0" and r.passed),
                "p0_total": sum(1 for r in self.results if r.severity == "P0"),
            }
        }, indent=2, ensure_ascii=False)


def main():
    parser = argparse.ArgumentParser(description="Phase 0 验证脚本")
    parser.add_argument("--json", action="store_true", help="输出 JSON 格式")
    parser.add_argument("--output", "-o", help="输出文件路径")
    parser.add_argument("--base-path", "-b", default=".", help="项目根目录")
    args = parser.parse_args()
    
    validator = Phase0Validator(base_path=args.base_path)
    success = validator.run_all_checks()
    
    if args.json:
        output = validator.generate_json()
    else:
        output = validator.generate_report()
    
    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(output)
        print(f"报告已保存到: {args.output}")
    else:
        print(output)
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
