package cache

import (
	"context"
	"testing"
	"time"

	"github.com/alicebob/miniredis/v2"
	"github.com/redis/go-redis/v9"
)

func TestRedisClient_Operations(t *testing.T) {
	mr, err := miniredis.Run()
	if err != nil {
		t.Fatalf("failed to start miniredis: %v", err)
	}
	defer mr.Close()

	rdb := redis.NewClient(&redis.Options{
		Addr: mr.Addr(),
	})
	client := NewFromUniversalClient(rdb)

	ctx := context.Background()

	// 1. Set & Get
	err = client.Set(ctx, "test:key:1", "value1", 1*time.Minute)
	if err != nil {
		t.Fatalf("unexpected set error: %v", err)
	}

	val, err := client.Get(ctx, "test:key:1")
	if err != nil || val != "value1" {
		t.Fatalf("expected 'value1', got val=%q, err=%v", val, err)
	}

	// 2. Miss
	_, err = client.Get(ctx, "test:nonexistent")
	if err != ErrCacheMiss {
		t.Fatalf("expected ErrCacheMiss, got %v", err)
	}

	// 3. Del
	err = client.Del(ctx, "test:key:1")
	if err != nil {
		t.Fatalf("unexpected del error: %v", err)
	}

	_, err = client.Get(ctx, "test:key:1")
	if err != ErrCacheMiss {
		t.Fatalf("expected ErrCacheMiss after del, got %v", err)
	}

	// 4. FlushPrefix
	_ = client.Set(ctx, "test:flush:1", "a", 1*time.Minute)
	_ = client.Set(ctx, "test:flush:2", "b", 1*time.Minute)
	_ = client.Set(ctx, "other:key:1", "c", 1*time.Minute)

	deleted, err := client.FlushPrefix(ctx, "test:flush:*")
	if err != nil {
		t.Fatalf("unexpected flush error: %v", err)
	}
	if deleted != 2 {
		t.Fatalf("expected 2 keys deleted, got %d", deleted)
	}

	val, err = client.Get(ctx, "other:key:1")
	if err != nil || val != "c" {
		t.Fatalf("expected other key to remain intact, got val=%q, err=%v", val, err)
	}

	// 5. Ping
	if err := client.Ping(ctx); err != nil {
		t.Fatalf("ping failed: %v", err)
	}
}

func TestRedisClient_Config(t *testing.T) {
	// Test default fallback options
	cfg := Config{
		Address: "localhost:6379",
	}
	opts := defaultRedisOptions(cfg)
	if opts.Addr != "localhost:6379" {
		t.Errorf("expected localhost:6379, got %s", opts.Addr)
	}
	if opts.PoolSize != 20 {
		t.Errorf("expected poolSize 20, got %d", opts.PoolSize)
	}

	// Test redis:// prefix stripping in Address
	cfgURL := Config{
		Address: "redis://127.0.0.1:6380",
	}
	optsURL := defaultRedisOptions(cfgURL)
	if optsURL.Addr != "127.0.0.1:6380" {
		t.Errorf("expected 127.0.0.1:6380, got %s", optsURL.Addr)
	}
}
