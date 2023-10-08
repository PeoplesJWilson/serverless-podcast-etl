data "archive_file" "scrape" {
    type = "zip"
    source_file = var.path_to_source_file
    output_path = var.path_to_artifact
}

resource "aws_lambda_function" "lambda_function" {
    filename = var.path_to_artifact
    function_name = var.function_name
    role = var.lambda_iam_role_arn
    handler = var.function_handler

    memory_size = var.memory_size
    timeout = var.timeout

    source_code_hash = filebase64sha256(var.path_to_artifact)

    runtime = var.runtime

    layers = var.lambda_layer_arns

    vpc_config {
        security_group_ids = var.lambda_security_group_ids
        subnet_ids = var.lambda_subnet_ids
    }

    environment {
        variables = {
            ENV_VAR_1 = var.env_var_1
            ENV_VAR_2 = var.env_var_2
            ENV_VAR_3 = var.env_var_3
            ENV_VAR_4 = var.env_var_4
            ENV_VAR_5 = var.env_var_5
            ENV_VAR_6 = var.env_var_6  
        }
    }
}
