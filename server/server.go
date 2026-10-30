package main

import (
	"context"
	"crypto/tls"
	"crypto/x509"
	"log"
	"net"
	"os"
	"os/signal"
	"path/filepath"
	"syscall"
	"time"

	"google.golang.org/grpc"
	"google.golang.org/grpc/credentials"
	"google.golang.org/grpc/metadata"
	"google.golang.org/grpc/peer"
	"google.golang.org/grpc/status"
	"python_go_grpc/server/api"
)

func loggingInterceptor(ctx context.Context, req interface{}, info *grpc.UnaryServerInfo, handler grpc.UnaryHandler) (interface{}, error) {
	started := time.Now()
	response, err := handler(ctx, req)
	remote := "unknown"
	if p, ok := peer.FromContext(ctx); ok {
		remote = p.Addr.String()
	}
	md, _ := metadata.FromIncomingContext(ctx)
	log.Printf("peer=%q method=%q status=%s duration=%s user-agent=%q", remote, info.FullMethod, status.Code(err), time.Since(started), md.Get("user-agent"))
	return response, err
}

func main() {
	dir := os.Getenv("CERTS_DIR")
	if dir == "" {
		dir = "certs"
	}
	pair, err := tls.LoadX509KeyPair(filepath.Join(dir, "server.pem"), filepath.Join(dir, "server-key.pem"))
	if err != nil {
		log.Fatal(err)
	}
	ca, err := os.ReadFile(filepath.Join(dir, "ca.pem"))
	if err != nil {
		log.Fatal(err)
	}
	pool := x509.NewCertPool()
	if !pool.AppendCertsFromPEM(ca) {
		log.Fatal("cannot parse CA certificate")
	}
	tlsConfig := &tls.Config{Certificates: []tls.Certificate{pair}, ClientCAs: pool, ClientAuth: tls.RequireAndVerifyClientCert, MinVersion: tls.VersionTLS12}
	secure := grpc.NewServer(grpc.Creds(credentials.NewTLS(tlsConfig)), grpc.UnaryInterceptor(loggingInterceptor))
	plain := grpc.NewServer(grpc.UnaryInterceptor(loggingInterceptor))
	api.RegisterDiceServiceServer(secure, api.NewServer())
	api.RegisterDiceServiceServer(plain, api.NewServer())
	failed := make(chan error, 2)
	for addr, srv := range map[string]*grpc.Server{"127.0.0.1:8443": secure, "127.0.0.1:50051": plain} {
		listener, err := net.Listen("tcp", addr)
		if err != nil {
			log.Fatal(err)
		}
		log.Printf("Starting gRPC server address=%q mtls=%t", addr, srv == secure)
		go func(s *grpc.Server, l net.Listener) { failed <- s.Serve(l) }(srv, listener)
	}
	stopped := make(chan os.Signal, 1)
	signal.Notify(stopped, syscall.SIGINT, syscall.SIGTERM)
	select {
	case sig := <-stopped:
		log.Printf("received signal=%s", sig)
	case err := <-failed:
		log.Printf("server stopped: %v", err)
	}
	secure.GracefulStop()
	plain.GracefulStop()
}
