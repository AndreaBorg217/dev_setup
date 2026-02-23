# Andrea's Developer Setup

## Steps

1. Create a _.env_ following _.env.example_. If you leave the `PYTHON_VERSION` & `GO_VERSION` are not set the latest will be obtained.

2. Install HomeBrew

```bash
bash install_brew.sh
```

3. Install Ansible

```bash
bash install_ansible.sh
```

4. Run the setup playbook

```bash
bash run_playbook.sh
```

## Contents

### Terminal

Task: `tasks/terminal.yml`

Took some inspiration from (Josean Martinez)[https://www.youtube.com/watch?v=U-omALWIBos]

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

`terminal/.zshrc` contains some aliases for _Python_ and _Docker_.

**REQUIRES SOME MANUAL STEPS (SEE BELOW)**

### Neovim

Task: `tasks/neovim.yml`

Took some inspirations from:

- (Josean Martinez)[https://www.youtube.com/watch?v=U-omALWIBos]
- (The Primeagen)[https://www.youtube.com/watch?v=c0Xmd4PGino]

### Visual Studio Code

Task: `tasks/vscode.yml`

Took some inspiration from (Levi Wilkerson)[https://www.youtube.com/watch?v=l7CMlJRE5Hw]

It is effectively a replica of the Neovim configs above.

`extensions.json` is installed. `settings.json` & `keybindings.json` are stowed.

### Apps

Task: `tasks/apps.yml`

- Notion
- Google Chrome
- Brave
- Spotify
- Dropbox

## Dotfiles managed by Stow

| Package                                                         | Symlinks to                                                |
| --------------------------------------------------------------- | ---------------------------------------------------------- |
| `zsh/.zshrc`                                                    | `~/.zshrc`                                                 |
| `tmux/.tmux.conf`                                               | `~/.tmux.conf`                                             |
| `neovim/.config/nvim`                                           | `~/.config/nvim`                                           |
| `vscode/Library/Application Support/Code/User/settings.json`    | `~/Library/Application Support/Code/User/settings.json`    |
| `vscode/Library/Application Support/Code/User/keybindings.json` | `~/Library/Application Support/Code/User/keybindings.json` |

## Manual steps required

A few things can't be automated due to macOS GUI restrictions:

1. **Powerlevel10k** —> restart iTerm2 and follow the configuration wizard
2. **iTerm2 font size** —> `CMD ,` > Profiles > Text > set font size to 20
3. **iTerm2 colour scheme** —> `CMD ,` > Profiles > Colors > import `coolnight.itermcolors` from the repo root
4. **tmux plugins** —> open a tmux session and press `CTRL+a r` then `CTRL+a SHIFT+i`
5. **GitHub auth** —> authenticate via GitHub Desktop or PAT on first `git push`
6. **Docker Desktop** —> open Docker Desktop manually once to accept the system extension prompt
