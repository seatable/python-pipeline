# Functions run on OpenFaas

## Directory description
For example
```
.
├── faas-functions
│   ├── merge-pdfs
│   │   ├── handler.py
│   │   └── requirements.txt
│   ├── merge-pdfs.yml
│   └── template
│       └── common-flask
│           ├── Dockerfile
│           ├── function
│           │   ├── handler.py
│           │   └── requirements.txt
│           ├── index.py
│           ├── requirements.txt
│           └── template.yml
└── readme.md
```
Functions and templates are stored in directory faas-functions.

Above faas-functions subtree shows that there are a function named merge-pdfs and a template repository, directory template, in which template common-flask is.

Merge-pdf is defined in merge-pdfs.yml and it's code is in directory merge-pdfs.


## Merge-pdfs description
A function which is created by template common-flask, `faas-cli new merge-pdfs --lang=common-flask` is to merge several pdfs stored in base into a large pdf. Invocation like this
```
curl --request POST 'SERVICE_URL/function/merge-pdfs' \
--header 'Authorization: Token ef5bef00efe9d81d9341fa1afddcc2dbf9fb0b28' \
--header 'Content-Type: application/json' \
--data-raw '{
	"dtable_uuid": "00390415b6dc416a8f2a70a3a1356a18",  // temp-api-token need post dtable_uuid
	"username": "xiongchao.cheng@seafile.com",          // temp-api-token need post dtable_uuid
	"files": ["files/2020-08/011001900611-81790489.pdf", "files/2020-08/013001920011-83356621.pdf"]
}'
```


## Deploy merge-pdfs
After deploying openfaas and installing faas-cli, cd into path faas-function, you can run `faas-cli build -f merge-pdfs.yml` to build merge-pdfs and run `faas-cli deploy -f merge-pdfs.yml` function.
Please note that there is an environment variable named `DTABLE_WEB_SERVICE_URL` need to be set in merge-pdfs.yml, or the function will not work.


## Run-python function
run-python function is to download python script file and run it.
```
curl --request POST 'SERVICE_URL/function/run-python'
--data-raw '{
	"script_url": "https://dev.seafile.com/seafhttp/files/6796540e-4633-40eb-999c-29c2a94595ae/append_row.py",  # script file download-url
	"env": {
		"dtable_web_url": "",  # dtable-web service URL
		"api_token": ""  # api-token / temp-api-token of dtable
	}
}'
```
