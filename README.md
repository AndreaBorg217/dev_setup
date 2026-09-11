# Andrea's Developer Setup

![Last tested](https://img.shields.io/badge/last%20tested-2026--07--25-2ea44f?style=for-the-badge&logo=ansible&logoColor=white)
![Neovim](https://img.shields.io/badge/NeoVim-%2357A143.svg?&style=for-the-badge&logo=neovim&logoColor=white)
![Vim](https://img.shields.io/badge/VIM-%2311AB00.svg?style=for-the-badge&logo=vim&logoColor=white)
![Ansible](https://img.shields.io/badge/ansible-%231A1918.svg?style=for-the-badge&logo=ansible&logoColor=white)
![Git](https://img.shields.io/badge/git-%23F05033.svg?style=for-the-badge&logo=git&logoColor=white)
![GitHub](https://img.shields.io/badge/github-%23121011.svg?style=for-the-badge&logo=github&logoColor=white)
![Visual Studio Code](https://img.shields.io/badge/Visual%20Studio%20Code-0078d7.svg?style=for-the-badge&logo=visual-studio-code&logoColor=white)
![Python](https://img.shields.io/badge/python-3670A0?style=for-the-badge&logo=python&logoColor=ffdd54)
![Go](https://img.shields.io/badge/go-%2300ADD8.svg?style=for-the-badge&logo=go&logoColor=white)
![Docker](https://img.shields.io/badge/docker-%230db7ed.svg?style=for-the-badge&logo=docker&logoColor=white)
![tmux](https://img.shields.io/badge/tmux-%23000000?style=for-the-badge&logo=tmux&logoColor=%231BB91F)
![iTerm2](https://img.shields.io/badge/iTerm2-%23000000?style=for-the-badge&logo=iterm2&logoColor=white)
[![Claude](https://img.shields.io/badge/Claude-D97757?style=for-the-badge&logo=claude&logoColor=white)](#)

## How to run

1. For each environment variable in _.env.example_, run `export VARIABLE_NAME=value`
2. Run the tracked `./run.sh`

## Testing

To test the playbook before applying it to a machine use [Tart](https://tart.run/quick-start/):

```bash
brew install cirruslabs/cli/tart
tart clone ghcr.io/cirruslabs/macos-sequoia-base:latest sequoia-base
tart clone sequoia-base test-dev-setup
tart run test-dev-setup
ssh admin@$(tart ip test-dev-setup)
```

**DOCKER MAY NOT WORK!!**

## Contents

### Terminal

Task: `tasks/terminal.yml`

We use **iTerm2** as the terminal, **Oh My Zsh** for customisation, and **tmux** for sessions.

This is a small tmux cheatsheet:

| Action                     | Command                 |
| -------------------------- | ----------------------- |
| New session                | `tmux new -s {NAME}`    |
| Close session              | `tmux detach`           |
| Re-enter session           | `tmux attach -t {NAME}` |
| Split vertically           | `CTRL a \|`             |
| Split horizontally         | `CTRL a -`              |
| Navigate terminals         | `CTRL hjkl`             |
| Maximise/minimise terminal | `CTRL a m`              |
| Resize window              | `CTRL a hjkl`           |
| New window                 | `CTRL a c`              |
| Rename window              | `CTRL a ,`              |

`terminal/.zshrc` contains some aliases for _Python_ and _Docker_.

### Neovim

Task: `tasks/neovim.yml`

The Neovim task is currently disabled because its `setup.yml` include is commented out. Enable it there, or deploy directly with:

```bash
stow --restow --no-folding --target "$HOME" neovim
```

Java support uses JDTLS with Spring Boot language-server extensions, debugging, tests, and Palantir formatting.

Supermaven provides inline AI completions. Start with `:SupermavenUseFree`, or use `:SupermavenUsePro` for an existing Pro account.

Machine-specific Neovim settings belong in
`neovim/.config/nvim/local.lua`, which is ignored by Git. For example, disable
format-on-save while retaining manual formatting with:

```lua
vim.g.disable_autoformat = true
```

This is a small neovim cheatsheet:

| Action                         | Command        |
| ------------------------------ | -------------- |
| Search for file                | `space ff`     |
| Search for string              | `space fs`     |
| Toggle file-tree               | `space ee`     |
| Open file-tree on current file | `space ef`     |
| Collapse file-tree             | `space ec`     |
| Refresh file-tree              | `space er`     |
| Toggle breakpoint              | `space db`     |
| Start debugger                 | `space dc`     |
| Quit debugger                  | `space dq`     |
| Step over                      | `space do`     |
| Focus on code                  | `space d0`     |
| Focus on scopes (variables)    | `space d1`     |
| Focus on watches               | `space d4`     |
| Focus on REPL                  | `space d5`     |
| Create mark                    | `m <a-z>`      |
| Go to mark                     | `' <a-z>`      |
| Toggle comment                 | `CTRL /` or `gcc` |
| Format file                    | `space fmt`    |
| Lint file                      | `space lf`     |
| Code actions                   | `space ca`     |
| Go to definition               | `space gd`     |
| Show references                | `space gr`     |
| Rename symbol                  | `space rn`     |
| Show docs                      | `K`            |
| Next diagnostic                | `]d`           |
| Previous diagnostic            | `[d`           |
| Show workspace diagnostics     | `space xw`     |
| Add file to Harpoon            | `space ha`     |
| Clear Harpoon                  | `space hc`     |
| Harpoon navigate               | `space h<1-4>` |
| Toggle rendered Markdown       | `space op`     |
| Split vertically               | `space sv`     |
| Split horizontally             | `space sh`     |
| Close split                    | `space sx`     |

### Visual Studio Code

Task: `tasks/vscode.yml`

VS Code uses separate keybindings and settings.

`keybindings.json` is stowed (live symlink). `settings.json` is handled by `vscode/merge_settings.py`:

- **No `vscode/settings.local.json`** -> base is symlinked, so edits are live (no re-run needed).
- **`vscode/settings.local.json` present** -> base + local are deep-merged into a generated file (cannot be a symlink). Edits to either source are **not** live.

To override VSCode settings on one machine, create `vscode/settings.local.json` with only the keys you want to override; for example to disable Python autoformat on a specific machine:

```json
{
    "[python]": {
        "editor.formatOnSave": false,
        "editor.codeActionsOnSave": {
            "source.organizeImports": "never"
        }
    }
}
```

After editing the base VSCode `settings.json` or `vscode/settings.local.json`, re-apply with:

```bash
ansible-playbook setup.yml --tags vscode
```

Extensions are managed via `vscode/manage_extensions.py`:

```bash
python3 vscode/manage_extensions.py --install    # install missing extensions from extensions.json
python3 vscode/manage_extensions.py --uninstall  # uninstall all extensions
python3 vscode/manage_extensions.py --reinstall  # uninstall all, then install from extensions.json
python3 vscode/manage_extensions.py --list       # list installed extensions with versions
```

Local extensions are kept in `vscode/extensions`. The VSCode task symlinks
`vscode/extensions/copy-reference` into
`~/.vscode/extensions/dev-setup.copy-reference-0.1.0`.

The `copy-reference` extension contributes the `copyReference.copy` command
(`Copy File Reference`), bound to `space c p` in Normal or Visual Vim mode. It
copies a reference for the active editor to the clipboard:

| Selection | Clipboard value |
| --------- | --------------- |
| No selection | `path/to/file.ext` |
| Selected text | `path/to/file.ext:start_line:end_line` |

Paths are workspace-relative for files inside the current workspace. Files
outside a workspace use their absolute path, and non-file editors use their URI.
The optional prompt support is currently disabled in the extension source.

The command was inspired by
[smnatale's copy command gist](https://gist.github.com/smnatale/b30dc21ff330495641fb59f36005562c).

### Apps

Task: `tasks/apps.yml`

- [![Google Chrome](https://img.shields.io/badge/Google%20Chrome-4285F4?logo=GoogleChrome&logoColor=white)](#)
- [![Brave](https://img.shields.io/badge/Brave-FB542B?logo=Brave&logoColor=white)](#)
- [![Spotify](https://img.shields.io/badge/Spotify-1ED760?logo=spotify&logoColor=white)](#)
- [![Dropbox](https://img.shields.io/badge/Dropbox-0061FF?logo=dropbox&logoColor=fff)](#)
- [![Bitwarden](https://img.shields.io/badge/Bitwarden-175DDC?logo=bitwarden&logoColor=white)](#)
- [![Bruno](https://img.shields.io/badge/Bruno-F4AA41?logo=Bruno&logoColor=black)](#)
- [![Notion](https://img.shields.io/badge/Notion-000?logo=notion&logoColor=fff)](#)

## Claude (Code)

Task: `tasks/claude.yml`

Installs the stable Claude Code Homebrew cask, language servers, CodeGraph, and
Context Mode. The following user-managed config is tracked in `.claude`:

- `.gitignore` - excludes Claude's runtime state and other machine-local files
- `CLAUDE.md` - core behavioural instructions
- `settings.json` - linked as `~/.claude/settings.json`; contains permissions,
  models, plugins, hooks, environment, and UI settings
- `agents` - custom subagent definitions
- `output-styles` - response style definitions
- `rules` - focused behavioural and workflow instructions
- `scripts` - hook and command-line helper scripts
- `skills` - reusable task-specific instructions
- `statusline.sh` - displays the current directory, context, usage limits, model, and Git branch

The tracked pre-tool hook blocks plaintext secret exposure. Context Mode owns
its upstream hooks, including cache healing; Ansible installs the plugin instead
of copying its hook implementation. CodeGraph's prompt hook is disabled so its
instructions are not injected on every prompt. RTK is not integrated with
Claude.

The secret-exposure hook blocks common plaintext disclosure paths before Claude
runs a tool: direct `op read`/`bw get`/`bws secret get`, SOPS/KSOPS decrypts to
stdout, untrapped SOPS temp-file redirects, ksops-backed `kustomize build`
output, `kubectl get secret -o yaml|json|jsonpath`, and direct Bash/Read
access to known credential files.

### Context and model routing

`opusplan` uses Sonnet normally and Opus in Plan Mode. The manual `planner` skill
is an Opus human-in-the-loop orchestrator: it keeps decisions, assumptions,
doubts, the execution plan, and the test plan visible until the user approves a
brief with no known gaps. A Haiku `plan-writer` then serializes that approved
brief without making decisions. The Sonnet `plan-execute` orchestrator dispatches
the tasks and never implements them itself.

Model routing applies to normal work and planned execution. Haiku handles
bounded deterministic work with complete inputs, such as evidence collection,
approved documentation, or static fixtures from an approved test matrix.
Sonnet handles source code, test logic, runtime configuration, debugging,
ambiguity, and other semantic or higher-risk work. Every worker is a leaf and
returns a compact receipt.

### Context Mode

Ansible adds the upstream `mksglu/context-mode` marketplace and installs
`context-mode@context-mode`. The plugin registers its own local stdio MCP server,
hooks, and SQLite/FTS5 storage; Ansible does not duplicate that setup.

The permission policy allows local search, statistics, diagnostics, indexing,
and CodeGraph reads; prompts for sandbox execution, network fetches, and
deletion; and denies hosted Insight and upgrades. Secret-bearing paths remain
denied, while ordinary logs and other large inputs are routed through Context
Mode instead of being blocked.

### CodeGraph

Ansible runs CodeGraph's upstream standalone installer without a version pin, so
each run installs the latest release. It registers the MCP through Claude's CLI;
the machine-specific registration remains in untracked `~/.claude.json`.

Initialize each code repository once:

```bash
codegraph init
```

Claude uses the MCP for fresh interactive source discovery and the CLI for
subagents and automation. Before an authorised targeted test run, identify
candidate tests from tracked and relevant untracked paths with:

```bash
{
  git diff --name-only HEAD
  git ls-files --others --exclude-standard
} | codegraph affected --stdin --quiet
```

Affected-test output narrows validation; it does not replace required checks.
There is no CodeGraph sync hook: the MCP catches up when it connects and watches
the repository while running. `DO_NOT_TRACK=1` is set in Claude, the shell, and
the CodeGraph installation environment.

### Installation and checks

Plugins are installed at user scope. The manual
`session-efficiency-reviewer` audits local transcripts without emitting their
prompt, command, or tool-result contents.

Run the focused local checks with:

```bash
python3 -m unittest discover -s .claude/tests -p 'test_*.py'
python3 -m py_compile \
  .claude/skills/planner/scripts/materialize_plan_bundle.py \
  .claude/skills/session-efficiency-reviewer/scripts/session_efficiency.py
ansible-playbook --syntax-check setup.yml
```

See the [Context Mode guide](https://betterstack.com/community/guides/ai/context-mode-mcp/),
[CodeGraph documentation](https://colbymchenry.github.io/codegraph/), and
[Claude Code subagent documentation](https://code.claude.com/docs/en/sub-agents)
for the upstream behaviour behind this setup.

### Routines

Inspired by [this LinkedIn post](https://www.linkedin.com/posts/fabian-wesner_a-quick-tip-on-claude-codes-5-hour-usage-activity-7468185272250281984-Dek0)

Go to [https://claude.ai/code/routines](https://claude.ai/code/routines) and create a routine as shown below:

![Align token refresh](resources/claude_limits_routine.png)

## Dotfiles managed by Stow

| Package                                                         | Symlinks to                                                |
| --------------------------------------------------------------- | ---------------------------------------------------------- |
| `terminal/.zshrc`                                               | `~/.zshrc`                                                 |
| `terminal/.p10k.zsh`                                            | `~/.p10k.zsh`                                              |
| `tmux/.tmux.conf`                                               | `~/.tmux.conf`                                             |
| `neovim/.config/nvim`                                           | `~/.config/nvim` (a real directory containing individual symlinks because Neovim uses `--no-folding`) |
| `vscode/Library/Application Support/Code/User/settings.json`    | `~/Library/Application Support/Code/User/settings.json` (handled by `vscode/merge_settings.py`, not stowed) |
| `vscode/Library/Application Support/Code/User/keybindings.json` | `~/Library/Application Support/Code/User/keybindings.json` |
| `.claude` tracked config files                                 | `~/.claude/...` (individual symlinks)                      |

## Credits

[Josean Martinez](https://www.youtube.com/@joseanmartinez)

- [Terminal setup](https://www.youtube.com/watch?v=CF1tMjvHDRA)
- [Colour scheme](https://github.com/josean-dev/dev-environment-files/tree/main)
- [tmux setup](https://www.youtube.com/watch?v=U-omALWIBos)
- [Neovim setup](https://youtu.be/6pAG3BHurdM?si=jjdpf5qU7i6ukMZC)
- [Neovim LSP](https://youtu.be/oBiBEx7L000?si=fNd8ogijBijMQtBo)

[ThePrimeagen](https://www.youtube.com/@ThePrimeagen)

- [Neovim setup](https://www.youtube.com/watch?v=c0Xmd4PGino)

[Levi Wilkerson](https://www.youtube.com/@frostytf2)

- [Neovim-like setup for VSCode](https://www.youtube.com/watch?v=l7CMlJRE5Hw)

[NeuralNine](https://www.youtube.com/@NeuralNine)

- [Python DAP](https://www.youtube.com/watch?v=tfC1i32eW3A)

[Dreams of Code](https://www.youtube.com/@dreamsofcode)

- [Go DAP](https://www.youtube.com/watch?v=i04sSQjd-qo)

Terminal font created by [romaktv](https://github.com/romkatv/powerlevel10k-media/blob/master/MesloLGS%20NF%20Regular.ttf)
