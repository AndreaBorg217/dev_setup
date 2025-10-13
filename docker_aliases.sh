# ============================================================================
# DOCKER FUNCTIONS
#   => add to your ~/.bashrc and run `source ~/.bashrc`
#   => add to your ~/.zshrc and run `source ~/.zshrc`
# ============================================================================

# Docker Compose log monitoring - follow last n lines (default 20) and filter for errors/warnings
dockerrs() {
    local lines=${1:-20}
    docker compose logs -f -n "$lines" | grep -E "ERROR|CRITICAL|WARNING"
}

# Docker Compose log monitoring - follow last n lines (default 20)
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

# Show all containers (including stopped)
docka() {
    docker ps -a
}

# Show container resource usage stats
docks() {
    docker stats
}

# Docker network scanner - lists all custom networks and their subnets
docknets() {
    OUTPUT_FILE="docker_networks.txt"
    
    # Clear the output file
    > "$OUTPUT_FILE"
    
    echo "Docker Network Subnet Report - $(date)" | tee -a "$OUTPUT_FILE"
    echo "=========================================" | tee -a "$OUTPUT_FILE"
    echo "" | tee -a "$OUTPUT_FILE"
    
    # Get all custom networks (excluding default bridge, host, none)
    for network in $(docker network ls --format "{{.Name}}" | grep -v "bridge\|host\|none"); do
        echo "=== $network ===" | tee -a "$OUTPUT_FILE"
        
        # Extract subnets for this network
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