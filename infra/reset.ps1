# Reset the stand to test data. Run from the project root:  .\infra\reset.ps1
# (comments are in English: Windows PowerShell 5.1 misreads UTF-8 files without BOM)
docker compose exec api python -m app.seed
# WireMock: drop stubs added by tests via admin API, reload stubs from infra/wiremock/mappings
Invoke-RestMethod -Method Post http://localhost:8089/__admin/reset | Out-Null
Write-Host "WireMock stubs reset to infra/wiremock/mappings"
