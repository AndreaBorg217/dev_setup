#!/bin/bash

set -a
source "$(dirname "$0")/.env"
set +a
ansible-playbook "$(dirname "$0")/setup.yml"