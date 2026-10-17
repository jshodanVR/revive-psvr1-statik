# Optional config/material overlay. Off never reads/rebuilds the game archive.
function Set-StatikEnhancedEdition {
    [CmdletBinding()]
    param([Parameter(Mandatory)][string]$Game, [bool]$Enabled=$false, [switch]$IgnoreUpdate)
    $base=[IO.Path]::GetFullPath((Split-Path -Parent $Game))
    $folder=Join-Path $base 'deadlock\content\paks'
    $target=Join-Path $folder 'revivepsvr1-enhanced_P.pak'
    $receipt=Join-Path $folder 'revivepsvr1-enhanced.receipt.json'
    if ((Test-Path -LiteralPath $receipt) -and ((Get-Item -LiteralPath $receipt).Attributes -band [IO.FileAttributes]::ReparsePoint)) {
        throw 'Enhanced receipt must be a regular file.'
    }
    # Never overwrite/delete a user file merely because it has our filename.
    $known=@()
    if (Test-Path -LiteralPath $target) {
        if ((Get-Item -LiteralPath $target).Attributes -band [IO.FileAttributes]::ReparsePoint) { throw 'Enhanced override must be a regular file.' }
        if (!(Test-Path -LiteralPath $receipt)) { throw 'Unmanaged Statik Enhanced override found. It was not changed; launch stopped.' }
        $installed=Get-Content -LiteralPath $receipt -Raw | ConvertFrom-Json
        if ($installed.Owner -ne 'RevivePSVR1.StatikEnhanced') { throw 'Unmanaged Statik Enhanced receipt; launch stopped.' }
        $known=@($installed.AcceptedHashes)
        if ((Get-FileHash -LiteralPath $target).Hash -notin $known) { throw 'Statik Enhanced override was modified externally. It was not changed; launch stopped.' }
    }
    if (!$Enabled) {
        if (Test-Path -LiteralPath $target) { Remove-Item -LiteralPath $target }
        Write-Output 'Statik Enhanced edition: OFF (original textures and materials).'
        return
    }
    if ((Test-Path -LiteralPath ($base+'-UPDATE\eboot.bin')) -and !$IgnoreUpdate) { throw 'Statik Enhanced edition has not been verified with an update overlay. Disable Enhanced to play this version.' }
    if ((Get-FileHash -LiteralPath $Game).Hash -ne '2F38FC89C11EB7F42E083DD0D2745F905AD9034CDD9CEA9C7FACF065DD0AA24E') {
        throw 'Statik Enhanced edition requires the verified CUSA06929 executable. Disable Enhanced to play this version.'
    }
    if (!('StatikEnhanced' -as [type])) { Add-Type -Path (Join-Path $PSScriptRoot 'StatikEnhanced.cs') }
    $pak=[StatikEnhanced]::Build((Join-Path $folder 'deadlock-ps4.pak'),(Join-Path $PSScriptRoot 'assets\statik-enhanced-material.bin'))
    $sha=[Security.Cryptography.SHA256]::Create()
    try { $hash=[BitConverter]::ToString($sha.ComputeHash($pak)).Replace('-','') } finally { $sha.Dispose() }
    if ((Test-Path -LiteralPath $target) -and (Get-FileHash -LiteralPath $target).Hash -eq $hash) {
        Write-Output 'Statik Enhanced edition: ON (texture filtering and selected surface materials).'
        return
    }
    $temp=$target+'.tmp-'+[Guid]::NewGuid().ToString('N')
    $receiptTemp=$receipt+'.tmp-'+[Guid]::NewGuid().ToString('N')
    try {
        [IO.File]::WriteAllBytes($temp,$pak)
        if ((Get-FileHash -LiteralPath $temp).Hash -ne $hash) { throw 'Enhanced profile did not verify.' }
        # Journal both old/new hashes first: either side of an interrupted atomic
        # replacement can be identified and disabled on the next launch.
        @{ Owner='RevivePSVR1.StatikEnhanced'; Revision=[StatikEnhanced]::Revision; AcceptedHashes=@(@($known)+@($hash) | Select-Object -Unique) } |
            ConvertTo-Json | Set-Content -LiteralPath $receiptTemp -Encoding UTF8
        if (Test-Path -LiteralPath $receipt) { [IO.File]::Replace($receiptTemp,$receipt,[System.Management.Automation.Language.NullString]::Value) }
        else { [IO.File]::Move($receiptTemp,$receipt) }
        if (Test-Path -LiteralPath $target) { [IO.File]::Replace($temp,$target,[System.Management.Automation.Language.NullString]::Value) }
        else { [IO.File]::Move($temp,$target) }
    } finally {
        foreach ($file in @($temp,$receiptTemp)) { if (Test-Path -LiteralPath $file) { Remove-Item -LiteralPath $file } }
    }
    Write-Output 'Statik Enhanced edition: ON (texture filtering and selected surface materials).'
}
