FROM ubuntu:24.04
ENV DEBIAN_FRONTEND=noninteractive PATH=/opt/venv/bin:/root/go/bin:$PATH
RUN apt-get update && apt-get install -y --no-install-recommends python3 python3-venv golang-go gcc libc6-dev protobuf-compiler nginx golang-cfssl ca-certificates curl openssl procps && rm -rf /var/lib/apt/lists/*
WORKDIR /workspace
COPY requirements.txt ./
RUN python3 -m venv /opt/venv && python -m pip install --no-cache-dir -r requirements.txt
COPY go.mod ./
RUN go mod download && go install google.golang.org/protobuf/cmd/protoc-gen-go@v1.36.5 && go install google.golang.org/grpc/cmd/protoc-gen-go-grpc@v1.5.1
COPY . .
RUN sh scripts/generate.sh && go test -race ./... && mkdir -p bin && go build -o bin/dice-server ./server && python manage.py check && python manage.py test client
EXPOSE 8000 8001
CMD ["sh", "scripts/start.sh"]
