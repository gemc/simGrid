#!/bin/zsh

# use ssh agent to grab a new token
uid=$(id -u)
export XDG_RUNTIME_DIR=/run/user/$uid
export BEARER_TOKEN_FILE=/var/run/user/$uid/bt_u$uid

# first time run

if [ -d /root/.ssh ]; then
	cp /sshkeys/id_ed25519 /root/.ssh
	[ -d /var/run/user/$uid ] || mkdir -p /var/run/user/$uid
	chmod 600 /root/.ssh/id_ed25519
fi

eval $(ssh-agent -s)
ssh-add
htgettoken --nooidc -v -a htvault.jlab.org -i jlab -r clas12 --credkey gemc@jlab.org
ssh-agent -k
