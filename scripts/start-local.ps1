param()

# Helper script to start local development stack
Set-Location -Path (Split-Path -Path $PSScriptRoot -Parent)

Write-Host "Starting local docker-compose stack (db, rabbitmq, web, worker)"
docker-compose up --build --remove-orphans

