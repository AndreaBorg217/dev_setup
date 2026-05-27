#!/usr/bin/env bash

input=$(cat)

model=$(    jq -r '.model.display_name                       // empty' <<< "$input")
ctx_pct=$(  jq -r '.context_window.used_percentage           // empty' <<< "$input")
transcript=$(jq -r '.transcript_path                         // empty' <<< "$input")
cwd=$(      jq -r '.workspace.current_dir // .cwd           // empty' <<< "$input")
lim_5h=$(   jq -r '.rate_limits.five_hour.used_percentage   // empty' <<< "$input")
lim_7d=$(   jq -r '.rate_limits.seven_day.used_percentage   // empty' <<< "$input")

reset='\033[0m'
bold='\033[1m'
dim='\033[2m'
green='\033[32m'
yellow='\033[33m'
red='\033[31m'
magenta='\033[35m'
cyan='\033[36m'

sep="$(printf " \033[2m│\033[0m ")"

_pct_color() {
    local p; p=$(printf '%.0f' "${1:-0}")
    if   [ "$p" -ge 80 ]; then printf '%s' "$red"
    elif [ "$p" -ge 50 ]; then printf '%s' "$yellow"
    else                       printf '%s' "$green"
    fi
}

# 1. model
part_model=""
[ -n "$model" ] && part_model="$(printf "${magenta}%s${reset}" "$model")"

# 2. context bar
part_ctx=""
if [ -n "$ctx_pct" ]; then
    p=$(printf '%.0f' "$ctx_pct")
    filled=$(( p * 10 / 100 ))
    [ "$filled" -gt 10 ] && filled=10
    bar=""
    for (( i=0; i<filled;    i++ )); do bar="${bar}█"; done
    for (( i=filled; i<10;   i++ )); do bar="${bar}░"; done
    c=$(_pct_color "$p")
    part_ctx="$(printf "${c}%s %d%%%s" "$bar" "$p" "$reset")"
fi

# 3. git branch (only when cwd is a git repo)
part_branch=""
if [ -n "$cwd" ]; then
    branch=$(git -C "$cwd" symbolic-ref --short HEAD 2>/dev/null)
    [ -z "$branch" ] && branch=$(git -C "$cwd" rev-parse --short HEAD 2>/dev/null)
    [ -n "$branch" ] && part_branch="$(printf "${green} %s${reset}" "$branch")"
fi

# 4. 5h rate limit
part_5h=""
if [ -n "$lim_5h" ]; then
    p=$(printf '%.0f' "$lim_5h")
    c=$(_pct_color "$p")
    part_5h="$(printf "${c}5h:%d%%%s" "$p" "$reset")"
fi

# 5. 7d rate limit
part_7d=""
if [ -n "$lim_7d" ]; then
    p=$(printf '%.0f' "$lim_7d")
    c=$(_pct_color "$p")
    part_7d="$(printf "${c}7d:%d%%%s" "$p" "$reset")"
fi

# 6. session duration from transcript birth time
part_dur=""
if [ -n "$transcript" ] && [ -f "$transcript" ]; then
    birth=$(stat -f '%B' "$transcript" 2>/dev/null)
    [ -z "$birth" ] || [ "$birth" = "0" ] && birth=$(stat -f '%c' "$transcript" 2>/dev/null)
    if [ -n "$birth" ] && [ "$birth" != "0" ]; then
        diff=$(( $(date +%s) - birth ))
        h=$(( diff / 3600 ))
        m=$(( (diff % 3600) / 60 ))
        [ "$h" -gt 0 ] && dur="${h}h $(printf '%02d' "$m")m" || dur="${m}m"
        part_dur="$(printf "${dim}%s${reset}" "$dur")"
    fi
fi

# 7. project folder
part_project=""
[ -n "$cwd" ] && part_project="$(printf "${bold}${cyan}%s${reset}" "$(basename "$cwd")")"

parts=()
[ -n "$part_model"   ] && parts+=("$part_model")
[ -n "$part_ctx"     ] && parts+=("$part_ctx")
[ -n "$part_branch"  ] && parts+=("$part_branch")
[ -n "$part_5h"      ] && parts+=("$part_5h")
[ -n "$part_7d"      ] && parts+=("$part_7d")
[ -n "$part_dur"     ] && parts+=("$part_dur")
[ -n "$part_project" ] && parts+=("$part_project")

out=""
for i in "${!parts[@]}"; do
    [ "$i" -gt 0 ] && out="${out}${sep}"
    out="${out}${parts[$i]}"
done

printf "%b\n" "$out"
