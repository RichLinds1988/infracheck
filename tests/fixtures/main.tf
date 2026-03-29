# --- Fault Tolerance ---

resource "aws_sqs_queue" "my_queue" {
  name = "my-queue"
  # no redrive_policy — should fail sqs_dlq_configured
}

resource "aws_db_instance" "my_db" {
  identifier        = "my-db"
  instance_class    = "db.t3.micro"
  engine            = "postgres"
  multi_az          = false  # should fail rds_multi_az_enabled
  backup_retention_period = 3  # should fail rds_backup_retention
  deletion_protection     = false  # should fail rds_deletion_protection
  publicly_accessible     = false
}

resource "aws_lambda_function" "my_func" {
  function_name = "my-func"
  runtime       = "python3.14"
  # no dead_letter_config — should fail lambda_dlq_configured
  # no tracing_config — should fail lambda_xray_tracing
}

resource "aws_dynamodb_table" "my_table" {
  name         = "my-table"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "id"
  # no point_in_time_recovery — should fail dynamodb_pitr_enabled
}

# --- Scalability ---

resource "aws_autoscaling_group" "my_asg" {
  name               = "my-asg"
  min_size           = 1
  max_size           = 3
  desired_capacity   = 1
  # no target_group_arns — autoscaling_elb_health_check skipped
}

# --- Security ---

resource "aws_s3_bucket_public_access_block" "my_bucket" {
  bucket                  = "my-bucket"
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_security_group" "my_sg" {
  name = "my-sg"

  ingress {
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

resource "aws_instance" "my_ec2" {
  ami           = "ami-12345678"
  instance_type = "t3.micro"

  metadata_options {
    http_tokens = "required"
  }
}

# --- Observability ---

resource "aws_cloudwatch_metric_alarm" "cpu_alarm" {
  alarm_name          = "high-cpu"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "CPUUtilization"
  namespace           = "AWS/EC2"
  period              = 120
  threshold           = 80
}

resource "aws_cloudwatch_log_group" "my_func_logs" {
  name              = "/aws/lambda/my-func"
  retention_in_days = 30
}

resource "aws_vpc" "my_vpc" {
  cidr_block = "10.0.0.0/16"
}

resource "aws_flow_log" "my_flow_log" {
  vpc_id          = "my_vpc"
  traffic_type    = "ALL"
  iam_role_arn    = "arn:aws:iam::123456789012:role/flow-log-role"
  log_destination = "arn:aws:s3:::my-flow-logs-bucket"
}
