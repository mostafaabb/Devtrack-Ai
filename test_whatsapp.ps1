# ══════════════════════════════════════════════════════════════════
# DevTrack AI - Real WhatsApp Webhook Simulation Script
# ══════════════════════════════════════════════════════════════════

$PHONE_NUMBER = Read-Host "Enter the Phone Number to test with (e.g. 96170123456)"
$MESSAGE = "Bonjour! Kifak? I want to order a Grilled Chicken Plate for delivery."

$PAYLOAD = @{
    entry = @(
        @{
            changes = @(
                @{
                    value = @{
                        messages = @(
                            @{
                                from = $PHONE_NUMBER
                                id = "WAMID.test_msg_id_" + (Get-Date -Format "yyyyMMddHHmmss")
                                text = @{
                                    body = $MESSAGE
                                }
                            }
                        )
                    }
                }
            )
        }
    )
} | ConvertTo-Json -Depth 10

Write-Host "`n🚀 Sending simulated WhatsApp message from $PHONE_NUMBER..." -ForegroundColor Blue
Write-Host "Message: $MESSAGE" -ForegroundColor Gray

try {
    $RESPONSE = Invoke-RestMethod -Method Post -Uri "http://localhost:8000/api/v1/whatsapp/webhook" -ContentType "application/json" -Body $PAYLOAD
    Write-Host "`n✅ Webhook successful!" -ForegroundColor Green
    Write-Host "The dashboard should now show the message and AI response live."
} catch {
    Write-Host "`n❌ Error triggering webhook: $_" -ForegroundColor Red
}
