#!/bin/bash

if [ -d "dhq-journal" ]; then
    echo "folder exists"
else
    echo "folder does not exist, downloading the data"
    git clone --depth 1 --filter=blob:none --sparse https://github.com/Digital-Humanities-Quarterly/dhq-journal.git
    cd dhq-journal
    git sparse-checkout set articles
    cd ..
fi
echo "done"
