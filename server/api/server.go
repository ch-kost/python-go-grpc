package api

import (
	"context"
	"math/rand"
)

const Dots = 6

type Server struct{ UnimplementedDiceServiceServer }

func NewServer() *Server { return &Server{} }

func (s *Server) RollDie(ctx context.Context, req *RollDieRequest) (*RollDieResponse, error) {
	// The package-level generator is safe for concurrent RPC handlers.
	return &RollDieResponse{Value: int32(rand.Intn(Dots) + 1)}, nil
}
