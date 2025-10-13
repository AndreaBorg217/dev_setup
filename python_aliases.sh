# ============================================================================
# PYTHON FUNCTIONS
#   => add to your ~/.bashrc and run `source ~/.bashrc`
#   => add to your ~/.zshrc and run `source ~/.zshrc`
# ============================================================================

venvc() {
    python3 -m venv .venv
    echo "Virtual environment '.venv' created."
}

venva(){
    source .venv/bin/activate
    echo "Virtual environment '.venv' activated."
}

venvi(){
    pip install -r requirements.txt
    echo "Dependencies from 'requirements.txt' installed."
}