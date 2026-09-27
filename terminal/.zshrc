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

# ============================================================================
# DOCKER FUNCTIONS
# Some of these (image size inspection, dockerignore effectiveness) are from
# https://devopscube.com/kubeflow-docker-image-optmization/
# ============================================================================

# Follow last n lines of logs, filtering for errors/warnings (default: 20)
dockerrs() {
    if [[ "$1" == "--help" || "$1" == "-h" ]]; then
        echo "Usage: dockerrs [lines]  (default: 20)"
        return 0
    fi
    local lines=${1:-20}
    docker compose logs -f -n "$lines" | grep -E "ERROR|CRITICAL|WARNING"
}

# Follow last n lines of logs (default: 20)
docklogs() {
    if [[ "$1" == "--help" || "$1" == "-h" ]]; then
        echo "Usage: docklogs [lines]  (default: 20)"
        return 0
    fi
    local lines=${1:-20}
    docker compose logs -f -n "$lines"
}

# Docker Compose up in detached mode
dockup() {
    [[ "$1" == "--help" || "$1" == "-h" ]] && { echo "Usage: dockup  (docker compose up -d)"; return 0; }
    docker compose up -d
}

# Docker Compose down
dockdown() {
    [[ "$1" == "--help" || "$1" == "-h" ]] && { echo "Usage: dockdown  (docker compose down)"; return 0; }
    docker compose down
}

# Docker Compose up with build in detached mode
dockupb() {
    [[ "$1" == "--help" || "$1" == "-h" ]] && { echo "Usage: dockupb  (docker compose up -d --build)"; return 0; }
    docker compose up -d --build
}

# Show running containers
dock() {
    [[ "$1" == "--help" || "$1" == "-h" ]] && { echo "Usage: dock  (docker ps)"; return 0; }
    docker ps
}

# Show all containers including stopped
docka() {
    [[ "$1" == "--help" || "$1" == "-h" ]] && { echo "Usage: docka  (docker ps -a)"; return 0; }
    docker ps -a
}

# Show container resource usage stats
docks() {
    [[ "$1" == "--help" || "$1" == "-h" ]] && { echo "Usage: docks  (docker stats)"; return 0; }
    docker stats
}

# Inspect image size
imgsize() {
    if [[ -z "$1" || "$1" == "--help" || "$1" == "-h" ]]; then
        echo "Usage: imgsize <image>"
        return 0
    fi
    local image="$1"
    echo "Total size for $image: $(docker images "$image" --format '{{.Size}}')"
    docker history "$image" --no-trunc --format "table {{.Size}}\t{{.CreatedBy}}" > "${image//\//_}.txt"
}

# dockerignore effectiveness
dockignore () {
    [[ "$1" == "--help" || "$1" == "-h" ]] && { echo "Usage: dockignore  (builds with no cache, greps transfer context size)"; return 0; }
    docker build --no-cache --progress=plain -t test . 2>&1 | grep "transferring context"
}

# List all custom Docker networks and their subnets
docknets() {
    [[ "$1" == "--help" || "$1" == "-h" ]] && { echo "Usage: docknets  (writes docker_networks.txt with subnets per network)"; return 0; }
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

# ============================================================================
# KUBECTL FUNCTIONS
# ============================================================================

# Switch kubectl context (no arg: list contexts)
kctx() {
    if [[ "$1" == "--help" || "$1" == "-h" ]]; then
        echo "Usage: kctx [context-name]  (no arg: list contexts)"
        return 0
    fi
    if [ -z "$1" ]; then
        kubectl config get-contexts
    else
        kubectl config use-context "$1"
    fi
}

# Switch kubectl namespace (no arg: list namespaces)
kname() {
    if [[ "$1" == "--help" || "$1" == "-h" ]]; then
        echo "Usage: kname [namespace]  (no arg: list namespaces)"
        return 0
    fi
    if [ -z "$1" ]; then
        kubectl get namespaces
    else
        kubectl config set-context --current --namespace="$1"
    fi
}

# Follow logs of the first pod matching a name pattern (default tail: 100 lines)
klogs() {
    if [[ -z "$1" || "$1" == "--help" || "$1" == "-h" ]]; then
        echo "Usage: klogs <pod-name-pattern> [container]"
        return 0
    fi
    local pattern="$1"
    local container="$2"
    local pod
    pod=$(kubectl get pods --no-headers -o custom-columns=":metadata.name" | grep "$pattern" | head -n1)
    if [ -z "$pod" ]; then
        echo "No pod matching '$pattern' found"
        return 1
    fi
    if [ -n "$container" ]; then
        kubectl logs -f --tail=100 "$pod" -c "$container"
    else
        kubectl logs -f --tail=100 "$pod"
    fi
}

# Follow logs of the first pod matching a name pattern, filtered for errors/warnings
kerrs() {
    if [[ -z "$1" || "$1" == "--help" || "$1" == "-h" ]]; then
        echo "Usage: kerrs <pod-name-pattern> [container]"
        return 0
    fi
    local pattern="$1"
    local container="$2"
    local pod
    pod=$(kubectl get pods --no-headers -o custom-columns=":metadata.name" | grep "$pattern" | head -n1)
    if [ -z "$pod" ]; then
        echo "No pod matching '$pattern' found"
        return 1
    fi
    if [ -n "$container" ]; then
        kubectl logs -f --tail=100 "$pod" -c "$container" | grep -E "ERROR|CRITICAL|WARNING|Exception"
    else
        kubectl logs -f --tail=100 "$pod" | grep -E "ERROR|CRITICAL|WARNING|Exception"
    fi
}

# List pods, sorted by age; pass through extra flags e.g. -n <ns>, -A, or -o wide
kpods() {
    if [[ "$1" == "--help" || "$1" == "-h" ]]; then
        echo "Usage: kpods [kubectl-get-flags]  (e.g. -n <ns>, -A, -o wide)"
        return 0
    fi
    kubectl get pods --sort-by=.metadata.creationTimestamp "$@"
}

# List deployments (wide output, sorted by age); pass through extra flags e.g. -n <ns> or -A
kdeps() {
    if [[ "$1" == "--help" || "$1" == "-h" ]]; then
        echo "Usage: kdeps [kubectl-get-flags]  (e.g. -n <ns>, -A)"
        return 0
    fi
    kubectl get deployments -o wide --sort-by=.metadata.creationTimestamp "$@"
}

# List services (wide output, sorted by age); pass through extra flags e.g. -n <ns> or -A
ksvcs() {
    if [[ "$1" == "--help" || "$1" == "-h" ]]; then
        echo "Usage: ksvcs [kubectl-get-flags]  (e.g. -n <ns>, -A)"
        return 0
    fi
    kubectl get services -o wide --sort-by=.metadata.creationTimestamp "$@"
}

# Describe a resource, e.g. kdesc pod my-pod, kdesc deployment my-deploy
kdesc() {
    if [[ "$1" == "--help" || "$1" == "-h" ]]; then
        echo "Usage: kdesc <resource-type> <name> [-n <namespace>]"
        echo "  e.g. kdesc pod my-pod, kdesc deployment my-deploy -n my-ns"
        return 0
    fi
    kubectl describe "$@"
}

# List events sorted by creation timestamp; pass through extra flags e.g. -n <ns> or -A
# First bare (non-flag) arg is treated as an object name and filtered via field-selector,
# e.g. `kevents my-pod -n my-ns` shows events for my-pod in my-ns.
kevents() {
    if [[ "$1" == "--help" || "$1" == "-h" ]]; then
        echo "Usage: kevents [object-name] [kubectl-get-flags]  (e.g. -n <ns>, -A)"
        return 0
    fi
    local name=""
    if [[ -n "$1" && "$1" != -* ]]; then
        name="$1"
        shift
    fi
    if [[ -n "$name" ]]; then
        kubectl get events --sort-by=.metadata.creationTimestamp --field-selector "involvedObject.name=$name" "$@"
    else
        kubectl get events --sort-by=.metadata.creationTimestamp "$@"
    fi
}

# List pods by CPU usage (metrics-server required); pass through extra flags e.g. -n <ns> or -A
kcpu() {
    if [[ "$1" == "--help" || "$1" == "-h" ]]; then
        echo "Usage: kcpu [kubectl-top-flags]  (e.g. -n <ns>, -A)"
        return 0
    fi
    kubectl top pods --sort-by=cpu "$@"
}

# List pods by memory usage (metrics-server required); pass through extra flags e.g. -n <ns> or -A
kram() {
    if [[ "$1" == "--help" || "$1" == "-h" ]]; then
        echo "Usage: kram [kubectl-top-flags]  (e.g. -n <ns>, -A)"
        return 0
    fi
    kubectl top pods --sort-by=memory "$@"
}

# Generate a resource manifest via client-side dry-run, e.g. kgen deploy.yaml deployment my-app --image=nginx
kgen() {
    if [[ -z "$1" || -z "$2" || "$1" == "--help" || "$1" == "-h" ]]; then
        echo "Usage: kgen <outfile> <kubectl-create-args...>"
        echo "  e.g. kgen deploy.yaml deployment my-app --image=nginx"
        return 0
    fi
    local outfile="$1"
    shift
    kubectl create "$@" --dry-run=client -o yaml > "$outfile"
}

lsg () {
    ls | grep -iE "$@"
}

gbc () {
    git branch "$@" && git checkout "$@"
}
