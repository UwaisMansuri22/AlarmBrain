output "api_url" {
  description = "AlarmBrain API URL"
  value       = aws_apigatewayv2_stage.default.invoke_url
}

output "sns_topic_arn" {
  description = "SNS topic ARN for CloudWatch alarms"
  value       = aws_sns_topic.alarms.arn
}

output "s3_bucket" {
  description = "S3 bucket for incident history"
  value       = aws_s3_bucket.incidents.bucket
}

output "lambda_function" {
  description = "Lambda function name"
  value       = aws_lambda_function.alarmbrain.function_name
}
