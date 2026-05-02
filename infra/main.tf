terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

# S3 bucket for incident history
resource "aws_s3_bucket" "incidents" {
  bucket = "${var.project_name}-incidents-${var.environment}"
}

resource "aws_s3_bucket_versioning" "incidents" {
  bucket = aws_s3_bucket.incidents.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_public_access_block" "incidents" {
  bucket                  = aws_s3_bucket.incidents.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# Lambda function
resource "aws_lambda_function" "alarmbrain" {
  filename         = "../lambda.zip"
  function_name    = "${var.project_name}-${var.environment}"
  role             = aws_iam_role.lambda_role.arn
  handler          = "app.main.handler"
  runtime          = "python3.11"
  timeout          = 30
  memory_size      = 256
  source_code_hash = filebase64sha256("../lambda.zip")

  environment {
    variables = {
      ENVIRONMENT      = var.environment
      S3_BUCKET_NAME   = aws_s3_bucket.incidents.bucket
      ANTHROPIC_API_KEY = var.claude_api_key
    }
  }
}

# SNS topic
resource "aws_sns_topic" "alarms" {
  name = "${var.project_name}-alarms-${var.environment}"
}

# SNS → Lambda subscription
resource "aws_sns_topic_subscription" "lambda" {
  topic_arn = aws_sns_topic.alarms.arn
  protocol  = "lambda"
  endpoint  = aws_lambda_function.alarmbrain.arn
}

# Allow SNS to invoke Lambda
resource "aws_lambda_permission" "sns" {
  statement_id  = "AllowSNSInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.alarmbrain.function_name
  principal     = "sns.amazonaws.com"
  source_arn    = aws_sns_topic.alarms.arn
}

# API Gateway
resource "aws_apigatewayv2_api" "alarmbrain" {
  name          = "${var.project_name}-api-${var.environment}"
  protocol_type = "HTTP"
}

resource "aws_apigatewayv2_integration" "lambda" {
  api_id                 = aws_apigatewayv2_api.alarmbrain.id
  integration_type       = "AWS_PROXY"
  integration_uri        = aws_lambda_function.alarmbrain.invoke_arn
  payload_format_version = "2.0"
}

resource "aws_apigatewayv2_route" "analyze" {
  api_id    = aws_apigatewayv2_api.alarmbrain.id
  route_key = "POST /analyze"
  target    = "integrations/${aws_apigatewayv2_integration.lambda.id}"
}

resource "aws_apigatewayv2_route" "health" {
  api_id    = aws_apigatewayv2_api.alarmbrain.id
  route_key = "GET /health"
  target    = "integrations/${aws_apigatewayv2_integration.lambda.id}"
}

resource "aws_apigatewayv2_stage" "default" {
  api_id      = aws_apigatewayv2_api.alarmbrain.id
  name        = "$default"
  auto_deploy = true
}

resource "aws_lambda_permission" "api_gateway" {
  statement_id  = "AllowAPIGatewayInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.alarmbrain.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.alarmbrain.execution_arn}/*/*"
}

# CloudWatch log group
resource "aws_cloudwatch_log_group" "alarmbrain" {
  name              = "/aws/lambda/${var.project_name}-${var.environment}"
  retention_in_days = 14
}
