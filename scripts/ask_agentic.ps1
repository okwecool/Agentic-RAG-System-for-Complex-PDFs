$ErrorActionPreference = "Stop"

$python = "python"
if ($env:CONDA_PREFIX) {
    $candidate = Join-Path $env:CONDA_PREFIX "python.exe"
    if (Test-Path $candidate) {
        $python = $candidate
    }
}

& $python -m src.graph.cli @args
