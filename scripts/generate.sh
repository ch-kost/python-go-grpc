#!/bin/sh
set -eu
cd "$(dirname "$0")/.."
mkdir -p client/api server/api
python -m grpc_tools.protoc -I proto --python_out=client/api --grpc_python_out=client/api proto/api.proto
sed -i 's/^import api_pb2 as/from . import api_pb2 as/' client/api/api_pb2_grpc.py
protoc -I proto --go_out=. --go_opt=module=python_go_grpc --go-grpc_out=. --go-grpc_opt=module=python_go_grpc proto/api.proto
go mod tidy
gofmt -w server
