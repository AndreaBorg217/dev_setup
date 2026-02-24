#!/bin/bash

# INSTALL HOMEBREW
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
echo 'eval "$(/opt/homebrew/bin/brew shellenv)"' >> $HOME/.zprofile
eval "$(/opt/homebrew/bin/brew shellenv)"

# INSTALL GIT
brew install git

# INSTALL ANSIBLE
brew install ansible
brew install ansible-lint

# Clone dotfiles
mkdir -p $HOME/Documents/GitHub/dev_setup
git clone https://github.com/AndreaBorg217/dev_setup.stow $HOME/Documents/GitHub/dev_setup
