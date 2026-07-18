#!/usr/bin/env python3
"""Fail-closed Claude Code policy and deterministic output-rewrite hook."""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any


HOOKS_DIR = Path(__file__).resolve().parent
CONFIG_UNLOCK_ENV = "CLAUDE_CONFIG_UNLOCK"
LARGE_READ_BYTES = 128 * 1024
MAX_READ_LINES = 400
MAX_SINGLE_LINE_BYTES = 16 * 1024

LEVELS = {"critical": 1, "high": 2, "strict": 3}
SAFETY_LEVEL = "high"

PROTECTED_CONFIG_PARTS = (
    "hooks",
    "scripts",
    "rules",
    "skills",
)
PROTECTED_CONFIG_FILES = {
    "CLAUDE.md",
    "RTK.md",
    "settings.json",
    "settings.local.json",
    "statusline.sh",
}

KNOWN_EXECUTABLES = (
    "rm",
    "git",
    "find",
    "rsync",
    "diskutil",
    "gcloud",
    "redis-cli",
    "gh",
    "glab",
    "cat",
    "less",
    "head",
    "tail",
    "more",
    "bat",
    "view",
    "sed",
    "awk",
    "grep",
    "rg",
    "perl",
    "python",
    "python3",
    "ruby",
    "node",
    "mvn",
    "mvnw",
)

# --- protect-secrets ---

ALLOWLIST = (
    re.compile(r"\.env\.example$", re.IGNORECASE),
    re.compile(r"\.env\.sample$", re.IGNORECASE),
    re.compile(r"\.env\.template$", re.IGNORECASE),
    re.compile(r"\.env\.schema$", re.IGNORECASE),
    re.compile(r"\.env\.defaults$", re.IGNORECASE),
    re.compile(r"env\.example$", re.IGNORECASE),
    re.compile(r"example\.env$", re.IGNORECASE),
)

SENSITIVE_FILES = (
    # CRITICAL
    {"level": "critical", "id": "env-file", "regex": re.compile(r"(?:^|/)\.env(?:\.[^/]*)?$"), "reason": ".env file contains secrets"},
    {"level": "critical", "id": "envrc", "regex": re.compile(r"(?:^|/)\.envrc$"), "reason": ".envrc (direnv) contains secrets"},
    {"level": "critical", "id": "ssh-private-key", "regex": re.compile(r"(?:^|/)\.ssh/id_[^/]+$"), "reason": "SSH private key"},
    {"level": "critical", "id": "ssh-private-key-2", "regex": re.compile(r"(?:^|/)(id_rsa|id_ed25519|id_ecdsa|id_dsa)$"), "reason": "SSH private key"},
    {"level": "critical", "id": "ssh-authorized", "regex": re.compile(r"(?:^|/)\.ssh/authorized_keys$"), "reason": "SSH authorized_keys"},
    {"level": "critical", "id": "aws-credentials", "regex": re.compile(r"(?:^|/)\.aws/credentials$"), "reason": "AWS credentials file"},
    {"level": "critical", "id": "aws-config", "regex": re.compile(r"(?:^|/)\.aws/config$"), "reason": "AWS config may contain secrets"},
    {"level": "critical", "id": "kube-config", "regex": re.compile(r"(?:^|/)\.kube/config$"), "reason": "Kubernetes config contains credentials"},
    {"level": "critical", "id": "pem-key", "regex": re.compile(r"\.pem$", re.IGNORECASE), "reason": "PEM key file"},
    {"level": "critical", "id": "key-file", "regex": re.compile(r"\.key$", re.IGNORECASE), "reason": "Key file"},
    {"level": "critical", "id": "p12-key", "regex": re.compile(r"\.(p12|pfx)$", re.IGNORECASE), "reason": "PKCS12 key file"},
    # HIGH
    {"level": "high", "id": "credentials-json", "regex": re.compile(r"(?:^|/)credentials\.json$", re.IGNORECASE), "reason": "Credentials file"},
    {"level": "high", "id": "secrets-file", "regex": re.compile(r"(?:^|/)(secrets?|credentials?)\.(json|ya?ml|toml)$", re.IGNORECASE), "reason": "Secrets configuration file"},
    {"level": "high", "id": "service-account", "regex": re.compile(r"service[_-]?account.*\.json$", re.IGNORECASE), "reason": "GCP service account key"},
    {"level": "high", "id": "gcloud-creds", "regex": re.compile(r"(?:^|/)\.config/gcloud/.*(credentials|tokens)", re.IGNORECASE), "reason": "GCloud credentials"},
    {"level": "high", "id": "azure-creds", "regex": re.compile(r"(?:^|/)\.azure/(credentials|accessTokens)", re.IGNORECASE), "reason": "Azure credentials"},
    {"level": "high", "id": "docker-config", "regex": re.compile(r"(?:^|/)\.docker/config\.json$"), "reason": "Docker config may contain registry auth"},
    {"level": "high", "id": "netrc", "regex": re.compile(r"(?:^|/)\.netrc$"), "reason": ".netrc contains credentials"},
    {"level": "high", "id": "npmrc", "regex": re.compile(r"(?:^|/)\.npmrc$"), "reason": ".npmrc may contain auth tokens"},
    {"level": "high", "id": "pypirc", "regex": re.compile(r"(?:^|/)\.pypirc$"), "reason": ".pypirc contains PyPI credentials"},
    {"level": "high", "id": "gem-creds", "regex": re.compile(r"(?:^|/)\.gem/credentials$"), "reason": "RubyGems credentials"},
    {"level": "high", "id": "vault-token", "regex": re.compile(r"(?:^|/)(\.vault-token|vault-token)$"), "reason": "Vault token file"},
    {"level": "high", "id": "keystore", "regex": re.compile(r"\.(keystore|jks)$", re.IGNORECASE), "reason": "Java keystore"},
    {"level": "high", "id": "htpasswd", "regex": re.compile(r"(?:^|/)\.?htpasswd$"), "reason": "htpasswd contains hashed passwords"},
    {"level": "high", "id": "pgpass", "regex": re.compile(r"(?:^|/)\.pgpass$"), "reason": "PostgreSQL password file"},
    {"level": "high", "id": "my-cnf", "regex": re.compile(r"(?:^|/)\.my\.cnf$"), "reason": "MySQL config may contain password"},
    # STRICT
    {"level": "strict", "id": "database-config", "regex": re.compile(r"(?:^|/)(?:config/)?database\.(json|ya?ml)$", re.IGNORECASE), "reason": "Database config may contain passwords"},
    {"level": "strict", "id": "ssh-known-hosts", "regex": re.compile(r"(?:^|/)\.ssh/known_hosts$"), "reason": "SSH known_hosts reveals infrastructure"},
    {"level": "strict", "id": "gitconfig", "regex": re.compile(r"(?:^|/)\.gitconfig$"), "reason": ".gitconfig may contain credentials"},
    {"level": "strict", "id": "curlrc", "regex": re.compile(r"(?:^|/)\.curlrc$"), "reason": ".curlrc may contain auth"},
)

BASH_PATTERNS = (
    # CRITICAL
    {"level": "critical", "id": "cat-env", "regex": re.compile(r"\b(cat|less|head|tail|more|bat|view)\s+[^|;]*\.env\b", re.IGNORECASE), "reason": "Reading .env file exposes secrets"},
    {"level": "critical", "id": "cat-ssh-key", "regex": re.compile(r"\b(cat|less|head|tail|more|bat)\s+[^|;]*(id_rsa|id_ed25519|id_ecdsa|id_dsa|\.pem|\.key)\b", re.IGNORECASE), "reason": "Reading private key"},
    {"level": "critical", "id": "cat-aws-creds", "regex": re.compile(r"\b(cat|less|head|tail|more)\s+[^|;]*\.aws/credentials", re.IGNORECASE), "reason": "Reading AWS credentials"},
    # HIGH - Environment exposure
    {"level": "high", "id": "env-dump", "regex": re.compile(r"\bprintenv\b|(?:^|[;&|]\s*)env\s*(?:$|[;&|])"), "reason": "Environment dump may expose secrets"},
    {"level": "high", "id": "echo-secret-var", "regex": re.compile(r"\becho\b[^;|&]*\$\{?[A-Za-z_]*(?:SECRET|KEY|TOKEN|PASSWORD|PASSW|CREDENTIAL|API_KEY|AUTH|PRIVATE)[A-Za-z_]*\}?", re.IGNORECASE), "reason": "Echoing secret variable"},
    {"level": "high", "id": "printf-secret-var", "regex": re.compile(r"\bprintf\b[^;|&]*\$\{?[A-Za-z_]*(?:SECRET|KEY|TOKEN|PASSWORD|CREDENTIAL|API_KEY|AUTH|PRIVATE)[A-Za-z_]*\}?", re.IGNORECASE), "reason": "Printing secret variable"},
    {"level": "high", "id": "cat-secrets-file", "regex": re.compile(r"\b(cat|less|head|tail|more)\s+[^|;]*(credentials?|secrets?)\.(json|ya?ml|toml)", re.IGNORECASE), "reason": "Reading secrets file"},
    {"level": "high", "id": "cat-netrc", "regex": re.compile(r"\b(cat|less|head|tail|more)\s+[^|;]*\.netrc", re.IGNORECASE), "reason": "Reading .netrc credentials"},
    {"level": "high", "id": "source-env", "regex": re.compile(r"\bsource\s+[^|;]*\.env\b|(?:^|[;&|]\s*)\.\s+[^|;]*\.env\b|^\.\s+[^|;]*\.env\b", re.IGNORECASE), "reason": "Sourcing .env loads secrets"},
    {"level": "high", "id": "export-cat-env", "regex": re.compile(r"export\s+.*\$\(cat\s+[^)]*\.env", re.IGNORECASE), "reason": "Exporting secrets from .env"},
    # HIGH - Exfiltration
    {"level": "high", "id": "curl-upload-env", "regex": re.compile(r"\bcurl\b[^;|&]*(-d\s*@|-F\s*[^=]+=@|--data[^=]*=@)[^;|&]*(\.env|credentials|secrets|id_rsa|\.pem|\.key)", re.IGNORECASE), "reason": "Uploading secrets via curl"},
    {"level": "high", "id": "curl-post-secrets", "regex": re.compile(r"\bcurl\b[^;|&]*-X\s*POST[^;|&]*[^;|&]*(\.env|credentials|secrets)", re.IGNORECASE), "reason": "POSTing secrets via curl"},
    {"level": "high", "id": "wget-post-secrets", "regex": re.compile(r"\bwget\b[^;|&]*--post-file[^;|&]*(\.env|credentials|secrets)", re.IGNORECASE), "reason": "POSTing secrets via wget"},
    {"level": "high", "id": "scp-secrets", "regex": re.compile(r"\bscp\b[^;|&]*(\.env|credentials|secrets|id_rsa|\.pem|\.key)[^;|&]+:", re.IGNORECASE), "reason": "Copying secrets via scp"},
    {"level": "high", "id": "rsync-secrets", "regex": re.compile(r"\brsync\b[^;|&]*(\.env|credentials|secrets|id_rsa)[^;|&]+:", re.IGNORECASE), "reason": "Syncing secrets via rsync"},
    {"level": "high", "id": "nc-secrets", "regex": re.compile(r"\bnc\b[^;|&]*<[^;|&]*(\.env|credentials|secrets|id_rsa)", re.IGNORECASE), "reason": "Exfiltrating secrets via netcat"},
    # HIGH - Copy/move/delete secrets
    {"level": "high", "id": "cp-env", "regex": re.compile(r"\bcp\b[^;|&]*\.env\b", re.IGNORECASE), "reason": "Copying .env file"},
    {"level": "high", "id": "cp-ssh-key", "regex": re.compile(r"\bcp\b[^;|&]*(id_rsa|id_ed25519|\.pem|\.key)\b", re.IGNORECASE), "reason": "Copying private key"},
    {"level": "high", "id": "mv-env", "regex": re.compile(r"\bmv\b[^;|&]*\.env\b", re.IGNORECASE), "reason": "Moving .env file"},
    {"level": "high", "id": "rm-ssh-key", "regex": re.compile(r"\brm\b[^;|&]*(id_rsa|id_ed25519|id_ecdsa|authorized_keys)", re.IGNORECASE), "reason": "Deleting SSH key"},
    {"level": "high", "id": "rm-env", "regex": re.compile(r"\brm\b.*\.env\b", re.IGNORECASE), "reason": "Deleting .env file"},
    {"level": "high", "id": "rm-aws-creds", "regex": re.compile(r"\brm\b[^;|&]*\.aws/credentials", re.IGNORECASE), "reason": "Deleting AWS credentials"},
    {"level": "high", "id": "truncate-secrets", "regex": re.compile(r"\btruncate\b.*\.(env|pem|key)\b|(?:^|[;&|]\s*)>\s*\.env\b", re.IGNORECASE), "reason": "Truncating secrets file"},
    # HIGH - Process environ
    {"level": "high", "id": "proc-environ", "regex": re.compile(r"/proc/[^/]*/environ"), "reason": "Reading process environment"},
    {"level": "high", "id": "xargs-cat-env", "regex": re.compile(r"xargs.*cat|\.env.*xargs", re.IGNORECASE), "reason": "Reading .env via xargs"},
    {"level": "high", "id": "find-exec-cat-env", "regex": re.compile(r"find\b.*\.env.*-exec|find\b.*-exec.*(cat|less)", re.IGNORECASE), "reason": "Finding and reading .env files"},
    # STRICT
    {"level": "strict", "id": "grep-password", "regex": re.compile(r"\bgrep\b[^|;]*(-r|--recursive)[^|;]*(password|secret|api.?key|token|credential)", re.IGNORECASE), "reason": "Grep for secrets may expose them"},
    {"level": "strict", "id": "base64-secrets", "regex": re.compile(r"\bbase64\b[^|;]*(\.env|credentials|secrets|id_rsa|\.pem)", re.IGNORECASE), "reason": "Base64 encoding secrets"},
)

# Fast-path sentinel: if none of these tokens appear in a Bash command, no
# BASH_PATTERNS entry can match.
BASH_SENTINELS = re.compile(
    r"\.env\b|(?:id_rsa|id_ed25519|id_ecdsa|id_dsa)\b|authorized_keys|"
    r"\.aws/credentials|\.pem\b|\.key\b|\.netrc|printenv|/proc/"
    r"|SECRET|KEY|TOKEN|PASSWORD|PASSW|CREDENTIAL|API_KEY|AUTH|PRIVATE"
    r"|credential|secret",
    re.IGNORECASE,
)

# --- block-dangerous-commands ---

DANGEROUS_PATTERNS = (
    # CRITICAL
    {"level": "critical", "id": "rm-home", "regex": re.compile(r"\brm\s+(-.+\s+)*[\"']?~/?[\"']?(\s|$|[;&|])"), "reason": "rm targeting home directory"},
    {"level": "critical", "id": "rm-home-var", "regex": re.compile(r"\brm\s+(-.+\s+)*[\"']?\$HOME[\"']?(\s|$|[;&|])"), "reason": "rm targeting $HOME"},
    {"level": "critical", "id": "rm-home-trailing", "regex": re.compile(r"\brm\s+.+\s+[\"']?(~/?|\$HOME)[\"']?(\s*$|[;&|])"), "reason": "rm with trailing ~/ or $HOME"},
    {"level": "critical", "id": "rm-root", "regex": re.compile(r"\brm\s+(-.+\s+)*/(\*|\s|$|[;&|])"), "reason": "rm targeting root filesystem"},
    {"level": "critical", "id": "rm-system", "regex": re.compile(r"\brm\s+(-.+\s+)*/(etc|usr|var|bin|sbin|lib|boot|dev|proc|sys)(/|\s|$)"), "reason": "rm targeting system directory"},
    {"level": "critical", "id": "rm-cwd", "regex": re.compile(r"\brm\s+(-.+\s+)*(\./?|\*|\./\*)(\s|$|[;&|])"), "reason": "rm deleting current directory contents"},
    {"level": "critical", "id": "dd-disk", "regex": re.compile(r"\bdd\b.+of=/dev/(sd[a-z]|nvme|hd[a-z]|vd[a-z]|xvd[a-z])"), "reason": "dd writing to disk device"},
    {"level": "critical", "id": "mkfs", "regex": re.compile(r"\bmkfs(\.\w+)?\s+/dev/(sd[a-z]|nvme|hd[a-z]|vd[a-z])"), "reason": "mkfs formatting disk"},
    {"level": "critical", "id": "fork-bomb", "regex": re.compile(r":\(\)\s*\{.*:\s*\|\s*:.*&"), "reason": "fork bomb detected"},
    # HIGH
    {"level": "high", "id": "curl-pipe-sh", "regex": re.compile(r"\b(curl|wget)\b.+\|\s*(ba)?sh\b"), "reason": "piping URL to shell (RCE risk)"},
    {"level": "high", "id": "git-force-main", "regex": re.compile(r"\bgit\s+push\b(?!.+--force-with-lease).+(--force|-f)\b.+\b(main|master)\b"), "reason": "force push to main/master"},
    {"level": "high", "id": "git-reset-hard", "regex": re.compile(r"\bgit\s+reset\s+--hard"), "reason": "git reset --hard loses uncommitted work"},
    {"level": "high", "id": "git-clean-f", "regex": re.compile(r"\bgit\s+clean\s+(-\w*f|-f)"), "reason": "git clean -f deletes untracked files"},
    {"level": "high", "id": "chmod-777", "regex": re.compile(r"\bchmod\b.+\b777\b"), "reason": "chmod 777 is a security risk"},
    {"level": "high", "id": "cat-secrets", "regex": re.compile(r"\b(cat|less|head|tail|more)\b.+(credentials|secrets?|\.pem|\.key|id_rsa|id_ed25519)", re.IGNORECASE), "reason": "reading secrets file"},
    {"level": "high", "id": "env-dump", "regex": re.compile(r"\b(printenv|^env)\s*([;&|]|$)"), "reason": "env dump may expose secrets"},
    {"level": "high", "id": "echo-secret", "regex": re.compile(r"\becho\b.+\$\w*(SECRET|KEY|TOKEN|PASSWORD|API_|PRIVATE)", re.IGNORECASE), "reason": "echoing secret variable"},
    {"level": "high", "id": "docker-vol-rm", "regex": re.compile(r"\bdocker\s+volume\s+(rm|prune)"), "reason": "docker volume deletion loses data"},
    {"level": "high", "id": "rm-ssh", "regex": re.compile(r"\brm\b.+\.ssh/(id_|authorized_keys|known_hosts)"), "reason": "deleting SSH keys"},
    # HIGH - infrastructure
    {"level": "high", "id": "git-push-delete", "regex": re.compile(r"git\s+push\s+.*--delete", re.IGNORECASE), "reason": "deleting a remote Git branch or tag"},
    {"level": "high", "id": "git-branch-force-delete", "regex": re.compile(r"git\s+branch\s+-D", re.IGNORECASE), "reason": "force-deleting a local Git branch"},
    {"level": "high", "id": "sql-drop", "regex": re.compile(r"DROP\s+(TABLE|DATABASE|SCHEMA|INDEX)", re.IGNORECASE), "reason": "dropping a database object"},
    {"level": "high", "id": "sql-truncate", "regex": re.compile(r"TRUNCATE\s+TABLE", re.IGNORECASE), "reason": "truncating a database table"},
    {"level": "high", "id": "sql-delete", "regex": re.compile(r"DELETE\s+FROM", re.IGNORECASE), "reason": "deleting database rows"},
    {"level": "high", "id": "sql-alter-drop", "regex": re.compile(r"ALTER\s+TABLE\s+.*DROP", re.IGNORECASE), "reason": "dropping a database column or constraint"},
    {"level": "high", "id": "mongo-destructive", "regex": re.compile(r"db\..*\.(drop|deleteMany|remove)\(", re.IGNORECASE), "reason": "destructive MongoDB operation"},
    {"level": "high", "id": "docker-destructive", "regex": re.compile(r"docker(-compose|\s+compose)?\s+(down|kill|rm|rmi)", re.IGNORECASE), "reason": "tearing down Docker resources"},
    {"level": "high", "id": "docker-resource-delete", "regex": re.compile(r"docker\s+(system|volume|image|container|network)\s+(prune|rm)", re.IGNORECASE), "reason": "pruning or deleting Docker resources"},
    {"level": "high", "id": "kubectl-delete", "regex": re.compile(r"kubectl\s+delete", re.IGNORECASE), "reason": "deleting Kubernetes resources"},
    {"level": "high", "id": "kubectl-drain", "regex": re.compile(r"kubectl\s+drain", re.IGNORECASE), "reason": "draining a Kubernetes node"},
    {"level": "high", "id": "kubectl-replace-force", "regex": re.compile(r"kubectl\s+replace\s+--force", re.IGNORECASE), "reason": "force-replacing Kubernetes resources"},
    {"level": "high", "id": "argo-delete", "regex": re.compile(r"argo(cd)?\s+(app\s+)?delete", re.IGNORECASE), "reason": "deleting an Argo application or workflow"},
    {"level": "high", "id": "argo-terminate", "regex": re.compile(r"argo\s+terminate", re.IGNORECASE), "reason": "terminating an Argo workflow"},
    {"level": "high", "id": "argocd-remove", "regex": re.compile(r"argocd\s+(cluster|repo)\s+rm", re.IGNORECASE), "reason": "removing an Argo CD cluster or repository"},
    {"level": "high", "id": "argocd-sync-prune", "regex": re.compile(r"argocd\s+app\s+sync.*--prune", re.IGNORECASE), "reason": "syncing an Argo CD application with pruning"},
    {"level": "high", "id": "helm-delete", "regex": re.compile(r"helm\s+(uninstall|delete)", re.IGNORECASE), "reason": "deleting a Helm release"},
    {"level": "high", "id": "terraform-destroy", "regex": re.compile(r"terraform\s+destroy", re.IGNORECASE), "reason": "destroying Terraform-managed infrastructure"},
    {"level": "high", "id": "terraform-apply-destroy", "regex": re.compile(r"terraform\s+apply\s+.*-destroy", re.IGNORECASE), "reason": "applying a Terraform destroy plan"},
    {"level": "high", "id": "aws-destructive", "regex": re.compile(r"aws\s+.*\b(rb|rm|delete|terminate|destroy|purge)\b", re.IGNORECASE), "reason": "destructive AWS operation"},
    {"level": "high", "id": "airflow-db-destructive", "regex": re.compile(r"airflow\s+db\s+(reset|clean|drop-archived)", re.IGNORECASE), "reason": "resetting or purging the Airflow metadata database"},
    {"level": "high", "id": "airflow-entity-delete", "regex": re.compile(r"airflow\s+(dags|connections|variables|pools)\s+delete", re.IGNORECASE), "reason": "deleting an Airflow object"},
    {"level": "high", "id": "airflow-tasks-clear", "regex": re.compile(r"airflow\s+tasks\s+clear", re.IGNORECASE), "reason": "clearing Airflow task instances"},
    # STRICT
    {"level": "strict", "id": "git-force-any", "regex": re.compile(r"\bgit\s+push\b(?!.+--force-with-lease).+(--force|-f)\b"), "reason": "force push (use --force-with-lease)"},
    {"level": "strict", "id": "git-checkout-dot", "regex": re.compile(r"\bgit\s+checkout\s+\."), "reason": "git checkout . discards changes"},
    {"level": "strict", "id": "sudo-rm", "regex": re.compile(r"\bsudo\s+rm\b"), "reason": "sudo rm has elevated privileges"},
    {"level": "strict", "id": "docker-prune", "regex": re.compile(r"\bdocker\s+(system|image)\s+prune"), "reason": "docker prune removes images"},
    {"level": "strict", "id": "crontab-r", "regex": re.compile(r"\bcrontab\s+-r"), "reason": "removes all cron jobs"},
)

# --- git-safety ---

PROTECTED_BRANCHES = ("main", "master")

GIT_PATTERNS = (
    {"level": "high", "id": "push-main", "regex": re.compile(r"\bgit\s+push\b.*\bmain\b"), "reason": "Pushing to main is not allowed"},
    {"level": "high", "id": "push-master", "regex": re.compile(r"\bgit\s+push\b.*\bmaster\b"), "reason": "Pushing to master is not allowed"},
    {"level": "high", "id": "branch-delete-protected", "regex": re.compile(r"\bgit\s+branch\s+.*(?:-[dD]|--delete)\s+(?:main|master)\b"), "reason": "Deleting a protected branch is not allowed"},
    {"level": "high", "id": "commit-on-protected", "regex": re.compile(r"\bgit\s+commit\b"), "reason": "Committing directly on {branch} is not allowed", "branch_only": True},
    {"level": "high", "id": "merge-on-protected", "regex": re.compile(r"\bgit\s+merge\b"), "reason": "Merging into {branch} is not allowed", "branch_only": True},
    {"level": "high", "id": "rebase-on-protected", "regex": re.compile(r"\bgit\s+rebase\b"), "reason": "Rebasing {branch} is not allowed", "branch_only": True},
    {"level": "high", "id": "reset-on-protected", "regex": re.compile(r"\bgit\s+reset\b"), "reason": "Resetting {branch} is not allowed", "branch_only": True},
    {"level": "high", "id": "push-on-protected", "regex": re.compile(r"\bgit\s+push\b"), "reason": "Pushing from {branch} is not allowed", "branch_only": True},
    {"level": "high", "id": "gh-pr-merge", "regex": re.compile(r"\bgh\s+pr\s+merge\b"), "reason": "Merging PRs via gh CLI is not allowed"},
    {"level": "high", "id": "gh-pr-close", "regex": re.compile(r"\bgh\s+pr\s+close\b"), "reason": "Closing PRs via gh CLI is not allowed"},
    {"level": "high", "id": "gh-issue-close", "regex": re.compile(r"\bgh\s+issue\s+close\b"), "reason": "Closing issues via gh CLI is not allowed"},
    {"level": "high", "id": "gh-release-delete", "regex": re.compile(r"\bgh\s+release\s+delete\b"), "reason": "Deleting releases via gh CLI is not allowed"},
    {"level": "high", "id": "gh-repo-delete", "regex": re.compile(r"\bgh\s+repo\s+delete\b"), "reason": "Deleting repos via gh CLI is not allowed"},
    {"level": "high", "id": "glab-mr-merge", "regex": re.compile(r"\bglab\s+mr\s+(?:merge|accept)\b"), "reason": "Merging MRs via glab CLI is not allowed"},
    {"level": "high", "id": "glab-mr-close", "regex": re.compile(r"\bglab\s+mr\s+close\b"), "reason": "Closing MRs via glab CLI is not allowed"},
    {"level": "high", "id": "glab-mr-delete", "regex": re.compile(r"\bglab\s+mr\s+(?:delete|del)\b"), "reason": "Deleting MRs via glab CLI is not allowed"},
    {"level": "high", "id": "glab-issue-close", "regex": re.compile(r"\bglab\s+issue\s+close\b"), "reason": "Closing issues via glab CLI is not allowed"},
    {"level": "high", "id": "glab-issue-delete", "regex": re.compile(r"\bglab\s+issue\s+(?:delete|del)\b"), "reason": "Deleting issues via glab CLI is not allowed"},
    {"level": "high", "id": "glab-release-delete", "regex": re.compile(r"\bglab\s+release\s+delete\b"), "reason": "Deleting releases via glab CLI is not allowed"},
    {"level": "high", "id": "glab-repo-delete", "regex": re.compile(r"\bglab\s+repo\s+delete\b"), "reason": "Deleting repos via glab CLI is not allowed"},
    {"level": "high", "id": "glab-ci-delete", "regex": re.compile(r"\bglab\s+(?:ci|pipe|pipeline)\s+delete\b"), "reason": "Deleting CI pipelines via glab CLI is not allowed"},
    {"level": "high", "id": "glab-ci-cancel", "regex": re.compile(r"\bglab\s+(?:ci|pipe|pipeline)\s+cancel\s+pipeline\b(?![^\n]*--dry-run)"), "reason": "Cancelling CI pipelines via glab CLI is not allowed"},
    {"level": "high", "id": "glab-variable-delete", "regex": re.compile(r"\bglab\s+variable\s+(?:delete|remove)\b"), "reason": "Deleting CI/CD variables via glab CLI is not allowed"},
    {"level": "high", "id": "glab-deploy-key-delete", "regex": re.compile(r"\bglab\s+deploy-key\s+delete\b"), "reason": "Deleting deploy keys via glab CLI is not allowed"},
    {"level": "high", "id": "glab-runner-delete", "regex": re.compile(r"\bglab\s+(?:runner|runner-controller)\s+delete\b"), "reason": "Deleting runners via glab CLI is not allowed"},
    {"level": "high", "id": "glab-securefile-delete", "regex": re.compile(r"\bglab\s+securefile\s+(?:remove|rm|delete)\b"), "reason": "Deleting secure files via glab CLI is not allowed"},
    {"level": "high", "id": "glab-registry-delete", "regex": re.compile(r"\bglab\s+container-registry\s+repository\s+(?:delete|del)\b"), "reason": "Deleting container registry repositories via glab CLI is not allowed"},
    {"level": "high", "id": "glab-api-delete", "regex": re.compile(r"\bglab\s+api\b[^;&|]*(?:-X|--method(?:=|\s+))\s*DELETE\b", re.IGNORECASE), "reason": "Deleting GitLab resources via glab api is not allowed"},
)

# --- protect-tests ---

TEST_PATH = re.compile(
    "|".join((
        r"(^|/)(tests?|__tests__|spec|specs)/",
        r"(^|/)test_[^/]+\.py$",
        r"_test\.(py|go|rb|js|jsx|ts|tsx|mjs|cjs)$",
        r"\.(test|spec)\.(js|jsx|ts|tsx|mjs|cjs)$",
        r"(^|/)[^/]+_spec\.rb$",
        r"(^|/)[^/]*Test\.(java|kt|cs)$",
        r"(^|/)Test[^/]*\.(java|kt|cs)$",
    )),
    re.IGNORECASE,
)

TEST_TOKEN = re.compile(
    r"(test_[\w.-]+\.\w+|[\w.-]+_test\.\w+|[\w.-]+\.(test|spec)\.\w+|"
    r"[\w.-]+_spec\.rb|(^|[\s'\"/])(tests?|__tests__|specs?)(/|[\s'\"]|$))",
    re.IGNORECASE,
)
DELETE_VERB = re.compile(r"(\brm\b|\bunlink\b|\bshred\b|\btrash\b|\bgit\s+rm\b|\bfind\b.*\s-delete\b)")
RENAME_VERB = re.compile(r"\bmv\b")
DISABLED_DEST = re.compile(r"(\.bak|\.old|\.orig|\.disabled|\.skip|\.ignore|\.tmp|~)([\"'\s]|$)", re.IGNORECASE)

SKIP_MARKERS = (
    re.compile(r"@pytest\.mark\.(skip|xfail)"),
    re.compile(r"@unittest\.skip"),
    re.compile(r"\bpytest\.skip\s*\("),
    re.compile(r"@Disabled\b"),
    re.compile(r"@Ignore\b"),
    re.compile(r"\b(it|test|describe|context)\.skip\s*\("),
    re.compile(r"\bx(it|describe|test|context)\s*\("),
    re.compile(r"\bt\.Skip(Now)?\s*\("),
    re.compile(r"#\[ignore\]"),
    re.compile(r"\[Ignore\]"),
)

ASSERTION_MARKERS = (
    re.compile(r"\bassert\b"),
    re.compile(r"\b(?:expect|verify|assertThat|assertEquals|assertTrue|assertFalse)\s*\("),
)
TAUTOLOGICAL_ASSERTION = re.compile(
    r"\bassert\s+True\b|\bassertTrue\s*\(\s*true\s*\)|"
    r"\bexpect\s*\(\s*true\s*\)",
    re.IGNORECASE,
)

EXTRA_DANGEROUS_PATTERNS = (
    ("find-delete", re.compile(r"\bfind\b[^\n;&|]*\s-delete\b", re.IGNORECASE), "find -delete removes files recursively"),
    ("rsync-delete", re.compile(r"\brsync\b[^\n;&|]*\s--delete(?:\s|=|$)", re.IGNORECASE), "rsync --delete removes destination files"),
    ("diskutil-erase", re.compile(r"\bdiskutil\s+(?:eraseDisk|eraseVolume|partitionDisk|zeroDisk|secureErase)\b", re.IGNORECASE), "diskutil destructive disk operation"),
    ("gcloud-delete", re.compile(r"\bgcloud\b[^\n;&|]*\b(delete|remove)\b", re.IGNORECASE), "destructive gcloud operation"),
    ("redis-flush", re.compile(r"\bredis-cli\b[^\n;&|]*\bFLUSH(?:ALL|DB)\b", re.IGNORECASE), "Redis database flush"),
    ("gh-api-delete", re.compile(r"\bgh\s+api\b[^;&|]*(?:-X|--method(?:=|\s+))\s*DELETE\b", re.IGNORECASE), "deleting GitHub resources via gh api"),
)


# --- secrets check ---

def is_allowlisted(file_path: str | None) -> bool:
    return bool(file_path and any(pattern.search(file_path) for pattern in ALLOWLIST))


def _check_file_path(file_path: str | None, safety_level: str = SAFETY_LEVEL) -> dict[str, Any]:
    if not file_path or is_allowlisted(file_path):
        return {"blocked": False, "pattern": None}
    threshold = LEVELS.get(safety_level, LEVELS["high"])
    for pattern in SENSITIVE_FILES:
        if LEVELS[pattern["level"]] <= threshold and pattern["regex"].search(file_path):
            return {"blocked": True, "pattern": pattern}
    return {"blocked": False, "pattern": None}


def _check_bash_secrets(command: str | None, safety_level: str = SAFETY_LEVEL) -> dict[str, Any]:
    if not command:
        return {"blocked": False, "pattern": None}
    if not BASH_SENTINELS.search(command):
        return {"blocked": False, "pattern": None}
    checked_command = command
    for pattern in ALLOWLIST:
        checked_command = pattern.sub("<allowed-env-template>", checked_command)
    threshold = LEVELS.get(safety_level, LEVELS["high"])
    for pattern in BASH_PATTERNS:
        if LEVELS[pattern["level"]] <= threshold and pattern["regex"].search(checked_command):
            return {"blocked": True, "pattern": pattern}
    sensitive_path = re.search(
        r"(?:^|[\s'\"])(?:[^\s'\"]*/)?"
        r"(?:\.env(?:\.[^\s/'\"]+)?|credentials\.json|"
        r"secrets?\.(?:json|ya?ml|toml)|\.aws/credentials|\.netrc|id_(?:rsa|ed25519|ecdsa|dsa)|"
        r"[^\s/'\"]+\.(?:pem|key))(?:$|[\s'\"])",
        checked_command,
        re.IGNORECASE,
    )
    reader_or_stager = re.search(
        r"\b(?:sed|awk|grep|rg|perl|python\d*|ruby|node|git\s+(?:add|diff|show)|tar|zip)\b",
        checked_command,
        re.IGNORECASE,
    )
    if sensitive_path and reader_or_stager:
        return {
            "blocked": True,
            "pattern": {
                "level": "high",
                "id": "indirect-secret-access",
                "reason": "indirectly reading or staging a sensitive file",
            },
        }
    return {"blocked": False, "pattern": None}


def check_secrets(tool_name: str, tool_input: dict[str, Any] | None, safety_level: str = SAFETY_LEVEL) -> dict[str, Any]:
    tool_input = tool_input if isinstance(tool_input, dict) else {}
    if tool_name in ("Read", "Edit", "Write"):
        return _check_file_path(tool_input.get("file_path"), safety_level)
    if tool_name == "Bash":
        return _check_bash_secrets(tool_input.get("command"), safety_level)
    return {"blocked": False, "pattern": None}


# --- dangerous command check ---

def check_dangerous_command(command: str, safety_level: str = SAFETY_LEVEL) -> dict[str, Any]:
    threshold = LEVELS.get(safety_level, LEVELS["high"])
    for pattern in DANGEROUS_PATTERNS:
        if LEVELS[pattern["level"]] <= threshold and pattern["regex"].search(command):
            return {"blocked": True, "pattern": pattern}
    return {"blocked": False, "pattern": None}


# --- git safety check ---

def get_current_branch() -> str:
    try:
        result = subprocess.run(
            ["git", "branch", "--show-current"],
            check=True,
            capture_output=True,
            text=True,
        )
        return result.stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return ""


def check_git_command(
    command: str,
    branch: str | None = None,
    safety_level: str = SAFETY_LEVEL,
) -> dict[str, Any]:
    threshold = LEVELS.get(safety_level, LEVELS["high"])
    current_branch = branch
    for pattern in GIT_PATTERNS:
        if LEVELS[pattern["level"]] > threshold or not pattern["regex"].search(command):
            continue
        if pattern.get("branch_only"):
            if not current_branch:
                current_branch = get_current_branch()
            if current_branch not in PROTECTED_BRANCHES:
                continue
        reason = pattern["reason"].replace("{branch}", current_branch or "")
        return {"blocked": True, "pattern": pattern, "reason": reason}
    return {"blocked": False}


# --- test protection check ---

def added_marker(old_string: str | None, new_string: str | None) -> bool:
    before = old_string or ""
    after = new_string or ""
    return any(pattern.search(after) and not pattern.search(before) for pattern in SKIP_MARKERS)


def check_tests_tool(
    tool_name: str,
    tool_input: dict[str, Any] | None = None,
    safety_level: str = SAFETY_LEVEL,
) -> dict[str, Any]:
    tool_input = tool_input if isinstance(tool_input, dict) else {}
    threshold = LEVELS.get(safety_level, LEVELS["high"])

    def allow() -> dict[str, Any]:
        return {"blocked": False}

    def _deny(level: str, rule_id: str, reason: str) -> dict[str, Any]:
        if LEVELS[level] <= threshold:
            return {"blocked": True, "id": rule_id, "level": level, "reason": reason}
        return allow()

    if tool_name == "Bash":
        command = tool_input.get("command", "")
        if not TEST_TOKEN.search(command):
            return allow()
        if DELETE_VERB.search(command):
            return _deny("critical", "delete-test", "deleting test file(s) or test directory")
        if RENAME_VERB.search(command) and DISABLED_DEST.search(command):
            return _deny("high", "rename-test", "renaming a test file to a disabled name")
        return allow()

    if tool_name == "Edit":
        if TEST_PATH.search(tool_input.get("file_path", "")) and added_marker(
            tool_input.get("old_string"), tool_input.get("new_string")
        ):
            return _deny("high", "skip-test", "adding a skip/xfail/ignore marker to an existing test")
        return allow()

    if tool_name == "MultiEdit":
        if TEST_PATH.search(tool_input.get("file_path", "")):
            edits = tool_input.get("edits", [])
            if isinstance(edits, list):
                for edit in edits:
                    if isinstance(edit, dict) and added_marker(edit.get("old_string"), edit.get("new_string")):
                        return _deny("high", "skip-test", "adding a skip/xfail/ignore marker to an existing test")
        return allow()

    if tool_name == "Write":
        if TEST_PATH.search(tool_input.get("file_path", "")) and added_marker("", tool_input.get("content", "")):
            return _deny("strict", "write-skipped-test", "writing a test file that is already skipped/ignored")
        return allow()

    return allow()


# --- policy core ---

def config_unlocked() -> bool:
    return os.environ.get(CONFIG_UNLOCK_ENV) == "1"


def deny(rule_id: str, reason: str) -> dict[str, Any]:
    return {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": f"[{rule_id}] {reason}",
        }
    }


def _resolve_path(file_path: str, cwd: str | None) -> Path:
    path = Path(file_path).expanduser()
    if not path.is_absolute():
        path = Path(cwd or os.getcwd()) / path
    return path.resolve(strict=False)


def _claude_root() -> Path:
    return (Path.home() / ".claude").resolve(strict=False)


def is_protected_config_path(file_path: str | None, cwd: str | None = None) -> bool:
    if not isinstance(file_path, str) or not file_path:
        return False
    path = _resolve_path(file_path, cwd)
    root = _claude_root()
    try:
        relative = path.relative_to(root)
    except ValueError:
        return False
    if not relative.parts:
        return True
    return relative.parts[0] in PROTECTED_CONFIG_PARTS or relative.name in PROTECTED_CONFIG_FILES


def _references_protected_config(command: str) -> bool:
    root = re.escape(str(_claude_root()))
    textual_root = re.escape(str(Path.home() / ".claude"))
    protected = r"(?:hooks|scripts|rules|skills)(?:/|\b)|(?:CLAUDE\.md|settings(?:\.local)?\.json|statusline\.sh)\b"
    return bool(
        re.search(
            rf"(?:~|\$HOME|\$PWD)/\.claude/{protected}|"
            rf"(?:^|[\s'\"(])(?:\./)?\.claude/{protected}|"
            rf"(?:{root}|{textual_root})/{protected}",
            command,
        )
    )


def normalize_for_safety(command: str) -> str:
    normalized = command
    executable_group = "|".join(re.escape(name) for name in KNOWN_EXECUTABLES)
    normalized = re.sub(rf"(['\"])(?P<exe>{executable_group})\1", lambda match: match.group("exe"), normalized)
    assignments = {
        match.group("name"): match.group("exe")
        for match in re.finditer(
            rf"(?:^|[;]\s*)(?P<name>[A-Za-z_][A-Za-z0-9_]*)\s*=\s*['\"]?(?P<exe>{executable_group})['\"]?(?=\s*;)",
            normalized,
        )
    }
    for name, executable in assignments.items():
        normalized = re.sub(rf"\$\{{{re.escape(name)}\}}|\${re.escape(name)}\b", executable, normalized)
    git_global_option = r"(?:-C\s+\S+|--git-dir(?:=|\s+)\S+|--work-tree(?:=|\s+)\S+)"
    normalized = re.sub(rf"\bgit(?:\s+{git_global_option})+\s+", "git ", normalized)
    return normalized


def _check_assertion_weakening(tool_name: str, tool_input: dict[str, Any]) -> dict[str, Any] | None:
    edits: list[dict[str, Any]] = []
    file_path = tool_input.get("file_path", "")
    if not TEST_PATH.search(file_path):
        return None
    if tool_name == "Edit":
        edits = [tool_input]
    elif tool_name == "MultiEdit" and isinstance(tool_input.get("edits"), list):
        edits = [edit for edit in tool_input["edits"] if isinstance(edit, dict)]
    elif tool_name == "Write":
        resolved = _resolve_path(file_path, None)
        if resolved.exists():
            return deny("overwrite-test", "Write cannot replace an existing test file; use a reviewable Edit")
        if TAUTOLOGICAL_ASSERTION.search(str(tool_input.get("content", ""))):
            return deny("tautological-test", "refusing to create a test with a tautological assertion")
        return None

    for edit in edits:
        before = str(edit.get("old_string", ""))
        after = str(edit.get("new_string", ""))
        if TAUTOLOGICAL_ASSERTION.search(after) and not TAUTOLOGICAL_ASSERTION.search(before):
            return deny("tautological-test", "refusing to add a tautological test assertion")
        before_count = sum(len(pattern.findall(before)) for pattern in ASSERTION_MARKERS)
        after_count = sum(len(pattern.findall(after)) for pattern in ASSERTION_MARKERS)
        if before_count > after_count:
            return deny("remove-test-assertion", "removing test assertions requires manual review")
    return None


def _bounded_read(tool_input: dict[str, Any], cwd: str | None) -> dict[str, Any] | None:
    file_path = tool_input.get("file_path")
    if not isinstance(file_path, str) or not file_path:
        return None
    path = _resolve_path(file_path, cwd)
    if not path.is_file() or path.stat().st_size <= LARGE_READ_BYTES:
        return None
    with path.open("rb") as handle:
        sample = handle.read(max(LARGE_READ_BYTES, MAX_SINGLE_LINE_BYTES + 1))
    if b"\0" in sample:
        return None
    if any(len(line) > MAX_SINGLE_LINE_BYTES for line in sample.splitlines()):
        return deny("large-single-line-read", "large single-line file; use rtk json, jq, rg, or a targeted Bash query")
    requested_limit = tool_input.get("limit")
    if isinstance(requested_limit, int) and 0 < requested_limit <= MAX_READ_LINES:
        return None
    updated_input = dict(tool_input)
    updated_input["limit"] = MAX_READ_LINES
    return {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "allow",
            "permissionDecisionReason": f"Large file; read capped at {MAX_READ_LINES} lines. Use grep/rg for targeted pattern search.",
            "updatedInput": updated_input,
        }
    }


def _run_rtk(payload: dict[str, Any], normalized_command: str) -> dict[str, Any]:
    if shutil.which("rtk") is None:
        return {}
    rtk_payload = dict(payload)
    original_input = payload.get("tool_input", {})
    rtk_input = dict(original_input) if isinstance(original_input, dict) else {}
    rtk_input["command"] = normalized_command
    rtk_payload["tool_input"] = rtk_input
    result = subprocess.run(
        ["rtk", "hook", "claude"],
        input=json.dumps(rtk_payload, separators=(",", ":")),
        capture_output=True,
        text=True,
        timeout=3,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError("RTK hook failed")
    if not result.stdout.strip():
        return {}
    parsed = json.loads(result.stdout)
    if not isinstance(parsed, dict):
        raise ValueError("RTK hook returned non-object JSON")
    output = parsed.get("hookSpecificOutput")
    if not isinstance(output, dict):
        raise ValueError("RTK hook returned invalid hookSpecificOutput")
    updated = output.get("updatedInput")
    if isinstance(updated, dict):
        output["updatedInput"] = {**rtk_input, **updated}
    return parsed


def evaluate_pre_tool(payload: dict[str, Any]) -> dict[str, Any]:
    tool_name = payload.get("tool_name", "")
    tool_input = payload.get("tool_input")
    tool_input = tool_input if isinstance(tool_input, dict) else {}
    cwd = payload.get("cwd") if isinstance(payload.get("cwd"), str) else None

    if tool_name in ("WebSearch", "WebFetch"):
        return {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "ask",
                "permissionDecisionReason": "WebSearch/WebFetch in main context costs tokens. Already in a subagent? Hit allow. Otherwise: spawn a Haiku Agent instead.",
            }
        }

    checked_input = tool_input
    normalized = ""
    if tool_name == "Bash":
        normalized = normalize_for_safety(str(tool_input.get("command", "")))
        checked_input = {**tool_input, "command": normalized}

    if tool_name in ("Edit", "MultiEdit", "Write") and not config_unlocked():
        if is_protected_config_path(tool_input.get("file_path"), cwd):
            return deny("config-locked", f"Claude configuration is locked; restart with {CONFIG_UNLOCK_ENV}=1 to edit it")

    secret_input = checked_input
    if tool_name in ("Read", "Edit", "MultiEdit", "Write") and isinstance(tool_input.get("file_path"), str):
        secret_input = {**checked_input, "file_path": str(_resolve_path(tool_input["file_path"], cwd))}
    secret_result = check_secrets(tool_name, secret_input)
    if secret_result.get("blocked"):
        pattern = secret_result["pattern"]
        return deny(pattern["id"], pattern["reason"])

    test_result = check_tests_tool(tool_name, checked_input)
    if test_result.get("blocked"):
        return deny(test_result["id"], test_result["reason"])
    assertion_result = _check_assertion_weakening(tool_name, tool_input)
    if assertion_result:
        return assertion_result

    if tool_name == "Read":
        return _bounded_read(tool_input, cwd) or {}
    if tool_name != "Bash":
        return {}

    command = str(tool_input.get("command", ""))
    if not config_unlocked() and _references_protected_config(normalized):
        return deny(
            "config-locked",
            f"Bash access to protected Claude configuration requires {CONFIG_UNLOCK_ENV}=1; use Read for inspection",
        )

    dangerous_result = check_dangerous_command(normalized)
    if dangerous_result.get("blocked"):
        pattern = dangerous_result["pattern"]
        return deny(pattern["id"], pattern["reason"])
    git_result = check_git_command(normalized)
    if git_result.get("blocked"):
        return deny(git_result["pattern"]["id"], git_result["reason"])
    for rule_id, pattern, reason in EXTRA_DANGEROUS_PATTERNS:
        if pattern.search(normalized):
            return deny(rule_id, reason)

    try:
        rtk_output = _run_rtk(payload, command)
    except (OSError, subprocess.SubprocessError, ValueError, RuntimeError, json.JSONDecodeError):
        return {}
    return rtk_output


def evaluate_config_change(payload: dict[str, Any]) -> dict[str, Any]:
    if config_unlocked() or payload.get("source") == "policy_settings":
        return {}
    source = str(payload.get("source", "configuration"))
    return {
        "decision": "block",
        "reason": f"{source} changes are locked for this session; restart with {CONFIG_UNLOCK_ENV}=1 to apply them",
    }


def _log_internal_error(error: Exception, raw: str) -> None:
    try:
        log_dir = HOOKS_DIR.parent / "hooks-logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        fingerprint = hashlib.sha256(raw.encode("utf-8", errors="replace")).hexdigest()[:16]
        with (log_dir / "policy-errors.log").open("a", encoding="utf-8") as handle:
            handle.write(f"input={fingerprint} error={type(error).__name__}\n")
    except Exception:
        pass


def main() -> None:
    raw = sys.stdin.read()
    try:
        payload = json.loads(raw)
        if not isinstance(payload, dict):
            raise ValueError("hook input must be an object")
        event = payload.get("hook_event_name")
        if event == "ConfigChange":
            output = evaluate_config_change(payload)
        else:
            output = evaluate_pre_tool(payload)
        print(json.dumps(output, separators=(",", ":")))
    except Exception as error:
        _log_internal_error(error, raw)
        print("Claude policy hook failed closed", file=sys.stderr)
        raise SystemExit(2)


if __name__ == "__main__":
    main()
