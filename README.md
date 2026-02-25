# Andrea's Developer Setup

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

### Visual Studio Code

Task: `tasks/vscode.yml`

It is effectively a replica of the Neovim configs above.

`extensions.json` is installed. `settings.json` & `keybindings.json` are stowed.

### Apps

Task: `tasks/apps.yml`

- [![Google Chrome](https://img.shields.io/badge/Google%20Chrome-4285F4?logo=GoogleChrome&logoColor=white)](#)
- [![Brave](https://img.shields.io/badge/Brave-FB542B?logo=Brave&logoColor=white)](#)
- [![Spotify](https://img.shields.io/badge/Spotify-1ED760?logo=spotify&logoColor=white)](#)
- [![Dropbox](https://img.shields.io/badge/Dropbox-0061FF?logo=dropbox&logoColor=fff)](#)
- [![Bitwarden](https://img.shields.io/badge/Bitwarden-175DDC?logo=bitwarden&logoColor=white)](#)
- [![Bruno](https://img.shields.io/badge/Bruno-F4AA41?logo=Bruno&logoColor=black)](#)
- [![Notion](https://img.shields.io/badge/Notion-000?logo=notion&logoColor=fff)](#)

## Dotfiles managed by Stow

| Package                                                         | Symlinks to                                                |
| --------------------------------------------------------------- | ---------------------------------------------------------- |
| `terminal/.zshrc`                                               | `~/.zshrc`                                                 |
| `terminal/.p10k.zsh`                                            | `~/.p10k.zsh`                                              |
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
