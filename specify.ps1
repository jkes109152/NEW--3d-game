# Run only the Spec Kit installation belonging to this project.
$specifyExecutable = Join-Path $PSScriptRoot '.tools/spec-kit/Scripts/specify.exe'
if (-not (Test-Path -LiteralPath $specifyExecutable)) {
    throw 'Project-local Spec Kit is missing. See SPEC-KIT.md for installation instructions.'
}
& $specifyExecutable @args
exit $LASTEXITCODE
