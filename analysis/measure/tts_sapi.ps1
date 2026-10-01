# Generate spoken starter commands with Windows SAPI (System.Speech) for the synthetic benchmark.
# Usage: powershell -ExecutionPolicy Bypass -File tts_sapi.ps1 -OutDir <dir>
# Writes one 22.05 kHz 16-bit mono wav per (voice, rate, pitch, text) and a manifest CSV.
param(
    [Parameter(Mandatory = $true)][string]$OutDir
)
Add-Type -AssemblyName System.Speech
New-Item -ItemType Directory -Force -Path $OutDir | Out-Null
$synth = New-Object System.Speech.Synthesis.SpeechSynthesizer
$fmt = New-Object System.Speech.AudioFormat.SpeechAudioFormatInfo(22050, [System.Speech.AudioFormat.AudioBitsPerSample]::Sixteen, [System.Speech.AudioFormat.AudioChannel]::Mono)

$voices = @()
foreach ($v in $synth.GetInstalledVoices()) { if ($v.Enabled) { $voices += $v.VoiceInfo } }

# Texts: the "Set" command in a few orthographic/prosodic forms, plus "On your marks" for context.
$texts = [ordered]@{
    "set"      = "Set"
    "set_excl" = "Set!"
    "set_long" = "Sett."
    "marks"    = "On your marks"
}
$rates = @(-3, 0, 3)                  # SAPI rate, -10..10
$pitches = @("medium")  # SSML prosody pitch has no audible effect in System.Speech; pitch varied later by resampling

$manifest = @()
foreach ($vi in $voices) {
    $synth.SelectVoice($vi.Name)
    $vshort = ($vi.Name -replace "Microsoft ", "" -replace " Desktop", "").ToLower()
    $lang = $vi.Culture.Name
    foreach ($key in $texts.Keys) {
        foreach ($rate in $rates) {
            foreach ($pitch in $pitches) {
                if ($key -eq "marks" -and $pitch -ne "medium") { continue }
                $fname = "{0}_{1}_r{2}_{3}.wav" -f $vshort, $key, $rate, $pitch
                $path = Join-Path $OutDir $fname
                $synth.Rate = $rate
                $ssml = "<speak version='1.0' xmlns='http://www.w3.org/2001/10/synthesis' xml:lang='$lang'><prosody pitch='$pitch'>" + $texts[$key] + "</prosody></speak>"
                $synth.SetOutputToWaveFile($path, $fmt)
                $synth.SpeakSsml($ssml)
                $synth.SetOutputToNull()
                $manifest += [pscustomobject]@{ file = $fname; voice = $vi.Name; culture = $lang; gender = "$($vi.Gender)"; text_key = $key; text = $texts[$key]; rate = $rate; pitch = $pitch }
            }
        }
    }
}
$synth.Dispose()
$manifest | Export-Csv -NoTypeInformation -Encoding UTF8 -Path (Join-Path $OutDir "tts_manifest.csv")
Write-Output ("wrote {0} files to {1}" -f $manifest.Count, $OutDir)
