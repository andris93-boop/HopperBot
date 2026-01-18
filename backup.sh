#!/bin/sh

dirname=$(date "+%a-%H")
rm -rf backups/$dirname
mkdir -p backups/$dirname
for D in *.db; do
    sqlite3 "$D" ".backup 'backups/$dirname/$D'"
done
cp .env* backups/$dirname/
scp -i $HOME/.ssh/id_ed25519 -r backups/$dirname pi5:hopper_backup/
