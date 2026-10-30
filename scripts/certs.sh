#!/bin/sh
set -eu
cd "$(dirname "$0")/../certs"
umask 077
cfssl gencert -initca ca-csr.json | cfssljson -bare ca -
cfssl gencert -ca=ca.pem -ca-key=ca-key.pem -config=ca-config.json -profile=server server-csr.json | cfssljson -bare server
cfssl gencert -ca=ca.pem -ca-key=ca-key.pem -config=ca-config.json -profile=client client-csr.json | cfssljson -bare client
openssl req -x509 -newkey rsa:2048 -nodes -keyout rogue-key.pem -out rogue.pem -days 1 -subj '/CN=untrusted-client' >/dev/null 2>&1
