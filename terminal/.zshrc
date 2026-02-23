# Enable Powerlevel10k instant prompt. Should stay close to the top of ~/.zshrc.
if [[ -r "${XDG_CACHE_HOME:-$HOME/.cache}/p10k-instant-prompt-${(%):-%n}.zsh" ]]; then
  source "${XDG_CACHE_HOME:-$HOME/.cache}/p10k-instant-prompt-${(%):-%n}.zsh"
fi

# Path to your Oh My Zsh installation.
export ZSH="$HOME/.oh-my-zsh"

# Theme
ZSH_THEME="powerlevel10k/powerlevel10k"

# Plugins
plugins=(git zsh-autosuggestions zsh-syntax-highlighting web-search)

source $ZSH/oh-my-zsh.sh

# To customize prompt, run `p10k configure` or edit ~/.p10k.zsh.
[[ ! -f ~/.p10k.zsh ]] || source ~/.p10k.zsh


# ============================================================================
# PYTHON FUNCTIONS
# ============================================================================

# Create a new virtual environment using Python 3.12
venvc() {
    python3.12 -m venv .venv
}

# Activate the virtual environment
venva(){
    source .venv/bin/activate
}

# Install black and project dependencies
venvi(){
    pip3 install black
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
