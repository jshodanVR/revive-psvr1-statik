[CmdletBinding()]
param([ValidateRange(1,128)][int]$Jobs=4,[switch]$ConfigureOnly)
$ErrorActionPreference='Stop'
$root=Split-Path -Parent $PSScriptRoot
& (Join-Path $PSScriptRoot 'build-pc-vr.ps1') -Jobs $Jobs -ConfigureOnly:$ConfigureOnly
if($ConfigureOnly) { return }
& (Join-Path $PSScriptRoot 'prepare-statik.ps1')
