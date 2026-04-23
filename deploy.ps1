# ══════════════════════════════════════════════════════════════════
# DevTrack AI - Production Deployment & Management Script (PowerShell)
# ══════════════════════════════════════════════════════════════════

# Colors
Write-Host "🚀 Beginning DevTrack AI Production Setup..." -ForegroundColor Blue

# Function: Generate Secure Secret
function New-Secret {
    [Convert]::ToBase64String((1..32 | ForEach-Object { [byte](Get-Random -Minimum 0 -Maximum 255) }))
}

# 1. Check/Generate .env file
if (-not (Test-Path .env)) {
    Write-Host "⚠️  No .env file found. Generating from production template..." -ForegroundColor Yellow
    Copy-Item .env.production .env
    
    # Generate random secrets
    $SECRET_KEY = New-Secret
    $JWT_SECRET_KEY = New-Secret
    $DB_PASSWORD = New-Secret
    
    # Update .env (multi-line replacement)
    (Get-Content .env) -replace "CHANGE_ME_GENERATE_A_SECURE_64_CHAR_HEX_STRING", $SECRET_KEY `
                   -replace "CHANGE_ME_STRONG_DATABASE_PASSWORD", $DB_PASSWORD | Set-Content .env
    
    Write-Host "✅ .env file created with secure generated secrets." -ForegroundColor Green
    Write-Host "👉 IMPORTANT: Manually add your GEMINI_API_KEY to the .env file!" -ForegroundColor Yellow
}

# 2. Setup SSL Certificate Directory
if (-not (Test-Path nginx\ssl)) { New-Item -ItemType Directory -Path nginx\ssl }
if (-not (Test-Path nginx\ssl\cert.pem)) {
    Write-Host "⚠️  No SSL certificates found. Please generate them for production." -ForegroundColor Yellow
    Write-Host "Self-signed certificate generation instructions are in nginx\ssl\README.md" -ForegroundColor Gray
}

# 3. Start Infrastructure Stack
Write-Host "🐳 Starting Docker Compose stack (Production mode)..." -ForegroundColor Blue
docker-compose -f docker-compose.prod.yml up -d --build

# 4. Wait for Setup
Write-Host "⏳ Waiting for initial setup (15s)..." -ForegroundColor Gray
Start-Sleep -Seconds 15

# 5. Run Database Migrations
Write-Host "🗄️  Running database migrations..." -ForegroundColor Blue
docker-compose -f docker-compose.prod.yml exec api alembic upgrade head

# 6. Check Health
Write-Host "📡 Checking system health..." -ForegroundColor Blue
try {
    $HEALTH = Invoke-RestMethod -Uri "http://localhost/api/health"
    if ($HEALTH.status -eq "healthy") {
        Write-Host "✅ SYSTEM IS ONLINE AND HEALTHY!" -ForegroundColor Green
        Write-Host "   - Dashboard: https://localhost"
        Write-Host "   - API Docs: https://localhost/api/docs"
    } else {
        Write-Host "❌ Health check failed. Check logs with: docker-compose logs api" -ForegroundColor Red
    }
} catch {
    Write-Host "❌ Health check failed. API may still be starting..." -ForegroundColor Red
}

Write-Host "Done!" -ForegroundColor Blue
