# Install homebrew

```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
echo 'eval "$(/opt/homebrew/bin/brew shellenv)"' >> /Users/[username]/.zprofile
eval "$(/opt/homebrew/bin/brew shellenv)"
```

# Install iTerm2

```bash
brew install --cask iterm2
```

# Install git
```bash
brew install git
```

# Install Oh My Zsh
```bash
sh -c "$(curl -fsSL https://raw.githubusercontent.com/ohmyzsh/ohmyzsh/master/tools/install.sh)"
```

# Install PowerLevel10K Theme for Oh My Zsh
```bash
git clone https://github.com/romkatv/powerlevel10k.git $ZSH_CUSTOM/themes/powerlevel10k
```

# Configure the terminal theme

1. Open *~/.zshrc* and change the value of `ZSH_THEME` to `ZSH_THEME="powerlevel10k/powerlevel10k"` then run `source ~/.zshrc`.
2. Restart the terminal and configure as prompted
3. `CMD ,` > Profiles > Text > set font size to 20
4. Run `curl https://raw.githubusercontent.com/josean-dev/dev-environment-files/main/coolnight.itermcolors --output ~/Downloads/coolnight.itermcolors`
5. `CMD ,` > Profiles > Colors > import downloaded profile from downloads > set colour profile

# Terminal plugins
```bash
git clone https://github.com/zsh-users/zsh-autosuggestions ${ZSH_CUSTOM:-~/.oh-my-zsh/custom}/plugins/zsh-autosuggestions 
git clone https://github.com/zsh-users/zsh-syntax-highlighting.git ${ZSH_CUSTOM:-~/.oh-my-zsh/custom}/plugins/zsh-syntax-highlighting
```

1. Open *~/.zshrc* and change the value of `plugins` to `plugins=(git zsh-autosuggestions zsh-syntax-highlighting web-search)` then run `source ~/.zshrc`.
   1. Ensure `source $ZSH/oh-my-zsh.sh` is underneath the plugins

# TMUX
1. `brew install tmux`
2. `touch ~/.tmux.conf` and paste this:

```conf
set -g prefix C-a
unbind C-b
bind-key C-a send-prefix

# Change keybinds for window splits
unbind %
bind | split-window -h

unbind '"'
bind - split-window -v

unbind %
bind | split-window -h

unbind '"'
bind - split-window -v

# Keybind to refresh this config
unbind r
bind r source-file ~/.tmux.conf

# Keybind to resize terminals
bind -r j resize-pane -D 5
bind -r k resize-pane -U 5
bind -r l resize-pane -R 5
bind -r h resize-pane -L 5

# Keybind to maximise/minimise terminals
bind -r m resize-pane -Z

# Enable mouse
set -g mouse on

# Vim copy/paste
set-window-option -g mode-keys vi

bind-key -T copy-mode-vi 'v' send -X begin-selection # start selecting text with "v"
bind-key -T copy-mode-vi 'y' send -X copy-selection # copy text with "y"

unbind -T copy-mode-vi MouseDragEnd1Pane # don't exit copy mode after dragging with mouse
```

3. Run `tmux source-file ~/.tmux.conf` in an active session 

4. `git clone https://github.com/tmux-plugins/tpm ~/.tmux/plugins/tpm` and add these to the conf file:

```conf
# tpm plugin
set -g @plugin 'tmux-plugins/tpm'

# list of tmux plugins
set -g @plugin 'christoomey/vim-tmux-navigator' # for navigating panes and vim/nvim with Ctrl-hjkl
set -g @plugin 'jimeh/tmux-themepack' # to configure tmux theme
set -g @plugin 'tmux-plugins/tmux-resurrect' # persist tmux sessions after computer restart
set -g @plugin 'tmux-plugins/tmux-continuum' # automatically saves sessions for you every 15 minutes

set -g @themepack 'powerline/default/cyan' # use this theme for tmux

set -g @resurrect-capture-pane-contents 'on' # allow tmux-ressurect to capture pane contents
set -g @continuum-restore 'on' # enable tmux-continuum functionality

# Initialize TMUX plugin manager (keep this line at the very bottom of tmux.conf)
run '~/.tmux/plugins/tpm/tpm'
```

5. Run `CTRL a r` then `CTRL a SHIFT i`