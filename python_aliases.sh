# ============================================================================
# PYTHON FUNCTIONS
#   => add to your ~/.bashrc and run `source ~/.bashrc`
#   => add to your ~/.zshrc and run `source ~/.zshrc`
# ============================================================================

venvc() {
    python3 -m venv .venv
}

venva(){
    source .venv/bin/activate
}

venvi(){
    pip install black
    pip install -r requirements.txt
}

venvf(){
    pip freeze > requirements.txt
}

venvd(){
    deactivate
}

pylintrc(){
    touch .pylintrc
    echo -e "[MESSAGES CONTROL]\ndisable=import-error" > .pylintrc
}
