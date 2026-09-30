# Lets the Azure site copy notes, flags and uploaded transcripts to the repo's "inbox" branch
# (the morning sync reads them from there, files transcripts in SharePoint and tailors drafts).
param([string]$ResourceGroup = "rg-zotok-s3desk", [string]$SiteName = "zotok-s3-desk")
$sec = Read-Host "Paste the GitHub fine-grained token (input hidden)" -AsSecureString
$tok = [Runtime.InteropServices.Marshal]::PtrToStringAuto([Runtime.InteropServices.Marshal]::SecureStringToBSTR($sec))
az staticwebapp appsettings set -n $SiteName -g $ResourceGroup --setting-names "GITHUB_TOKEN=$tok" "GITHUB_REPO=wisehall-vishal/zotok-s3-desk" -o none
if ($LASTEXITCODE -ne 0) { throw "Could not save the token." }
$tok = $null
Write-Host "Saved. New notes and transcripts on the site will now reach the morning sync." -ForegroundColor Green
