#!/usr/bin/env bash
# Usage: parse-transcript.sh <path-to-jsonl>
# Prints user messages and skill-related tool calls from a transcript
FILE="${1:-$(ls -t ~/.claude/projects/-Users-andrea-borg-Documents-GitHub-dev-setup/*.jsonl | head -1)}"
cat "$FILE" | python3 -c "
import sys, json
for line in sys.stdin:
    try:
        msg = json.loads(line)
        if msg.get('type') == 'user':
            content = msg.get('message', {}).get('content', '')
            if isinstance(content, str) and content.strip():
                print('USER:', content[:200])
            elif isinstance(content, list):
                for block in content:
                    if isinstance(block, dict) and block.get('type') == 'text':
                        text = block.get('text', '').strip()
                        if text:
                            print('USER:', text[:200])
        elif msg.get('type') == 'assistant':
            content = msg.get('message', {}).get('content', [])
            if isinstance(content, list):
                for block in content:
                    if isinstance(block, dict) and block.get('type') == 'tool_use':
                        name = block.get('name', '')
                        inp = block.get('input', {})
                        if 'SKILL' in str(inp) or 'skill' in name.lower():
                            print('SKILL_TOOL:', name, str(inp)[:150])
    except:
        pass
"
