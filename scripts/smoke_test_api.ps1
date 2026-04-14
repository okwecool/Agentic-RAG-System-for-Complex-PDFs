param(
    [string]$BaseUrl = "http://127.0.0.1:8000",
    [string]$Query = "Sora 2 有什么升级？",
    [int]$TopK = 4,
    [switch]$TablesOnly
)

$args = @(
    "-m", "src.api.smoke_test",
    "--base-url", $BaseUrl,
    "--query", $Query,
    "--top-k", $TopK
)
if ($TablesOnly) {
    $args += "--tables-only"
}

python @args
