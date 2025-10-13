# Install fd
```bash
brew install fd
```

# Delete existing configs
```bash
sudo rm -rf ~/.config/nvim
sudo rm -rf ~/.local/state/nvim
sudo rm -rf ~/.local/share/nvim
```

# Create dirs
```bash
sudo mkdir ~/.config/nvim
sudo chown -R andreaborg:staff ~/.config/nvim
```

# Copy configs 
```bash
cp -a ~/Downloads/dev-setup/neovim/ ~/.config/nvim
```