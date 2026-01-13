@echo off
echo [1/3] Building Docker Image (This may take a while)...
docker build -t synthflow:latest .

echo [2/3] Saving Image to synthflow_offline.tar...
docker save -o synthflow_offline.tar synthflow:latest

echo [3/3] Done! Please copy 'synthflow_offline.tar' and 'docker-compose.yaml' to your offline machine.
pause