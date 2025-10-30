# CloudFormationデプロイスクリプト（Windows用）

param(
    [Parameter(Position=0)]
    [ValidateSet("deploy", "destroy", "status")]
    [string]$Action = "deploy",

    [string]$StackName = "hands-on-log-generator",
    [string]$Region = "ap-northeast-1"
)

switch ($Action) {
    "deploy" {
        Write-Host "Deploying CloudFormation stack: $StackName" -ForegroundColor Green

        aws cloudformation deploy `
            --template-file setup-log-generator.yaml `
            --stack-name $StackName `
            --capabilities CAPABILITY_NAMED_IAM `
            --region $Region `
            --tags Project=HandsOn Component=LogGenerator

        Write-Host ""
        Write-Host "Stack deployed successfully!" -ForegroundColor Green
        Write-Host ""
        Write-Host "Outputs:" -ForegroundColor Yellow

        aws cloudformation describe-stacks `
            --stack-name $StackName `
            --region $Region `
            --query 'Stacks[0].Outputs' `
            --output table
    }

    "destroy" {
        Write-Host "Deleting CloudFormation stack: $StackName" -ForegroundColor Yellow

        aws cloudformation delete-stack `
            --stack-name $StackName `
            --region $Region

        Write-Host "Waiting for stack deletion..." -ForegroundColor Yellow

        aws cloudformation wait stack-delete-complete `
            --stack-name $StackName `
            --region $Region

        Write-Host "Stack deleted successfully!" -ForegroundColor Green
    }

    "status" {
        Write-Host "Checking stack status: $StackName" -ForegroundColor Cyan

        aws cloudformation describe-stacks `
            --stack-name $StackName `
            --region $Region `
            --query 'Stacks[0].[StackName,StackStatus]' `
            --output table
    }
}

