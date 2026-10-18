param(
    [string]$Region = "ap-south-1",
    [string]$Repository = "hisaabset",
    [string]$Tag = "latest",
    [switch]$LiveEmail
)

$ErrorActionPreference = "Stop"

function Require-Command([string]$Name) {
    if (-not (Get-Command $Name -ErrorAction SilentlyContinue)) {
        throw "Required command '$Name' was not found in PATH."
    }
}

Require-Command "aws"
Require-Command "docker"

$accountId = (aws sts get-caller-identity --query Account --output text --no-cli-pager).Trim()
if (-not $accountId -or $accountId -notmatch "^\d{12}$") {
    throw "AWS identity could not be resolved. Run 'aws configure' or use an AWS profile."
}

$registry = "$accountId.dkr.ecr.$Region.amazonaws.com"
$image = "$registry/$Repository`:$Tag"

Write-Host "Authenticating Docker with ECR..."
aws ecr get-login-password --region $Region |
    docker login --username AWS --password-stdin $registry

Write-Host "Building $image..."
docker build --tag $image (Join-Path $PSScriptRoot "..\..")

Write-Host "Pushing $image..."
docker push $image

$mode = "true"
if ($LiveEmail) {
    $mode = "false"
    Write-Warning "Live email mode requested. Confirm SES identity, IAM, and recipient approval before deployment."
}

$templatePath = Join-Path $PSScriptRoot "hisaabset-task-definition.template.json"
$renderedPath = Join-Path $PSScriptRoot "hisaabset-task-definition.rendered.json"
$template = Get-Content -Raw -LiteralPath $templatePath
$template = $template.Replace("<AWS_ACCOUNT_ID>", $accountId)
$template = $template.Replace("<ECS_EXECUTION_ROLE>", "ecsTaskExecutionRole")
$template = $template.Replace("<HISAABSET_TASK_ROLE>", "HisaabsetEcsTaskRole")
$template = $template.Replace("<ECR_IMAGE_URI>", $image)
$definition = $template | ConvertFrom-Json
$emailMode = $definition.containerDefinitions[0].environment |
    Where-Object { $_.name -eq "HISAABSET_EMAIL_TEST_MODE" }
$emailMode.value = $mode
[System.IO.File]::WriteAllText($renderedPath, ($definition | ConvertTo-Json -Depth 20), (New-Object System.Text.UTF8Encoding($false)))

Write-Host ""
Write-Host "Image pushed: $image"
Write-Host "Rendered task definition: $renderedPath"
Write-Host "Next steps:"
Write-Host "  1. Register the rendered task definition in ECS."
Write-Host "  2. Create/update the Fargate service and load balancer."
Write-Host "  3. Keep HISAABSET_EMAIL_TEST_MODE=true until a controlled test passes."
