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
    pip install black
    pip install -r requirements.txt
    echo "Dependencies from 'requirements.txt' installed."
}

venvf(){
    pip freeze > requirements.txt
}

pylintrc(){
    touch .pylintrc
    echo -e "[MESSAGES CONTROL]\ndisable=import-error" > .pylintrc
}
