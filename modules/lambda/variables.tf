variable "env_var_1" {
  description = "environment variable"
  default = ""
  type        = string
}

variable "env_var_2" {
  description = "environment variable"
  default = ""
  type        = string
}

variable "env_var_3" {
  description = "environment variable"
  default = ""
  type        = string
}

variable "env_var_4" {
  description = "environment variable"
  default = ""
  type        = string
}

variable "env_var_5" {
  description = "environment variable"
  default = ""
  type        = string
}

variable "env_var_6" {
  description = "environment variable"
  default = ""
  type        = string
}


variable "lambda_iam_role_arn" {
  description = "Lambda IAM Role ARN"
  type        = string
}

variable "path_to_source_file" {
  description = "Path to Lambda Fucntion Source Code"
  type        = string
}

variable "path_to_artifact" {
  description = "Path to ZIP artifact"
  type        = string
}

variable "function_name" {
  description = "Name of Lambda Function"
  type        = string
}

variable "function_handler" {
  description = "Name of Lambda Function Handler"
  type        = string
}

variable "memory_size" {
  description = "Lambda Memory"
  type        = number
}

variable "timeout" {
  description = "Lambda Timeout"
  type        = number
}

variable "runtime" {
  description = "Lambda Runtime"
  type        = string
}

variable "lambda_layer_arns" {
  description = "lambda_layer_arns"
  type        = list(string)
  default = []
}

variable "lambda_security_group_ids" {
  description = "list of sec group ids"
  type = list(string)
  default = []
}

variable "lambda_subnet_ids" {
  description = "list of subnet ids"
  type = list(string)
  default = []
}