# S3 Follow-up Desk -> Azure Static Web App (+ Table Storage), linked to the GitHub repo.
# Run from PowerShell on a PC where `az login` is already done:
#   powershell -ExecutionPolicy Bypass -File deploy.ps1 -Repo https://github.com/<owner>/zotok-s3-desk
param(
  [Parameter(Mandatory=$true)][string]$Repo,
  [string]$ResourceGroup = "rg-zotok-s3desk",
  [string]$Location = "centralindia",
  [string]$SiteName = "zotok-s3-desk",
  [string]$SiteRegion = "eastasia"
)
$ErrorActionPreference = "Stop"
Write-Host "`n== 1/5 Azure account" -ForegroundColor Cyan
az account show --query "{subscription:name, user:user.name}" -o table
if ($LASTEXITCODE -ne 0) { throw "Run 'az login' first." }
az provider register -n Microsoft.Web --wait | Out-Null
az provider register -n Microsoft.Storage --wait | Out-Null

Write-Host "`n== 2/5 Resource group and storage (notes, drafts, transcripts)" -ForegroundColor Cyan
az group create -n $ResourceGroup -l $Location -o none
$storage = az storage account list -g $ResourceGroup --query "[0].name" -o tsv
if (-not $storage) {
  $storage = "zotoks3desk" + (Get-Random -Minimum 1000 -Maximum 9999)
  az storage account create -n $storage -g $ResourceGroup -l $Location --sku Standard_LRS --kind StorageV2 --min-tls-version TLS1_2 --allow-blob-public-access false -o none
}
$conn = az storage account show-connection-string -n $storage -g $ResourceGroup --query connectionString -o tsv
Write-Host "Storage: $storage"

Write-Host "`n== 3/5 Static Web App linked to $Repo (a GitHub sign-in code will appear)" -ForegroundColor Cyan
$exists = az staticwebapp list -g $ResourceGroup --query "[?name=='$SiteName'] | length(@)" -o tsv
if ($exists -eq "0") {
  az staticwebapp create -n $SiteName -g $ResourceGroup -l $SiteRegion --sku Free `
    --source $Repo --branch main --app-location "app" --api-location "api" --output-location "" `
    --login-with-github -o none
}

Write-Host "`n== 4/5 App settings (your Anthropic API key stays in Azure)" -ForegroundColor Cyan
$sec = Read-Host "Paste the Anthropic API key (input hidden)" -AsSecureString
$key = [Runtime.InteropServices.Marshal]::PtrToStringAuto([Runtime.InteropServices.Marshal]::SecureStringToBSTR($sec))
az staticwebapp appsettings set -n $SiteName -g $ResourceGroup --setting-names `
  "STORAGE_CONNECTION=$conn" "ALLOWED_DOMAIN=zotok.ai" "ANTHROPIC_API_KEY=$key" "ANTHROPIC_MODEL=claude-sonnet-5-5" -o none
$key = $null

Write-Host "`n== 5/5 Done" -ForegroundColor Green
$hostName = az staticwebapp show -n $SiteName -g $ResourceGroup --query defaultHostname -o tsv
Write-Host "Site: https://$hostName  (first deploy takes ~3 minutes; watch the repo's Actions tab)"
Write-Host "Sign-in: any @zotok.ai Microsoft account. Others can sign in but see no data."
