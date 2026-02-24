# Andrea's Developer Setup

## How to run

Create and run `run.sh`

## Testing

To test the playbook before applying it to a machine use [Tart](https://tart.run/quick-start/):

```bash
brew install cirruslabs/cli/tart
tart clone ghcr.io/cirruslabs/macos-sequoia-base:latest sequoia-base
tart run sequoia-base
```

**DOCKER MAY NOT WORK!!**

## Contents

### Terminal

Task: `tasks/terminal.yml`

Took some inspiration from [Josean Martinez](https://www.youtube.com/watch?v=U-omALWIBos). Colour scheme created by [Josean Martinez](https://github.com/josean-dev/dev-environment-files/tree/main). Font by [romkatv](https://github.com/romkatv/powerlevel10k-media/blob/master/MesloLGS%20NF%20Regular.ttf)

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

Took some inspiration from:

- [Josean Martinez](https://www.youtube.com/watch?v=U-omALWIBos)
- [The Primeagen](https://www.youtube.com/watch?v=c0Xmd4PGino)
- [NeuralNine](https://www.youtube.com/watch?v=tfC1i32eW3A)
- [Dreams of Code](https://www.youtube.com/watch?v=i04sSQjd-qo)

### Visual Studio Code

Task: `tasks/vscode.yml`

Took some inspiration from [Levi Wilkerson](https://www.youtube.com/watch?v=l7CMlJRE5Hw)

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

1. **Nerd Font** -> double click on the font file in the repo to register it
1. **iTerm2 font size** —> `CMD ,` > Profiles > Text > set font size to 20 & apply the nerd font
1. **iTerm2 colour scheme** —> `CMD ,` > Profiles > Colors > import `coolnight.itermcolors` from the repo root
1. **tmux plugins** —> open a tmux session and press `CTRL+a r` then `CTRL+a SHIFT+i`
