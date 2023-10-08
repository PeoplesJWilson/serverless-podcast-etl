data "archive_file" "layer" {
    type = "zip"
    source_dir = var.path_to_layer_source
    output_path = var.path_to_layer_artifact
}

resource "aws_s3_bucket" "b" {
  bucket = var.layer_bucket_name
}

resource "aws_s3_object" "object" {
  bucket = aws_s3_bucket.b.id
  key    = var.layer_object_name
  source = data.archive_file.layer.output_path
}

resource "aws_lambda_layer_version" "lambda_layer" {
    s3_bucket = aws_s3_bucket.b.id
    s3_key = aws_s3_object.object.id
    layer_name = var.layer_name

    compatible_runtimes = var.compatible_layer_runtimes
    compatible_architectures = var.compatible_architectures
}