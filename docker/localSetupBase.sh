#!/bin/sh

# on fedora and ubuntu installation dir is different for modules
[[ -f /usr/share/Modules/init/sh ]] && source /usr/share/Modules/init/sh
[[ -f /usr/share/modules/init/sh ]] && source /usr/share/modules/init/sh

export TERM=xterm-256color
export CLICOLOR=1
export LSCOLORS="gxfxcxdxbxegedabagacad"
PROMPT='%F{yellow}%m%F{red} $%f '

alias l='\ls -lph         --color'
alias lt='\ls -lrtph       --color'
alias ll='\ls -d -lh .*    --color'
alias llt='\ls -d -lrth .*  --color'
alias lz='ls --human-readable --size -1 -S --classify' # order by size
alias gista='git branch ; git status -s'

# pelican
uid=$(id -u)
export XDG_RUNTIME_DIR=/run/user/$uid
export BEARER_TOKEN_FILE=/var/run/user/$uid/bt_u$uid


