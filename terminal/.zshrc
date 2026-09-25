# Enable Powerlevel10k instant prompt. Should stay close to the top of ~/.zshrc.
if [[ -r "${XDG_CACHE_HOME:-$HOME/.cache}/p10k-instant-prompt-${(%):-%n}.zsh" ]]; then
  source "${XDG_CACHE_HOME:-$HOME/.cache}/p10k-instant-prompt-${(%):-%n}.zsh"
fi

# Path to your Oh My Zsh installation.
export ZSH="$HOME/.oh-my-zsh"
export PATH="$HOME/.local/bin:$HOME/.local/opt/neovim/current/bin:$PATH"
export DO_NOT_TRACK=1

# Theme
ZSH_THEME="powerlevel10k/powerlevel10k"

# Plugins
plugins=(git zsh-autosuggestions zsh-syntax-highlighting web-search)

source $ZSH/oh-my-zsh.sh

# To customize prompt, run `p10k configure` or edit ~/.p10k.zsh.
[[ ! -f ~/.p10k.zsh ]] || source ~/.p10k.zsh

# ============================================================================
# OTHER FUNCTIONS
# ============================================================================

dev() {
    local attach=0
    if [[ "$1" == "-a" || "$1" == "--attach" ]]; then
        attach=1
        shift
    fi
    local session_name="${1:-${PWD:t}}"

    if tmux has-session -t "=$session_name" 2>/dev/null; then
        if (( attach )); then
            if [[ -n "$TMUX" ]]; then
                tmux switch-client -t "=$session_name"
            else
                tmux attach-session -t "=$session_name"
            fi
            return
        fi
        tmux kill-session -t "=$session_name"
    fi

    tmux new-session -d -s "$session_name" -n dev -c "$PWD" "zsh -c 'nvim; exec zsh'"
    tmux split-window -h -t "=$session_name:dev" -c "$PWD" "zsh -c 'claude; exec zsh'"
    tmux split-window -v -t "=$session_name:dev.1" -c "$PWD"
    tmux select-pane -t "=$session_name:dev.0"

    if [[ -n "$TMUX" ]]; then
        tmux switch-client -t "=$session_name"
    else
        tmux attach-session -t "=$session_name"
    fi
}

function end_session {
    tmux kill-session -t "=${1:-${PWD:t}}"
}

git() {
    # Intercept git push to protected branches
    if [[ "$1" == "push" ]]; then
        local branch
        branch=$(command git symbolic-ref --short HEAD 2>/dev/null)
        if [[ "$branch" =~ ^(master|main|prod|production)$ ]]; then
            echo "⚠️  You're about to push to '$branch'. Are you sure? (y/n)"
            read -r confirm
            [[ "$confirm" =~ ^[Yy]$ ]] || { echo "Push cancelled."; return 1; }
        fi
    fi
    command git "$@"
}
# ============================================================================
# PYTHON FUNCTIONS
# ============================================================================

alias python=python3
alias pip=pip3

# Create a new virtual environment
venvc() {
    python3 -m venv .venv
}

# Activate the virtual environment
venva(){
    source .venv/bin/activate
}

# Install project dependencies
venvi(){
    pip3 install isort # curently there's a bug that requires this
    pip3 install -r requirements.txt
}

# Freeze current dependencies to requirements.txt
venvf(){
    pip3 freeze > requirements.txt
}

# Deactivate the virtual environment
venvd(){
    deactivate
}

# Create a .pylintrc that disables import-error
pylintrc(){
    touch .pylintrc
    echo -e "[MESSAGES CONTROL]\ndisable=import-error" > .pylintrc
}


# ============================================================================
# DOCKER FUNCTIONS
# ============================================================================

# Follow last n lines of logs, filtering for errors/warnings (default: 20)
dockerrs() {
    local lines=${1:-20}
    docker compose logs -f -n "$lines" | grep -E "ERROR|CRITICAL|WARNING"
}

# Follow last n lines of logs (default: 20)
docklogs() {
    local lines=${1:-20}
    docker compose logs -f -n "$lines"
}

# Docker Compose up in detached mode
dockup() {
    docker compose up -d
}

# Docker Compose down
dockdown() {
    docker compose down
}

# Docker Compose up with build in detached mode
dockupb() {
    docker compose up -d --build
}

# Show running containers
dock() {
    docker ps
}

# Show all containers including stopped
docka() {
    docker ps -a
}

# Show container resource usage stats
docks() {
    docker stats
}

# Inspect image size
imgsize() {
    local image="$1"
    echo "Total size for $image: $(docker images "$image" --format '{{.Size}}')"
    docker history "$image" --no-trunc --format "table {{.Size}}\t{{.CreatedBy}}" > "${image//\//_}.txt"
}

# dockerignore effectiveness
dockignore () {
    docker build --no-cache --progress=plain -t test . 2>&1 | grep "transferring context"
}

# List all custom Docker networks and their subnets
docknets() {
    OUTPUT_FILE="docker_networks.txt"
    > "$OUTPUT_FILE"

    echo "Docker Network Subnet Report - $(date)" | tee -a "$OUTPUT_FILE"
    echo "=========================================" | tee -a "$OUTPUT_FILE"
    echo "" | tee -a "$OUTPUT_FILE"

    for network in $(docker network ls --format "{{.Name}}" | grep -v "bridge\|host\|none"); do
        echo "=== $network ===" | tee -a "$OUTPUT_FILE"

        subnets=$(docker network inspect "$network" | jq -r '.[].IPAM.Config[]? | select(.Subnet != null) | .Subnet' 2>/dev/null)

        if [ -n "$subnets" ]; then
            echo "$subnets" | tee -a "$OUTPUT_FILE"
        else
            echo "No subnets configured" | tee -a "$OUTPUT_FILE"
        fi

        echo "" | tee -a "$OUTPUT_FILE"
    done

    echo "Report saved to: $OUTPUT_FILE"
    echo "Total networks scanned: $(docker network ls --format "{{.Name}}" | grep -v "bridge\|host\|none" | wc -l)"
}

lsg () {
    ls | grep -iE "$@"
}

gbc () {
    git branch "$@" && git checkout "$@"
}

# Clean unused Neovim plugins and LSPs (lua spec removed ≠ uninstalled)
# - Lazy: `python = {}` in linter.lua stays installed until `Lazy clean`
# - Mason: `ensure_installed` in mason.lua doesn't auto-uninstall old servers (e.g. removed pyright)
function nvim_clean {
    echo "→ Lazy: removing unused plugins (no longer in lua spec)..."
    nvim --headless "+Lazy! clean" +qa 2>/dev/null
    echo ""
    echo "→ Mason: uninstalling packages not in mason.lua ensure_installed..."
    # actual Mason package dir names (mason-lspconfig maps lua_ls->lua-language-server etc.)
    local keep="pyright ruff gopls jdtls lua-language-server yaml-language-server dockerfile-language-server docker-compose-language-service gofumpt goimports golangci-lint gomodifytags impl yamllint yamlfmt hadolint cspell stylua prettier java-debug-adapter java-test palantir-java-format vscode-spring-boot-tools"
    for pkg in $(ls -1 ~/.local/share/nvim/mason/packages 2>/dev/null); do
        if ! echo "$keep" | tr ' ' '\n' | grep -qx "$pkg"; then
            echo "  - MasonUninstall $pkg (not in ensure_installed)"
            nvim --headless "+MasonUninstall $pkg" +qa 2>/dev/null
        else
            echo "  ✓ keep $pkg"
        fi
    done
    echo ""
    echo "  Verify with :Mason and :LspInfo"
}
alias clean_nvim=nvim_clean
