#!/bin/bash -l

# Start privateGPT.py as a background process
python privateGPT.py &

# Start monitoring source_documents folder for changes
while true; do
  inotifywait -q -e create source_documents/ | while read -r file; do

    # Stop privateGPT.py
    kill $(pgrep -f privateGPT.py)

    # Run ingest.py script here
    python ingest.py

    # Start privateGPT.py again
    python privateGPT.py &
  done
done
