package api

import (
	"context"
	"sync"
	"testing"
)

func TestRollDieConcurrent(t *testing.T) {
	s := NewServer()
	var wg sync.WaitGroup
	for n := 0; n < 32; n++ {
		wg.Add(1)
		go func() {
			defer wg.Done()
			for i := 0; i < 100; i++ {
				result, err := s.RollDie(context.Background(), &RollDieRequest{})
				if err != nil || result.Value < 1 || result.Value > Dots {
					t.Errorf("invalid result: %v %v", result, err)
				}
			}
		}()
	}
	wg.Wait()
}
