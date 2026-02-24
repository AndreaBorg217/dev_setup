#!/bin/bash

set -e  # Exit on error

REPO_DIR="$HOME/Documents/GitHub/dev_setup"
DOTFILES_REPO="https://github.com/AndreaBorg217/dev_setup.git"
BRANCH="ansible-refactor"

echo "========================================================"
echo "Andrea's Developer Setup - Automated Installation"
echo "========================================================"

# ============================================================================
# STEP 1: Bootstrap Dependencies
# ============================================================================

echo ""
echo "Step 1: Installing dependencies (Homebrew, Git, Ansible)..."
echo ""

# Check if Homebrew is installed
if ! command -v brew &> /dev/null; then
    echo "Installing Homebrew..."
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
    echo 'eval "$(/opt/homebrew/bin/brew shellenv)"' >> $HOME/.zprofile
    eval "$(/opt/homebrew/bin/brew shellenv)"
else
    echo "Homebrew already installed"
fi

# Ensure brew is in PATH
if ! command -v brew &> /dev/null; then
    eval "$(/opt/homebrew/bin/brew shellenv)"
fi

# Install Git
if ! command -v git &> /dev/null; then
    echo "Installing Git..."
    brew install git
else
    echo "Git already installed"
fi

# Install Ansible
if ! command -v ansible &> /dev/null; then
    echo "Installing Ansible..."
    brew install ansible ansible-lint
else
    echo "Ansible already installed"
fi

# ============================================================================
# STEP 2: Clone Repository (if not already done)
# ============================================================================

echo ""
echo "Step 2: Setting up dotfiles repository..."
echo ""

if [ ! -d "$REPO_DIR/.git" ]; then
    echo "Cloning repository..."
    mkdir -p "$(dirname "$REPO_DIR")"
    git clone "$DOTFILES_REPO" "$REPO_DIR"
    cd "$REPO_DIR"
    git checkout "$BRANCH"
else
    echo "Repository already cloned at $REPO_DIR"
    cd "$REPO_DIR"
    git fetch
    git pull
fi

# ============================================================================
# STEP 3: Configure Environment Variables
# ============================================================================

echo ""
echo "Step 3: Configuring environment variables..."
echo ""


# Check that GIT_USER_NAME and GIT_USER_EMAIL are set and if not kaboom
if [ -z "$GIT_USER_NAME" ] || [ -z "$GIT_USER_EMAIL" ]; then
    echo "Error: GIT_USER_NAME and GIT_USER_EMAIL environment variables must be set before running this script."
    echo "Please set them and re-run the script."
    exit 1
fi


# ============================================================================
# STEP 4: Run Ansible Playbook
# ============================================================================

echo ""
echo "Step 4: Running Ansible playbook..."
echo ""

cd "$REPO_DIR"

echo "Running full setup (this may take a while)..."
ansible-playbook setup.yml 

# ============================================================================
# COMPLETION
# ============================================================================

echo ""
echo "========================================================"
echo "Installation complete!"
echo "========================================================"
echo ""
echo "Please restart your terminal or run 'exec zsh' to load the new configuration."
echo ""
echo "Next steps: Refer to README.md for manual steps"
