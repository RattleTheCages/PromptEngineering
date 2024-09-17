#!/bin/noop /bin/bash

# The following are the steps to install the QK AI IDE Prompt Engineering development environment.
# Onto a blink VM with a freshly loaded copy of
# debian-12-x86_64
# These steps are to be executed as root.


cd ~/.ssh
ssh-keygen -t rsa -b 4096 -C "Daniel.Huffman@machine-name"
cat id_rsa.pub
ssh root@107.172.50.181 'cat >> ~/.ssh/authorized_keys' < id_rsa.pub
cd ~
scp root@107.172.50.181:~/.bashrc .
scp root@107.172.50.181:~/.openai .
export `cat ~/.openai`
apt update
apt install python3 -y
apt install python3.11-venv
apt install --upgrade pip
apt install git -y
git config --global user.email Daniel.Huffman@gmail.com
git config --global user.name "Daniel Huffman"
mkdir projects; cd projects
git clone git@github.com:rattlethecages/PromptEngineering.git
python3 -m venv PromptEngineering
source PromptEngineering/bin/activate
pip install openai
cd PromptEngineering
python QK/QK.py

