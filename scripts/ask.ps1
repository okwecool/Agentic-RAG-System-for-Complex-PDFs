param(
    [Parameter(Mandatory = $true)]
    [string]$Query,
    [int]$TopK = 6,
    [switch]$TablesOnly
)

$args = @("-m", "src.generation.cli", "--query", $Query, "--top-k", $TopK)
if ($TablesOnly) {
    $args += "--tables-only"
}

python @args
