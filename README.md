# CodeServer-PythonReverseProxy

Switch to aiohttp Resources:

- https://stackoverflow.com/questions/52382999/how-to-implement-a-websocket-aware-reverse-proxy-with-aiohttp-python-3-6
- https://docs.aiohttp.org/en/stable/web_quickstart.html

oauth resources:

- https://github.com/klen/aioauth-client
- https://realpython.com/flask-google-login/
- https://docs.aiohttp.org/en/stable/web_quickstart.html
- https://docs.github.com/en/free-pro-team@latest/developers/apps/authorizing-oauth-apps

ssl resources:

- https://letsencrypt.org/docs/certificates-for-localhost/

Create a local cert:

`mkdir src/localcert && openssl req -x509 -out src/localcert/localhost.crt -keyout src/localcert/localhost.key -newkey rsa:2048 -nodes -sha256 -subj '/CN=localhost' -extensions EXT -config <( printf "[dn]\nCN=localhost\n[req]\ndistinguished_name = dn\n[EXT]\nsubjectAltName=DNS:localhost\nkeyUsage=digitalSignature\nextendedKeyUsage=serverAuth")`

## Current start steps

1. Get a server
1. git clone this project
1. Create a group called `coderg` with the gid 1024
1. Create a user called `coder` with the uid 1000 with group `coderg`
1. Install SSL certs or run certbot for free LetsEncrypt SSL
1. Add/edit your `src/.env` file
1. npm run build:codeserverdocker
  - This builds the customized code-server image
1. npm start