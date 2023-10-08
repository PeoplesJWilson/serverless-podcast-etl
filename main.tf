# creates vpc, 2 private subnets, 1 public subnet, nat gateway, igw, some routes, and vpc-sg
module "networking" {
    source = "./modules/networking"
}

# create s3 buckets
module "rssBucket" {
    source = "./modules/s3"
    s3_bucket_name = local.rss_bucket_name
}
module "mp3ChunksBucket" {
    source = "./modules/s3"

    s3_bucket_name = local.mp3_chunks_bucket_name
}
module "transcriptionChunksBucket" {
    source = "./modules/s3"
    s3_bucket_name = local.transcription_chunks_bucket_name
}
module "fullTranscriptionBucket" {
    source = "./modules/s3"
    s3_bucket_name = local.full_transcription_bucket_name
}
module "sentimentBucket" {
    source = "./modules/s3"
    s3_bucket_name = local.sentiment_bucket_name
}
module "entityBucket" {
    source = "./modules/s3"
    s3_bucket_name = local.entity_bucket_name
}



#___________ Security config for rds database__________

# sec group for lambda-sg
resource "aws_security_group" "lambda_sg" {
    name        = local.lambda_sg_name
    description = "security group for lambda"
    vpc_id      = module.networking.main_vpc_id

    ingress {
      from_port          = 8050
      to_port            = 8050
      protocol           = "tcp"
      cidr_blocks        = ["0.0.0.0/0"]
    }

    ingress {
        from_port          = 22
        to_port            = 22
        protocol           = "tcp"
        cidr_blocks        = ["0.0.0.0/0"]
    }
    
    egress {
        from_port        = 0
        to_port          = 0
        protocol         = "-1"
        cidr_blocks      = ["0.0.0.0/0"]
        ipv6_cidr_blocks = ["::/0"]
    }
}
resource "aws_security_group" "rds_sg" {
    name        = local.rds_sg_name
    description = "security group for rds - allows ingress from lambda-sg"
    vpc_id      = module.networking.main_vpc_id

    ingress {
        from_port        = 3306
        to_port          = 3306
        protocol         = "tcp"
        security_groups = [aws_security_group.lambda_sg.id]
    }
    
    egress {
        from_port        = 0
        to_port          = 0
        protocol         = "-1"
        cidr_blocks      = ["0.0.0.0/0"]
        ipv6_cidr_blocks = ["::/0"]
    }
}

# rds database deployed in private subnet group of network
module "podcastETLDatabase" {
    source = "./modules/rds"

    username = local.rds_username
    password = local.rds_password
    db_name = local.rds_db_name
    engine = local.rds_engine

    vpc_security_group_ids = [aws_security_group.rds_sg.id]
    db_subnet_group_name = module.networking.private_subnet_group_name

}
resource "local_file" "rdsLogin" {
 filename = "ec2_data/environment.py"
 content = <<EOT
USER_NAME = "${local.rds_username}"
PASSWORD = "${local.rds_password}"
DB_NAME  = "${local.rds_db_name}"
RDS_ENDPOINT = "${module.podcastETLDatabase.rds_db_endpoint}"
EOT
}




#___________ FIRST LAMBDA FUNCTION ___________
# - sqs trigger
# - scrapes website for RSS feeds
# - stores json containing feeds into S3 bucket

# layers
module "seleniumLayer" {
    source = "./modules/generic_layer"

    path_to_layer_source = local.path_to_selenium_layer_source
    path_to_layer_artifact = local.path_to_selenium_layer_artifact
    path_to_layer_filename = local.path_to_selenium_layer_filename
    layer_name = local.selenium_layer_name
    compatible_layer_runtimes = local.compatible_layer_runtimes
    compatible_architectures = local.compatible_architectures
}
module "chromedriverLayer" {
    source = "./modules/generic_layer"

    path_to_layer_source = local.path_to_chromedriver_layer_source
    path_to_layer_artifact = local.path_to_chromedriver_layer_artifact
    path_to_layer_filename = local.path_to_chromedriver_layer_filename 
    layer_name = local.chromedriver_layer_name

    compatible_layer_runtimes = local.compatible_layer_runtimes
    compatible_architectures = local.compatible_architectures
}
# role with s3Put policy
module "s3Put" {
    source = "./modules/iam"

    lambda_iam_policy_name = local.lambda_s3_put_policy_name
    lambda_iam_policy_path = local.lambda_s3_put_policy_path
    lambda_iam_role_name   = local.lambda_s3_put_role_name

    lambda_iam_role_path   = local.lambda_iam_role_path
}

# create SQS queue for trigger lambda function 
resource "aws_sqs_queue" "scrape_podcasts_queue" {
  name                        = "scrape-podcasts-queue.fifo"
  visibility_timeout_seconds = 300
  fifo_queue                  = true
  content_based_deduplication = false
}
# first lambda function 
module "rssScrape" {
    source="./modules/lambda"

    env_var_1 = module.rssBucket.s3_bucket_name


    lambda_iam_role_arn = module.s3Put.lambda_iam_role_arn
    path_to_source_file = local.scrape_path_to_source_file
    path_to_artifact = local.scrape_path_to_artifact

    function_name = local.scrape_function_name
    function_handler = local.scrape_function_handler


    memory_size = local.memory_size
    timeout = local.timeout
    runtime = local.runtime

    lambda_layer_arns = [module.seleniumLayer.layer_arn, module.chromedriverLayer.layer_arn]
}
# add sqs queue to trigger lambda function 
resource "aws_lambda_event_source_mapping" "scrape_podcasts_trigger" {
  event_source_arn  = aws_sqs_queue.scrape_podcasts_queue.arn
  function_name     = module.rssScrape.lambda_function_arn
  batch_size        = 1 
  enabled           = true
}




#___________ SECOND LAMBDA FUNCTION ___________
#  - grabs rss feeds
#  - collects metadata
#  - stores in RDS
#  - triggered by json put into rss bucket

# layer
module "requestsLayer" {
    source = "./modules/generic_layer"

    path_to_layer_source = local.path_to_requests_layer_source
    path_to_layer_artifact = local.path_to_requests_layer_artifact
    path_to_layer_filename = local.path_to_requests_layer_filename
    layer_name = local.requests_layer_name

    compatible_layer_runtimes = local.compatible_layer_runtimes
    compatible_architectures = local.compatible_architectures
}
module "mysqlLayer" {
    source = "./modules/generic_layer"

    path_to_layer_source = local.path_to_mysql_layer_source
    path_to_layer_artifact = local.path_to_mysql_layer_artifact
    path_to_layer_filename = local.path_to_mysql_layer_filename
    layer_name = local.mysql_layer_name

    compatible_layer_runtimes = local.compatible_layer_runtimes
    compatible_architectures = local.compatible_architectures
}
module "xmltodictLayer" {
    source = "./modules/generic_layer"

    path_to_layer_source = local.path_to_xmltodict_layer_source
    path_to_layer_artifact = local.path_to_xmltodict_layer_artifact
    path_to_layer_filename = local.path_to_xmltodict_layer_filename
    layer_name = local.xmltodict_layer_name

    compatible_layer_runtimes = local.compatible_layer_runtimes
    compatible_architectures = local.compatible_architectures
}

# role with s3Get and VPC access policies
module "s3GetAndVPC" {
    source = "./modules/iam"

    lambda_iam_policy_name = local.lambda_vpc_and_s3_get_policy_name
    lambda_iam_policy_path = local.lambda_vpc_and_s3_get_policy_path
    lambda_iam_role_name   = local.lambda_vpc_and_s3_get_role_name

    lambda_iam_role_path   = local.lambda_iam_role_path 
}

# second lambda function
module "metadataSave" {
    source="./modules/lambda"

    env_var_1 = module.rssBucket.s3_bucket_name
    env_var_2 = local.rds_username
    env_var_3 = local.rds_password
    env_var_4 = module.podcastETLDatabase.rds_db_endpoint
    env_var_5 = local.rds_db_name
    
    lambda_iam_role_arn = module.s3GetAndVPC.lambda_iam_role_arn
    path_to_source_file = local.metadata_path_to_source_file
    path_to_artifact = local.metadata_path_to_artifact

    function_name = local.metadata_function_name
    function_handler = local.metadata_function_handler

    lambda_security_group_ids = [aws_security_group.lambda_sg.id]
    lambda_subnet_ids = [module.networking.private_subnet_1_id, module.networking.private_subnet_2_id]


    memory_size = local.memory_size
    timeout = local.timeout
    runtime = local.runtime

    lambda_layer_arns = [module.requestsLayer.layer_arn, module.mysqlLayer.layer_arn, module.xmltodictLayer.layer_arn]
}

# allow rss bucket to invoke lambda function
resource "aws_lambda_permission" "s3_lambda_permission" {
  statement_id  = "AllowS3Invoke"
  action        = "lambda:InvokeFunction"
  function_name = module.metadataSave.lambda_function_arn
  principal     = "s3.amazonaws.com"
  source_arn    = module.rssBucket.s3_bucket_arn
}
# create notification when object is created
resource "aws_s3_bucket_notification" "bucket_notification" {
  bucket = module.rssBucket.s3_bucket_name
  depends_on = [module.metadataSave, aws_lambda_permission.s3_lambda_permission]

  lambda_function {
    lambda_function_arn = module.metadataSave.lambda_function_arn
    events              = ["s3:ObjectCreated:*"]
    filter_suffix       = ".json"
  }
}




#___________ THIRD LAMBDA FUNCTION ___________
#  - triggered by queue
# - downloads podcast and loads into S3 in ~10 minute chunks 

# role with s3Put and VPC access policies
module "s3PutAndVPC" {
    source = "./modules/iam"

    lambda_iam_policy_name = local.lambda_vpc_and_s3_put_policy_name
    lambda_iam_policy_path = local.lambda_vpc_and_s3_put_policy_path
    lambda_iam_role_name   = local.lambda_vpc_and_s3_put_role_name

    lambda_iam_role_path   = local.lambda_iam_role_path 
}
# create SQS queue for trigger lambda function 
resource "aws_sqs_queue" "podcast_download_queue" {
  name                        = "podcast-download-queue.fifo"
  visibility_timeout_seconds = 300
  fifo_queue                  = true
  content_based_deduplication = false
}
# third lambda function
module "DownloadPodcasts" {
    source="./modules/lambda"

    env_var_1 = module.mp3ChunksBucket.s3_bucket_name
    env_var_2 = local.rds_username
    env_var_3 = local.rds_password
    env_var_4 = module.podcastETLDatabase.rds_db_endpoint
    env_var_5 = local.rds_db_name
    
    lambda_iam_role_arn = module.s3PutAndVPC.lambda_iam_role_arn
    path_to_source_file = local.download_podcasts_path_to_source_file
    path_to_artifact = local.download_podcasts_path_to_artifact

    function_name = local.download_podcasts_function_name
    function_handler = local.download_podcasts_function_handler

    lambda_security_group_ids = [aws_security_group.lambda_sg.id]
    lambda_subnet_ids = [module.networking.private_subnet_1_id, module.networking.private_subnet_2_id]


    memory_size = local.memory_size
    timeout = local.timeout
    runtime = local.runtime

    lambda_layer_arns = [module.requestsLayer.layer_arn, module.mysqlLayer.layer_arn]
}
# add sqs queue to trigger lambda function 
resource "aws_lambda_event_source_mapping" "download_podcasts_trigger" {
  event_source_arn  = aws_sqs_queue.podcast_download_queue.arn
  function_name     = module.DownloadPodcasts.lambda_function_arn
  batch_size        = 1 
  enabled           = true
}




#___________ FOURTH LAMBDA FUNCTION ___________

# role with start_transcription_job
module "startTranscription" {
    source = "./modules/iam"

    lambda_iam_policy_name = local.lambda_start_transcription_policy_name
    lambda_iam_policy_path = local.lambda_start_transcription_policy_path
    lambda_iam_role_name   = local.lambda_start_transcription_role_name

    lambda_iam_role_path   = local.lambda_iam_role_path 
}
# lambda function 
module "TranscribePodcasts" {
    source="./modules/lambda"

    env_var_1 = module.transcriptionChunksBucket.s3_bucket_name
    
    lambda_iam_role_arn = module.startTranscription.lambda_iam_role_arn
    path_to_source_file = local.transcribe_path_to_source_file
    path_to_artifact = local.transcribe_path_to_artifact

    function_name = local.transcribe_function_name
    function_handler = local.transcribe_function_handler

    memory_size = local.memory_size
    timeout = local.timeout
    runtime = local.runtime
}

# allow mp3 bucket to invoke lambda function
resource "aws_lambda_permission" "s3_transcribe_lambda_permission" {
  statement_id  = "AllowS3Invoke"
  action        = "lambda:InvokeFunction"
  function_name = module.TranscribePodcasts.lambda_function_arn
  principal     = "s3.amazonaws.com"
  source_arn    = module.mp3ChunksBucket.s3_bucket_arn
}
# create notification when object is created
resource "aws_s3_bucket_notification" "start_transcribing_notification" {
  bucket = module.mp3ChunksBucket.s3_bucket_name
  depends_on = [module.TranscribePodcasts, aws_lambda_permission.s3_transcribe_lambda_permission]

  lambda_function {
    lambda_function_arn = module.TranscribePodcasts.lambda_function_arn
    events              = ["s3:ObjectCreated:*"]
    filter_suffix       = ".mp3"
  }
}




#___________ FIFTH LAMBDA FUNCTION ___________
#  - triggered by put into transcriptionBucket
#  - concatenates 10 minute transcriptions into single

# layer: nltk
module "nltkLayer" {
    source = "./modules/generic_layer"

    path_to_layer_source = local.path_to_nltk_layer_source
    path_to_layer_artifact = local.path_to_nltk_layer_artifact
    path_to_layer_filename = local.path_to_nltk_layer_filename
    layer_name = local.nltk_layer_name

    compatible_layer_runtimes = local.compatible_layer_runtimes
    compatible_architectures = local.compatible_architectures
}
module "regexLayer" {
    source = "./modules/generic_layer"

    path_to_layer_source = local.path_to_regex_layer_source
    path_to_layer_artifact = local.path_to_regex_layer_artifact
    path_to_layer_filename = local.path_to_regex_layer_filename
    layer_name = local.regex_layer_name

    compatible_layer_runtimes = local.compatible_layer_runtimes
    compatible_architectures = local.compatible_architectures
}


# role with s3Get and VPC access policies
module "s3GetAnds3PutAndVPC" {
    source = "./modules/iam"

    lambda_iam_policy_name = local.lambda_vpc_and_s3_get_and_s3_put_policy_name
    lambda_iam_policy_path = local.lambda_vpc_and_s3_get_and_s3_put_policy_path
    lambda_iam_role_name   = local.lambda_vpc_and_s3_get_and_s3_put_role_name

    lambda_iam_role_path   = local.lambda_iam_role_path 
}

# fifth lambda function
module "reduceTranscriptions" {
    source="./modules/lambda"

    env_var_1 = module.fullTranscriptionBucket.s3_bucket_name
    env_var_2 = local.rds_username
    env_var_3 = local.rds_password
    env_var_4 = module.podcastETLDatabase.rds_db_endpoint
    env_var_5 = local.rds_db_name
    
    lambda_iam_role_arn = module.s3GetAnds3PutAndVPC.lambda_iam_role_arn
    path_to_source_file = local.reduce_transcriptions_path_to_source_file
    path_to_artifact = local.reduce_transcriptions_path_to_artifact

    function_name = local.reduce_transcriptions_function_name
    function_handler = local.reduce_transcriptions_function_handler

    lambda_security_group_ids = [aws_security_group.lambda_sg.id]
    lambda_subnet_ids = [module.networking.private_subnet_1_id, module.networking.private_subnet_2_id]


    memory_size = local.memory_size
    timeout = local.timeout
    runtime = local.runtime

    lambda_layer_arns = [module.mysqlLayer.layer_arn, module.nltkLayer.layer_arn, module.regexLayer.layer_arn]
}

# allow transcription bucket to invoke lambda function
resource "aws_lambda_permission" "transcription_bucket_lambda_permission" {
  statement_id  = "AllowS3Invoke"
  action        = "lambda:InvokeFunction"
  function_name = module.reduceTranscriptions.lambda_function_arn
  principal     = "s3.amazonaws.com"
  source_arn    = module.transcriptionChunksBucket.s3_bucket_arn
}
# create notification when object is created
resource "aws_s3_bucket_notification" "transcription_bucket_notification" {
  bucket = module.transcriptionChunksBucket.s3_bucket_name
  depends_on = [module.reduceTranscriptions, aws_lambda_permission.transcription_bucket_lambda_permission]

  lambda_function {
    lambda_function_arn = module.reduceTranscriptions.lambda_function_arn
    events              = ["s3:ObjectCreated:*"]
    filter_suffix       = ".json"
  }
}


#___________ SIXTH LAMBDA FUNCTION ___________
#  - triggered by put into fullTranscriptionBucket
#  - starts async jobs for sentiment and entity detection



module "comprehendS3FullAcessRole" {
    source = "./modules/iam"

    lambda_iam_policy_name = local.comprehend_policy_name
    lambda_iam_policy_path = local.comprehend_policy_path
    lambda_iam_role_name   = local.comprehend_role_name

    lambda_iam_role_path   = local.comprehend_iam_role_path 
}

# role with comprehend access
module "comprehendStartAsyncRole" {
    source = "./modules/iam"

    lambda_iam_policy_name = local.lambda_start_async_policy_name
    lambda_iam_policy_path = local.lambda_start_async_policy_path
    lambda_iam_role_name   = local.lambda_start_async_role_name

    lambda_iam_role_path   = local.lambda_iam_role_path 
}

# sixth lambda function
module "startMLJobs" {
    source="./modules/lambda"

    env_var_1 = module.sentimentBucket.s3_bucket_name
    env_var_2 = module.entityBucket.s3_bucket_name
    env_var_3 = module.comprehendS3FullAcessRole.lambda_iam_role_arn
    
    lambda_iam_role_arn = module.comprehendStartAsyncRole.lambda_iam_role_arn

    path_to_source_file = local.start_async_jobs_path_to_source_file
    path_to_artifact = local.start_async_jobs_path_to_artifact

    function_name = local.start_async_jobs_function_name
    function_handler = local.start_async_jobs_function_handler


    memory_size = local.memory_size
    timeout = local.timeout
    runtime = local.runtime

    lambda_layer_arns = [module.mysqlLayer.layer_arn]
}

# allow transcription bucket to invoke lambda function
resource "aws_lambda_permission" "full_transcription_bucket_lambda_permission" {

  action        = "lambda:InvokeFunction"
  function_name = module.startMLJobs.lambda_function_arn
  principal     = "s3.amazonaws.com"
  source_arn    = module.fullTranscriptionBucket.s3_bucket_arn
}
# create notification when object is created
resource "aws_s3_bucket_notification" "full_transcription_bucket_notification" {
  bucket = module.fullTranscriptionBucket.s3_bucket_name
  depends_on   = [aws_lambda_permission.full_transcription_bucket_lambda_permission, module.startMLJobs]

  lambda_function {
    lambda_function_arn = module.startMLJobs.lambda_function_arn
    events              = ["s3:ObjectCreated:*"]
    filter_suffix       = ".txt"
  }
}








#___________ SEVENTH LAMBDA FUNCTION(s) ___________
#  - triggered by put into sentiment/entity bucket
#  - gathers ML job data and transforms-loads into RDS 

# seventh lambda function
module "TLSentiment" {
    source="./modules/lambda"

    env_var_1 = module.fullTranscriptionBucket.s3_bucket_name
    env_var_2 = local.rds_username
    env_var_3 = local.rds_password
    env_var_4 = module.podcastETLDatabase.rds_db_endpoint
    env_var_5 = local.rds_db_name
    
    lambda_iam_role_arn = module.s3GetAnds3PutAndVPC.lambda_iam_role_arn

    path_to_source_file = local.transform_load_sentiment_path_to_source_file
    path_to_artifact = local.transform_load_sentiment_path_to_artifact

    function_name = local.transform_load_sentiment_function_name
    function_handler = local.transform_load_sentiment_function_handler

    lambda_security_group_ids = [aws_security_group.lambda_sg.id]
    lambda_subnet_ids = [module.networking.private_subnet_1_id, module.networking.private_subnet_2_id]

    memory_size = local.memory_size
    timeout = local.timeout
    runtime = local.runtime

    lambda_layer_arns = [module.mysqlLayer.layer_arn]
}

# allow sentiment bucket to invoke lambda function
resource "aws_lambda_permission" "sentiment_bucket_lambda_permission" {
  statement_id  = "AllowS3Invoke"
  action        = "lambda:InvokeFunction"
  function_name = module.TLSentiment.lambda_function_arn
  principal     = "s3.amazonaws.com"
  source_arn    = module.sentimentBucket.s3_bucket_arn
}
# create notification when object is created
resource "aws_s3_bucket_notification" "sentiment_bucket_notification" {
  bucket = module.sentimentBucket.s3_bucket_name
  depends_on = [module.TLSentiment, aws_lambda_permission.sentiment_bucket_lambda_permission]

  lambda_function {
    lambda_function_arn = module.TLSentiment.lambda_function_arn
    events              = ["s3:ObjectCreated:*"]
    filter_suffix       = ".gz"
  }
}

# OTHER seventh lambda function
module "TLEntity" {
    source="./modules/lambda"

    env_var_1 = module.fullTranscriptionBucket.s3_bucket_name
    env_var_2 = local.rds_username
    env_var_3 = local.rds_password
    env_var_4 = module.podcastETLDatabase.rds_db_endpoint
    env_var_5 = local.rds_db_name
    
    lambda_iam_role_arn = module.s3GetAnds3PutAndVPC.lambda_iam_role_arn

    path_to_source_file = local.transform_load_entity_path_to_source_file
    path_to_artifact = local.transform_load_entity_path_to_artifact

    function_name = local.transform_load_entity_function_name
    function_handler = local.transform_load_entity_function_handler

    lambda_security_group_ids = [aws_security_group.lambda_sg.id]
    lambda_subnet_ids = [module.networking.private_subnet_1_id, module.networking.private_subnet_2_id]

    memory_size = local.memory_size
    timeout = local.timeout
    runtime = local.runtime

    lambda_layer_arns = [module.mysqlLayer.layer_arn]
}

# allow entity bucket to invoke lambda function
resource "aws_lambda_permission" "entity_bucket_lambda_permission" {
  statement_id  = "AllowS3Invoke"
  action        = "lambda:InvokeFunction"
  function_name = module.TLEntity.lambda_function_arn
  principal     = "s3.amazonaws.com"
  source_arn    = module.entityBucket.s3_bucket_arn
}
# create notification when object is created
resource "aws_s3_bucket_notification" "entity_bucket_notification" {
  bucket = module.entityBucket.s3_bucket_name
  depends_on = [module.TLEntity, aws_lambda_permission.entity_bucket_lambda_permission]

  lambda_function {
    lambda_function_arn = module.TLEntity.lambda_function_arn
    events              = ["s3:ObjectCreated:*"]
    filter_suffix       = ".gz"
  }
}













data "aws_ami" "ubuntu" {

    most_recent = true

    filter {
        name   = "name"
        values = ["ubuntu/images/hvm-ssd/ubuntu-focal-20.04-amd64-server-*"]
    }

    filter {
        name = "virtualization-type"
        values = ["hvm"]
    }

    owners = ["099720109477"]
}
resource "tls_private_key" "privateKey" {
  algorithm = "RSA"
  rsa_bits  = 4096
}
resource "aws_key_pair" "podcastETLDashboardKP" {
  key_name   = "podcast_etl_key"
  public_key = tls_private_key.privateKey.public_key_openssh

  provisioner "local-exec" {
    command = "echo '${tls_private_key.privateKey.private_key_pem}' > ./dashboardBastion.pem"
  }
}


resource "aws_instance" "dashboardBastionInstance" {
  depends_on = [local_file.rdsLogin]
  ami           = data.aws_ami.ubuntu.id
  instance_type = "t2.micro"
  key_name      = aws_key_pair.podcastETLDashboardKP.key_name

  vpc_security_group_ids = [aws_security_group.lambda_sg.id]
  subnet_id = module.networking.public_subnet

  associate_public_ip_address = true


  provisioner "file" {
    source      = "./ec2_data"
    destination = "/home/ubuntu"

    connection {
      type        = "ssh"
      user        = "ubuntu"
      private_key = tls_private_key.privateKey.private_key_pem
      host        = "${self.public_dns}"
    }
  }
}

resource "local_file" "ssh-exec" {
 filename = "ssh.sh"
 content = <<EOT
chmod 400 dashboardBastion.pem
ssh -i "dashboardBastion.pem" ubuntu@${aws_instance.dashboardBastionInstance.public_dns}
#DNS for dashboard viewing: ${aws_instance.dashboardBastionInstance.public_dns}:8050
EOT
}