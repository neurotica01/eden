#!/bin/bash

BACKEND_SCRIPT_PATH="reverie/backend_server"
BACKEND_SCRIPT_FILE="reverie.py"
# VENV_PATH=".venv"
LOGS_PATH="../../logs"



echo "Running backend server at: http://127.0.0.1:8000/simulator_home"
timestamp=$(date +"%Y-%m-%d_%H-%M-%S")
echo "Timestamp: ${timestamp}"
mkdir -p ${LOGS_PATH}
.venv/bin/python3 ${BACKEND_SCRIPT_PATH}/${BACKEND_SCRIPT_FILE} --origin ${1} --target ${2} 2>&1 | tee ${LOGS_PATH}/${2}_${timestamp}.txt
