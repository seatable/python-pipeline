# Functions run on OpenFaas

## Directory description
For example
```
.
├── merge-pdfs
│   ├── handler.py
│   └── requirements.txt
├── merge-pdfs.yml
├── readme.md
└── template
    └── common-flask
        ├── Dockerfile
        ├── function
        │   ├── handler.py
        │   └── requirements.txt
        ├── index.py
        ├── requirements.txt
        └── template.yml
```

Templates are stored in directory template.

Above tree shows that there are a function named merge-pdfs and a template repository, directory template, in which template common-flask is.

Merge-pdf is defined in merge-pdfs.yml and it's code is in directory merge-pdfs.


## Merge-pdfs description
A function which is created by template common-flask, `faas-cli new merge-pdfs --lang=common-flask` is to merge several pdfs stored in base into a large pdf. Invocation like this
```
curl --request POST 'SERVICE_URL/function/merge-pdfs' \
--header 'Content-Type: application/json' \
--data-raw '{
	"api_token": "ef5bef00efe9d81d9341fa1afddcc2dbf9fb0b28",
	"dtable_uuid": "00390415b6dc416a8f2a70a3a1356a18",
	"username": "xiongchao.cheng@seafile.com",
	"files": ["files/2020-08/011001900611-81790489.pdf", "files/2020-08/013001920011-83356621.pdf"]
}'
```


## Deploy merge-pdfs
After deploying openfaas and installing faas-cli, you can run `faas-cli deploy -f merge-pdf.yml` to deploy merge-pdfs function.
Please note that there is an environment variable named `DTABLE_WEB_SERVICE_URL` need to be set in merge-pdfs.yml, or the function will not work.
