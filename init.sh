mkdir layers

# use python3.7 environment for installing packages
virtualenv -p python3.7 local_layers # if you like venv, knock yourself out :)
source local_layers/bin/activate

# create selenium layer --> for lambda function 1, runtime 3.7
pip install selenium==3.8.0 -t layers/selenium/python/lib/python3.7/site-packages

# create chromdriver layer --> for lambda function 1, runtime 3.7
mkdir layers/chromedriver

curl -SL https://chromedriver.storage.googleapis.com/2.37/chromedriver_linux64.zip \
> chromedriver.zip

curl -SL https://github.com/adieuadieu/serverless-chrome/releases/download/v1.0.0-41/stable-headless-curl \
-SL https://github.com/adieuadieu/serverless-chrome/releases/download/v1.0.0-41/stable-headless-chromium-amazonlinux-2017-03.zip \
> headless-chromium.zip

unzip headless-chromium.zip -d layers/chromedriver
unzip chromedriver.zip -d layers/chromedriver
rm headless-chromium.zip chromedriver.zip


# create xmltodict layer --> for lambda function 2, runtime 3.7
pip install xmltodict -t layers/xmltodict/python/lib/python3.7/site-packages 

# create requests layer --> for lambda functions 2,3, runtime python3.7
pip install requests==2.25.1 -t layers/requests/python/lib/python3.7/site-packages 

# create mysql layer --> for lambda function 2,3 runtime python3.7
pip install mysql-connector-python==8.0.25 -t layers/mysql/python/lib/python3.7/site-packages

# create nltk layer 
pip install nltk==3.6.3 -t layers/nltk/python/lib/python3.7/site-packages
pip install regex -t layers/regex/python/lib/python3.7/site-packages

# lambda function 1 <--- [selenium, chromedriver]
# lambda function 2 <--- [requests, mysql, xmltdict]
# lambda function 3 <--- [requests, mysql, pydub]

mkdir artifacts
