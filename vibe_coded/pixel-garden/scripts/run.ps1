param([ValidateSet('install', 'dev', 'api', 'check', 'test', 'build')][string]$Task = 'api')
$ErrorActionPreference = 'Stop'
$appRoot = Split-Path $PSScriptRoot -Parent
Push-Location $appRoot
try {
    $appPython = Join-Path $appRoot '.venv/Scripts/python.exe'
    if ($Task -eq 'install') {
        if (-not (Test-Path -LiteralPath $appPython)) {
            $repoPython = Join-Path $appRoot '../../.venv/Scripts/python.exe'
            if (Test-Path -LiteralPath $repoPython) { & $repoPython -m venv .venv }
            elseif (Get-Command py -ErrorAction SilentlyContinue) { py -3 -m venv .venv }
            else { python -m venv .venv }
            if ($LASTEXITCODE -ne 0) { throw 'Python environment creation failed.' }
        }
        & $appPython -m pip install -r requirements.lock
        if ($LASTEXITCODE -ne 0) { throw 'Python dependency installation failed.' }
        $nodeCommand = Get-Command node -ErrorAction Stop
        $bundledPnpm = Join-Path (Split-Path $nodeCommand.Source -Parent) '../node_modules/pnpm/bin/pnpm.cjs'
        if (Get-Command pnpm -ErrorAction SilentlyContinue) { pnpm install --frozen-lockfile }
        elseif (Test-Path -LiteralPath $bundledPnpm) { & $nodeCommand.Source $bundledPnpm install --frozen-lockfile }
        elseif (Get-Command npx.cmd -ErrorAction SilentlyContinue) { npx.cmd --yes pnpm@11.25.0 install --frozen-lockfile }
        else { throw 'Install Node.js with npm, or make pnpm available on PATH.' }
    }
    elseif ($Task -eq 'api') { & $appPython -m uvicorn backend.app:app --host 127.0.0.1 --port 8000 }
    elseif ($Task -eq 'dev') { node node_modules/vite/bin/vite.js --host 127.0.0.1 }
    elseif ($Task -eq 'check') { node node_modules/typescript/bin/tsc --noEmit }
    elseif ($Task -eq 'build') {
        node node_modules/typescript/bin/tsc --noEmit
        if ($LASTEXITCODE -ne 0) { throw 'Type checking failed.' }
        node node_modules/vite/bin/vite.js build
    }
    elseif ($Task -eq 'test') {
        node node_modules/vitest/vitest.mjs run
        if ($LASTEXITCODE -ne 0) { throw 'Frontend tests failed.' }
        & $appPython -m pytest backend/tests -q
    }
    if ($LASTEXITCODE -ne 0) { throw "Task '$Task' failed with exit code $LASTEXITCODE." }
}
finally { Pop-Location }
