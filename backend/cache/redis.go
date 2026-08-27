package cache

import (
	"context"
	"errors"
	"fmt"
	"log"
	"net/url"
	"strings"
	"sync/atomic"
	"time"

	"github.com/redis/go-redis/v9"
)

// ErrCacheMiss is returned when a requested key is not present in cache.
var ErrCacheMiss = errors.New("cache: key not found")

// Config contains Redis connection and behavior settings.
type Config struct {
	// Address is the host:port string (e.g. "localhost:6379").
	Address string
	// URL can be provided instead of Address (e.g. "redis://:password@localhost:6379/0").
	URL string
	// Password for Redis authentication.
	Password string
	// DB is the Redis database index (default 0).
	DB int
	// PoolSize is the max socket connections.
	PoolSize int
	// ConnectTimeout for dial attempts.
	ConnectTimeout time.Duration
	// ReadTimeout for socket reads.
	ReadTimeout time.Duration
	// WriteTimeout for socket writes.
	WriteTimeout time.Duration
}

// Stats holds performance and observability metrics for the cache layer.
type Stats struct {
	Connected     bool    `json:"connected"`
	Hits          int64   `json:"hits"`
	Misses        int64   `json:"misses"`
	Sets          int64   `json:"sets"`
	Errors        int64   `json:"errors"`
	Invalidations int64   `json:"invalidations"`
	HitRate       float64 `json:"hit_rate"`
}

// Client is a resilient wrapper around the Redis client.
type Client struct {
	rdb           *redis.Client
	available     atomic.Bool
	hits          atomic.Int64
	misses        atomic.Int64
	sets          atomic.Int64
	errs          atomic.Int64
	invalidations atomic.Int64
}

// NewClient initializes a new Redis client. If Redis is unreachable, it logs a warning
// and marks the client as unavailable, allowing the system to degrade gracefully.
func NewClient(cfg Config) *Client {
	var opts *redis.Options

	if cfg.URL != "" {
		parsed, err := redis.ParseURL(cfg.URL)
		if err != nil {
			log.Printf("⚠️ Redis: failed to parse REDIS_URL %q: %v. Using fallback config.", cfg.URL, err)
			opts = defaultRedisOptions(cfg)
		} else {
			opts = parsed
		}
	} else {
		opts = defaultRedisOptions(cfg)
	}

	rdb := redis.NewClient(opts)
	c := &Client{rdb: rdb}

	// Test connection with a short timeout
	ctx, cancel := context.WithTimeout(context.Background(), 2*time.Second)
	defer cancel()

	if err := rdb.Ping(ctx).Err(); err != nil {
		c.available.Store(false)
		log.Printf("⚠️ Redis: initial connection failed (%v). Operating in graceful degraded mode (cache bypass).", err)
	} else {
		c.available.Store(true)
		log.Printf("✓ Connected to Redis at %s", opts.Addr)
	}

	return c
}

// NewFromUniversalClient creates a Client wrapping any existing redis.UniversalClient (useful for testing/miniredis).
func NewFromUniversalClient(rdb *redis.Client) *Client {
	c := &Client{rdb: rdb}
	c.available.Store(true)
	return c
}

func defaultRedisOptions(cfg Config) *redis.Options {
	addr := cfg.Address
	if addr == "" {
		addr = "localhost:6379"
	}
	// Strip redis:// prefix if present in Address
	if strings.HasPrefix(addr, "redis://") {
		if u, err := url.Parse(addr); err == nil {
			addr = u.Host
		}
	}

	poolSize := cfg.PoolSize
	if poolSize <= 0 {
		poolSize = 20
	}

	connectTimeout := cfg.ConnectTimeout
	if connectTimeout <= 0 {
		connectTimeout = 3 * time.Second
	}

	readTimeout := cfg.ReadTimeout
	if readTimeout <= 0 {
		readTimeout = 2 * time.Second
	}

	writeTimeout := cfg.WriteTimeout
	if writeTimeout <= 0 {
		writeTimeout = 2 * time.Second
	}

	return &redis.Options{
		Addr:         addr,
		Password:     cfg.Password,
		DB:           cfg.DB,
		PoolSize:     poolSize,
		DialTimeout:  connectTimeout,
		ReadTimeout:  readTimeout,
		WriteTimeout: writeTimeout,
	}
}

// IsAvailable returns true if the client is connected and active.
func (c *Client) IsAvailable() bool {
	if c == nil || c.rdb == nil {
		return false
	}
	return c.available.Load()
}

// Ping checks Redis connectivity and updates available status.
func (c *Client) Ping(ctx context.Context) error {
	if c == nil || c.rdb == nil {
		return errors.New("redis client not initialized")
	}
	err := c.rdb.Ping(ctx).Err()
	if err != nil {
		c.available.Store(false)
		c.errs.Add(1)
		return err
	}
	c.available.Store(true)
	return nil
}

// Get retrieves a string key from Redis.
func (c *Client) Get(ctx context.Context, key string) (string, error) {
	if !c.IsAvailable() {
		return "", ErrCacheMiss
	}

	val, err := c.rdb.Get(ctx, key).Result()
	if err != nil {
		if errors.Is(err, redis.Nil) {
			c.misses.Add(1)
			return "", ErrCacheMiss
		}
		c.errs.Add(1)
		// On network failure, temporarily mark unavailable
		if isNetErr(err) {
			c.available.Store(false)
		}
		return "", fmt.Errorf("redis get error: %w", err)
	}

	c.hits.Add(1)
	return val, nil
}

// Set stores a key-value pair with an expiration TTL.
func (c *Client) Set(ctx context.Context, key string, value interface{}, ttl time.Duration) error {
	if !c.IsAvailable() {
		return nil // silently ignore when unavailable
	}

	err := c.rdb.Set(ctx, key, value, ttl).Err()
	if err != nil {
		c.errs.Add(1)
		if isNetErr(err) {
			c.available.Store(false)
		}
		return fmt.Errorf("redis set error: %w", err)
	}

	c.sets.Add(1)
	return nil
}

// Del deletes one or more keys.
func (c *Client) Del(ctx context.Context, keys ...string) error {
	if !c.IsAvailable() || len(keys) == 0 {
		return nil
	}

	err := c.rdb.Del(ctx, keys...).Err()
	if err != nil {
		c.errs.Add(1)
		return fmt.Errorf("redis del error: %w", err)
	}

	c.invalidations.Add(int64(len(keys)))
	return nil
}

// FlushPrefix finds and removes all keys matching a prefix pattern (e.g. "screenscout:movie:*").
func (c *Client) FlushPrefix(ctx context.Context, prefixPattern string) (int64, error) {
	if !c.IsAvailable() {
		return 0, nil
	}

	var cursor uint64
	var deletedCount int64

	for {
		keys, nextCursor, err := c.rdb.Scan(ctx, cursor, prefixPattern, 100).Result()
		if err != nil {
			c.errs.Add(1)
			return deletedCount, fmt.Errorf("redis scan error: %w", err)
		}

		if len(keys) > 0 {
			if err := c.rdb.Del(ctx, keys...).Err(); err != nil {
				c.errs.Add(1)
				return deletedCount, fmt.Errorf("redis del error: %w", err)
			}
			deletedCount += int64(len(keys))
			c.invalidations.Add(int64(len(keys)))
		}

		cursor = nextCursor
		if cursor == 0 {
			break
		}
	}

	return deletedCount, nil
}

// Stats returns performance metrics for the cache instance.
func (c *Client) Stats() Stats {
	if c == nil {
		return Stats{Connected: false}
	}

	hits := c.hits.Load()
	misses := c.misses.Load()
	total := hits + misses

	var hitRate float64
	if total > 0 {
		hitRate = float64(hits) / float64(total)
	}

	return Stats{
		Connected:     c.IsAvailable(),
		Hits:          hits,
		Misses:        misses,
		Sets:          c.sets.Load(),
		Errors:        c.errs.Load(),
		Invalidations: c.invalidations.Load(),
		HitRate:       hitRate,
	}
}

// Redis returns the underlying raw *redis.Client.
func (c *Client) Redis() *redis.Client {
	if c == nil {
		return nil
	}
	return c.rdb
}

// XAdd appends an event message to a Redis stream.
func (c *Client) XAdd(ctx context.Context, args *redis.XAddArgs) (string, error) {
	if !c.IsAvailable() {
		return "", errors.New("redis is not available")
	}
	id, err := c.rdb.XAdd(ctx, args).Result()
	if err != nil {
		c.errs.Add(1)
		if isNetErr(err) {
			c.available.Store(false)
		}
		return "", err
	}
	return id, nil
}

// Close closes the underlying Redis connection pool.
func (c *Client) Close() error {
	if c != nil && c.rdb != nil {
		return c.rdb.Close()
	}
	return nil
}

func isNetErr(err error) bool {
	if err == nil {
		return false
	}
	msg := err.Error()
	return strings.Contains(msg, "connection refused") ||
		strings.Contains(msg, "i/o timeout") ||
		strings.Contains(msg, "broken pipe") ||
		strings.Contains(msg, "EOF")
}
