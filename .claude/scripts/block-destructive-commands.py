#!/usr/bin/env python3
"""
PreToolUse Hook: Blocks destructive command-line execution across OS, Git,
Databases, Docker, Kubernetes, Argo, AWS, Terraform, and Airflow.

Regex-based, so this is a speed bump, not a guarantee - quoting, variable
expansion, or wrapper scripts can bypass it.
"""

import json
import sys
import re

BLOCKED_PATTERNS = [
    # 1. Filesystem & OS
    r"rm\s+-[rf]{1,2}.*",                   # Recursive/force file deletion
    r"mkfs\.",                              # Formatting filesystems
    r"dd\s+if=",                            # Direct disk writing
    r">(>)?\s*/dev/(sd|hd|nvme)",           # Overwriting device nodes

    # 2. Git
    r"git\s+reset\s+--hard",                # Hard git resets
    r"git\s+push.*--force",                 # Force pushing to remote
    r"git\s+push\s+.*--delete",             # Deleting a remote branch/tag
    r"git\s+branch\s+-D",                   # Force-deleting a local branch
    r"git\s+clean\s+-[dfx]{1,3}",           # Cleaning untracked files

    # 3. Databases (SQL / NoSQL)
    r"DROP\s+(TABLE|DATABASE|SCHEMA|INDEX)",# SQL destructive drops
    r"TRUNCATE\s+TABLE",                    # SQL table truncation
    r"DELETE\s+FROM",                       # SQL row deletion
    r"ALTER\s+TABLE\s+.*DROP",              # SQL column/constraint dropping
    r"db\..*\.(drop|deleteMany|remove)\(",  # MongoDB bulk deletion

    # 4. Docker & Docker Compose
    r"docker(-compose|\s+compose)?\s+(down|kill|rm|rmi)", # Tearing down stacks or containers
    r"docker\s+(system|volume|image|container|network)\s+(prune|rm)", # Pruning resources

    # 5. Kubernetes (kubectl)
    r"kubectl\s+delete",                    # Deleting k8s resources
    r"kubectl\s+drain",                     # Draining k8s nodes
    r"kubectl\s+replace\s+--force",         # Force replacing resources

    # 6. Argo & ArgoCD
    r"argo(cd)?\s+(app\s+)?delete",         # Deleting Argo apps or workflows
    r"argo\s+terminate",                    # Terminating running workflows
    r"argocd\s+(cluster|repo)\s+rm",        # Removing clusters/repos from ArgoCD
    r"argocd\s+app\s+sync.*--prune",        # Syncing with auto-prune enabled

    # 7. Helm
    r"helm\s+(uninstall|delete)",           # Removing a release

    # 8. Terraform / IaC
    r"terraform\s+destroy",                 # Destroying managed infra
    r"terraform\s+apply\s+.*-destroy",      # Destroy plan applied via apply

    # 9. Cloud CLIs (word-boundaries to avoid matching inside words like
    # "confirm"/"terminate is fine but "firm"/"alarm"/"warm" are not verbs)
    r"aws\s+.*\b(rb|rm|delete|terminate|destroy|purge)\b",

    # 10. Apache Airflow
    r"airflow\s+db\s+(reset|clean|drop-archived)",          # Wiping or purging metadata DB
    r"airflow\s+(dags|connections|variables|pools)\s+delete", # Deleting DAGs, conns, variables, or pools
    r"airflow\s+tasks\s+clear",                             # Clearing task instances (triggers automated re-runs)
]

def main():
    try:
        input_data = json.loads(sys.stdin.read())
    except Exception:
        # Allow execution if stdin fails, avoiding breakage in non-tool contexts
        sys.exit(0)

    tool_name = input_data.get("tool_name", "")
    if tool_name != "Bash":
        sys.exit(0)

    command = input_data.get("tool_input", {}).get("command", "")

    for pattern in BLOCKED_PATTERNS:
        if re.search(pattern, command, re.IGNORECASE):
            response = {
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "permissionDecision": "deny",
                    "permissionDecisionReason": f"BLOCKED BY SECURITY POLICY: The command matched a destructive infrastructure/data pattern ('{pattern}'). Please use a dry-run flag, find a safe alternative, or ask the user to execute this manually."
                }
            }
            print(json.dumps(response))
            sys.exit(0)

    sys.exit(0)

if __name__ == "__main__":
    main()
