locals {

    /*===========NAMES AND SENSITIVE VARIABLES FOR YOU TO CONFIGURE==========*/
    # bucket names 
    rss_bucket_name = "podcast-etl-rss-feeds-bucket"
    mp3_chunks_bucket_name = "podcast-etl-mp3-chunks-bucket"
    transcription_chunks_bucket_name = "podcast-etl-transcription-chunks-bucket"
    full_transcription_bucket_name = "podcast-etl-full-transcriptions-bucket"
    sentiment_bucket_name = "podcast-etl-sentiment-output-bucket"
    entity_bucket_name = "podcast-etl-entity-output-bucket"

    # rds login info
    rds_username = "wilson"
    rds_password = "1thisisnotmyrealpassword2dontworry3"
    rds_db_name = "PodcastETLDB"
    rds_engine = "mysql" #this is grouped with rds, but shouldn't be configured

    /*===============IAM POLICIES AND ROLES INFO===============*/
    lambda_s3_put_policy_name = "lambda_s3_put_policy"
    lambda_s3_put_policy_path = "./modules/iam/lambda-s3-put-policy.json"
    lambda_s3_put_role_name = "lambda_scraper_role"

    lambda_vpc_and_s3_get_policy_name = "lambda_vpc_and_s3_get_policy"
    lambda_vpc_and_s3_get_policy_path = "./modules/iam/lambda-vpc-and-s3-get-policy.json"
    lambda_vpc_and_s3_get_role_name = "lambda_metadata_role"

    lambda_vpc_and_s3_put_policy_name = "lambda_vpc_and_s3_put_policy"
    lambda_vpc_and_s3_put_policy_path = "./modules/iam/lambda-vpc-and-s3-put-policy.json"
    lambda_vpc_and_s3_put_role_name = "lambda_download_podcasts_role"

    lambda_start_transcription_policy_name = "lambda_start_transcription_policy"
    lambda_start_transcription_policy_path = "./modules/iam/lambda-start-transcription-policy.json"
    lambda_start_transcription_role_name = "lambda_start_transcription_role"

    lambda_vpc_and_s3_get_and_s3_put_policy_name = "lambda_vpc_and_s3_get_and_s3_put_policy"
    lambda_vpc_and_s3_get_and_s3_put_policy_path = "./modules/iam/lambda-vpc-s3-get-s3-put-policy.json"
    lambda_vpc_and_s3_get_and_s3_put_role_name = "lambda_concatenate_transcriptions_role"

    lambda_start_async_policy_name = "lambda_start_async_policy"
    lambda_start_async_policy_path = "./modules/iam/lambda-start-async-jobs-policy.json"
    lambda_start_async_role_name = "lambda_start_async_jobs_role"

    lambda_iam_role_path = "./modules/iam/lambda-assume-role-policy.json"


    comprehend_policy_name = "comprehend_s3_full_access_policy"
    comprehend_policy_path = "./modules/iam/comprehend-s3-full-access-policy.json"
    comprehend_role_name = "comprehend_start_async_jobs"

    comprehend_iam_role_path = "./modules/iam/comprehend-assume-role-policy.json" 

    /*================LAMBDA LAYERS INFO===================*/

    # layers for first lambda function
    path_to_selenium_layer_source = "./layers/selenium"
    path_to_selenium_layer_artifact = "./artifacts/selenium.zip"
    path_to_selenium_layer_filename = "./artifacts/selenium.zip"
    selenium_layer_name = "selenium"

    path_to_chromedriver_layer_source = "./layers/chromedriver"
    path_to_chromedriver_layer_artifact = "./artifacts/chromedriver.zip"
    path_to_chromedriver_layer_filename = "./artifacts/chromedriver.zip"
    chromedriver_layer_name = "chromedriver"

    # layer for second (ONLY) lambda function
    path_to_xmltodict_layer_source = "./layers/xmltodict"
    path_to_xmltodict_layer_artifact = "./artifacts/xmltodict.zip"
    path_to_xmltodict_layer_filename = "./artifacts/xmltodict.zip"
    xmltodict_layer_name = "xmltodict"

    # layers for second & third lambda functions
    path_to_requests_layer_source = "./layers/requests"
    path_to_requests_layer_artifact = "./artifacts/requests.zip"
    path_to_requests_layer_filename = "./artifacts/requests.zip"
    requests_layer_name = "requests"

    path_to_mysql_layer_source = "./layers/mysql"
    path_to_mysql_layer_artifact = "./artifacts/mysql.zip"
    path_to_mysql_layer_filename = "./artifacts/mysql.zip"
    mysql_layer_name = "mysql"

    # layer for fifth lambda function
    path_to_nltk_layer_source = "./layers/nltk"
    path_to_nltk_layer_artifact = "./artifacts/nltk.zip"
    path_to_nltk_layer_filename = "./artifacts/nltk.zip"
    nltk_layer_name = "nltk"

    path_to_regex_layer_source = "./layers/regex"
    path_to_regex_layer_artifact = "./artifacts/regex.zip"
    path_to_regex_layer_filename = "./artifacts/regex.zip"
    regex_layer_name = "regex"



    # layer metadata
    compatible_layer_runtimes = ["python3.7"]
    compatible_architectures = ["x86_64"]

    /*============LAMBDA FUNCTION INFO============*/
    # first lambda function
    scrape_path_to_source_file = "./src/lambda_1.py"
    scrape_path_to_artifact = "./artifacts/lambda_1.zip"
    scrape_function_name = "scrape-rss-feeds"
    scrape_function_handler = "lambda_1.get_rss_feeds"

    # second lambda function
    metadata_path_to_source_file = "./src/lambda_2.py"
    metadata_path_to_artifact = "./artifacts/lambda_2.zip"
    metadata_function_name = "store-metadata"
    metadata_function_handler = "lambda_2.save_metadata"

    # third lambda function 
    download_podcasts_path_to_source_file = "./src/lambda_3.py"
    download_podcasts_path_to_artifact = "./artifacts/lambda_3.zip"
    download_podcasts_function_name = "download-podcasts"
    download_podcasts_function_handler = "lambda_3.download"

    # fourth lambda function
    transcribe_path_to_source_file = "./src/lambda_4.py"
    transcribe_path_to_artifact = "./artifacts/lambda_4.zip"
    transcribe_function_name = "transcribe-podcasts"
    transcribe_function_handler = "lambda_4.transcribe_podcast"

    # fifth lambda function
    reduce_transcriptions_path_to_source_file = "./src/lambda_5.py"
    reduce_transcriptions_path_to_artifact = "./artifacts/lambda_5.zip"
    reduce_transcriptions_function_name = "reduce-transcriptions"
    reduce_transcriptions_function_handler = "lambda_5.reduce"


    # sixth lambda function
    start_async_jobs_path_to_source_file = "./src/lambda_6.py"
    start_async_jobs_path_to_artifact = "./artifacts/lambda_6.zip"
    start_async_jobs_function_name = "start-async-jobs"
    start_async_jobs_function_handler = "lambda_6.start_async_detection"

    # seventh lambda function(s)
    transform_load_sentiment_path_to_source_file = "./src/lambda_71.py"
    transform_load_sentiment_path_to_artifact = "./artifacts/lambda_71.zip"
    transform_load_sentiment_function_name = "transform-load-sentiment-output"
    transform_load_sentiment_function_handler = "lambda_71.lambda_handler"

    transform_load_entity_path_to_source_file = "./src/lambda_72.py"
    transform_load_entity_path_to_artifact = "./artifacts/lambda_72.zip"
    transform_load_entity_function_name = "transform-load-entity-output"
    transform_load_entity_function_handler = "lambda_72.lambda_handler"

    # lambda config(s) 
    memory_size = 512
    timeout = 300
    runtime = "python3.7"

    /*===============SECURITY GROUP INFO ================*/
    lambda_sg_name = "lambdaSecurityGroup"
    rds_sg_name = "rdsSecurityGroup"

}