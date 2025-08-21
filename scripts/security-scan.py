#!/usr/bin/env python3
"""
Security scanning script for studiorum project.

This script runs comprehensive security checks including:
- Dependency vulnerability scanning with pip-audit
- Static code analysis with bandit
- Basic secret detection patterns

Usage: python scripts/security-scan.py [--fix] [--report]
"""

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any


def run_command(
    cmd: list[str], capture_output: bool = True
) -> subprocess.CompletedProcess:
    """Run a command and return the result."""
    print(f"🔄 Running: {' '.join(cmd)}")
    try:
        result = subprocess.run(
            cmd, capture_output=capture_output, text=True, check=False
        )
        return result
    except FileNotFoundError:
        print(f"❌ Command not found: {cmd[0]}")
        print(f"💡 Install missing tool: {cmd[0]}")
        sys.exit(1)


def check_pip_audit() -> dict[str, Any]:
    """Run pip-audit for dependency vulnerabilities."""
    print("\n🔒 Checking for dependency vulnerabilities...")

    result = run_command(["pip-audit", "--format=json", "--desc=off"])

    try:
        if result.stdout:
            audit_data = json.loads(result.stdout)
            # Extract vulnerabilities from pip-audit format
            all_vulns = []
            for dep in audit_data.get("dependencies", []):
                for vuln in dep.get("vulns", []):
                    all_vulns.append(
                        {
                            "package": dep.get("name", "unknown"),
                            "version": dep.get("version", "unknown"),
                            "vulnerability": vuln.get("description", "No description"),
                            "id": vuln.get("id", ""),
                            "fix_versions": vuln.get("fix_versions", []),
                        }
                    )

            if not all_vulns:
                print("✅ No known vulnerabilities found in dependencies")
                return {"status": "clean", "vulnerabilities": []}
            else:
                print(f"⚠️  Found {len(all_vulns)} vulnerabilities")
                for vuln in all_vulns:
                    print(f"   - {vuln['package']}: {vuln['vulnerability']}")
                return {"status": "vulnerable", "vulnerabilities": all_vulns}
        else:
            print("✅ No known vulnerabilities found in dependencies")
            return {"status": "clean", "vulnerabilities": []}
    except json.JSONDecodeError:
        print("❌ Failed to parse pip-audit output")
        print(result.stdout)
        print(result.stderr)
        return {"status": "error", "vulnerabilities": []}


def check_bandit() -> dict[str, Any]:
    """Run bandit for static security analysis."""
    print("\n🔍 Running static security analysis...")

    result = run_command(["bandit", "-r", "src/", "-f", "json", "-q"])

    try:
        if result.stdout:
            report = json.loads(result.stdout)
            issues = report.get("results", [])

            if not issues:
                print("✅ No security issues found in code")
                return {"status": "clean", "issues": []}
            else:
                print(f"⚠️  Found {len(issues)} potential security issues")
                for issue in issues:
                    print(
                        f"   - {issue.get('filename', 'unknown')}: {issue.get('test_name', 'unknown')}"
                    )
                return {"status": "issues", "issues": issues}
        else:
            print("✅ No security issues found in code")
            return {"status": "clean", "issues": []}
    except json.JSONDecodeError as e:
        print("❌ Failed to parse bandit output")
        print(f"JSON decode error: {e}")
        print("Raw stdout:")
        print(
            result.stdout[:500] + "..." if len(result.stdout) > 500 else result.stdout
        )
        return {"status": "error", "issues": []}


def check_secrets() -> dict[str, Any]:
    """Basic secret detection in source files."""
    print("\n🕵️  Scanning for potential secrets...")

    # Common secret patterns
    patterns = [
        (r'password\s*=\s*["\'][^"\']{8,}["\']', "Hardcoded password"),
        (r'api_key\s*=\s*["\'][^"\']{16,}["\']', "API key"),
        (r'secret\s*=\s*["\'][^"\']{16,}["\']', "Secret key"),
        (r'token\s*=\s*["\'][^"\']{16,}["\']', "Token"),
        (r'["\'][A-Za-z0-9]{32,}["\']', "Long random string (potential secret)"),
    ]

    issues = []
    src_dir = Path("src")

    if not src_dir.exists():
        print("⚠️  src/ directory not found")
        return {"status": "error", "issues": []}

    for py_file in src_dir.rglob("*.py"):
        try:
            content = py_file.read_text()
            for pattern, description in patterns:
                matches = re.finditer(pattern, content, re.IGNORECASE)
                for match in matches:
                    line_num = content[: match.start()].count("\n") + 1
                    issues.append(
                        {
                            "file": str(py_file),
                            "line": line_num,
                            "description": description,
                            "match": match.group(),
                        }
                    )
        except Exception as e:
            print(f"⚠️  Error reading {py_file}: {e}")

    if not issues:
        print("✅ No potential secrets found")
        return {"status": "clean", "issues": []}
    else:
        print(f"⚠️  Found {len(issues)} potential secrets")
        for issue in issues:
            print(f"   - {issue['file']}:{issue['line']} - {issue['description']}")
        return {"status": "issues", "issues": issues}


def generate_report(results: dict[str, Any], output_file: str = "security-report.json"):
    """Generate a comprehensive security report."""
    print(f"\n📋 Generating security report: {output_file}")

    report = {
        "timestamp": subprocess.run(
            ["date", "-Iseconds"], capture_output=True, text=True
        ).stdout.strip(),
        "summary": {
            "total_issues": (
                len(results.get("pip_audit", {}).get("vulnerabilities", []))
                + len(results.get("bandit", {}).get("issues", []))
                + len(results.get("secrets", {}).get("issues", []))
            ),
            "dependency_vulnerabilities": len(
                results.get("pip_audit", {}).get("vulnerabilities", [])
            ),
            "code_security_issues": len(results.get("bandit", {}).get("issues", [])),
            "potential_secrets": len(results.get("secrets", {}).get("issues", [])),
        },
        "details": results,
    }

    Path(output_file).write_text(json.dumps(report, indent=2))
    print(f"✅ Report saved to {output_file}")


def main():
    """Main security scanning function."""
    parser = argparse.ArgumentParser(
        description="Run security scans on the studiorum project"
    )
    parser.add_argument("--report", action="store_true", help="Generate JSON report")
    parser.add_argument(
        "--fix", action="store_true", help="Attempt to fix issues where possible"
    )
    args = parser.parse_args()

    print("🛡️  Starting security scan for studiorum project\n")

    results = {}
    exit_code = 0

    # Run all security checks
    results["pip_audit"] = check_pip_audit()
    results["bandit"] = check_bandit()
    results["secrets"] = check_secrets()

    # Determine overall status
    if any(r.get("status") in ["vulnerable", "issues"] for r in results.values()):
        exit_code = 1
        print("\n❌ Security issues found!")
    else:
        print("\n✅ All security checks passed!")

    # Generate report if requested
    if args.report:
        generate_report(results)

    # Attempt fixes if requested
    if args.fix and exit_code != 0:
        print("\n🔧 Attempting to fix issues...")
        if results["pip_audit"]["status"] == "vulnerable":
            print("💡 For dependency vulnerabilities, try: pip install --upgrade")
        if results["bandit"]["status"] == "issues":
            print("💡 Review bandit issues manually - they require code changes")
        if results["secrets"]["status"] == "issues":
            print(
                "💡 Review potential secrets manually - they require careful analysis"
            )

    # Print summary
    total_issues = sum(
        len(r.get("vulnerabilities", [])) + len(r.get("issues", []))
        for r in results.values()
    )

    print(f"\n📊 Summary: {total_issues} total security issues found")
    print("💡 Run with --report to generate detailed JSON report")
    print("💡 Run with --fix for remediation suggestions")

    sys.exit(exit_code)


if __name__ == "__main__":
    main()
