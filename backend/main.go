package main

import (
	"context"
	"fmt"
	"log"
	"os"
	"strings"
	"time"

	"github.com/cloudwego/hertz/pkg/app/server"
	"github.com/hertz-contrib/cors"
	"github.com/jackc/pgx/v5/pgxpool"
	"github.com/maoxiongkai/screenscout-backend/cache"
	"github.com/maoxiongkai/screenscout-backend/handler"
	"github.com/maoxiongkai/screenscout-backend/middleware"
	"github.com/maoxiongkai/screenscout-backend/repo"
	"github.com/maoxiongkai/screenscout-backend/service"
)

func main() {
	// Database connection
	dbURL := os.Getenv("DATABASE_URL")
	if dbURL == "" {
		dbURL = "postgresql://postgres:postgres@localhost:5432/screenscout"
	}

	ctx := context.Background()
	config, err := pgxpool.ParseConfig(dbURL)
	if err != nil {
		log.Fatalf("Unable to parse database config: %v", err)
	}
	if config.ConnConfig.RuntimeParams == nil {
		config.ConnConfig.RuntimeParams = make(map[string]string)
	}
	config.ConnConfig.RuntimeParams["timezone"] = "Asia/Singapore"

	pool, err := pgxpool.NewWithConfig(ctx, config)
	if err != nil {
		log.Fatalf("Unable to connect to database: %v", err)
	}
	defer pool.Close()

	// Verify connection
	if err := pool.Ping(ctx); err != nil {
		log.Fatalf("Unable to ping database: %v", err)
	}
	fmt.Println("✓ Connected to PostgreSQL database")

	// Redis Cache Setup
	redisURL := os.Getenv("REDIS_URL")
	redisAddr := os.Getenv("REDIS_ADDR")
	if redisURL == "" && redisAddr == "" {
		redisAddr = "localhost:6379"
	}

	listTTL := parseDurationEnv("CACHE_MOVIE_LIST_TTL", 5*time.Minute)
	detailTTL := parseDurationEnv("CACHE_MOVIE_DETAIL_TTL", 10*time.Minute)

	redisClient := cache.NewClient(cache.Config{
		URL:     redisURL,
		Address: redisAddr,
	})
	defer redisClient.Close()

	movieCache := cache.NewMovieCache(redisClient, listTTL, detailTTL)

	// Initialize repositories
	movieRepo := repo.NewMovieRepo(pool)
	movieRepo.SetCache(movieCache)

	cinemaRepo := repo.NewCinemaRepo(pool)
	userRepo := repo.NewUserRepo(pool)
	subRepo := repo.NewSubscriptionRepo(pool)
	reviewRepo := repo.NewReviewRepo(pool)

	// Ensure tables exist
	if err := userRepo.EnsureUserTable(ctx); err != nil {
		log.Printf("Warning: ensure user table failed: %v", err)
	} else {
		fmt.Println("✓ Users table verified")
	}

	if err := subRepo.EnsureSubscriptionTables(ctx); err != nil {
		log.Printf("Warning: ensure subscription tables failed: %v", err)
	} else {
		fmt.Println("✓ Subscription tables verified")
	}

	if err := reviewRepo.EnsureReviewTable(ctx); err != nil {
		log.Printf("Warning: ensure review table failed: %v", err)
	} else {
		fmt.Println("✓ Reviews table verified")
	}

	// Initialize services & handlers
	tgService := service.NewTelegramService()
	tgService.SetRedisClient(redisClient)
	movieHandler := handler.NewMovieHandler(movieRepo)
	cinemaHandler := handler.NewCinemaHandler(cinemaRepo)
	authHandler := handler.NewAuthHandler(userRepo)
	subHandler := handler.NewSubscriptionHandler(subRepo, userRepo, tgService)
	reviewHandler := handler.NewReviewHandler(reviewRepo, movieRepo)
	adminRepo := repo.NewAdminRepo(pool, movieCache)
	adminHandler := handler.NewAdminHandler(adminRepo)

	// Create Hertz server
	h := server.Default(server.WithHostPorts(":8080"))

	// Dynamic CORS configuration allowing localhost, domain, host IP, and environment overrides
	allowedOrigins := []string{
		"http://localhost:3000",
		"http://127.0.0.1:3000",
		"https://www.screenscout.live",
		"https://screenscout.live",
		"http://www.screenscout.live",
		"http://screenscout.live",
		"http://35.240.131.203",
		"http://35.240.131.203:3000",
		"http://35.240.131.203:8080",
		"https://35.240.131.203",
	}
	if customOrigins := os.Getenv("ALLOWED_ORIGINS"); customOrigins != "" {
		for _, o := range strings.Split(customOrigins, ",") {
			if trimmed := strings.TrimSpace(o); trimmed != "" {
				allowedOrigins = append(allowedOrigins, trimmed)
			}
		}
	}
	if feURL := os.Getenv("FRONTEND_URL"); feURL != "" {
		allowedOrigins = append(allowedOrigins, strings.TrimRight(feURL, "/"))
	}
	if apiURL := os.Getenv("NEXT_PUBLIC_API_URL"); apiURL != "" {
		allowedOrigins = append(allowedOrigins, strings.TrimRight(apiURL, "/"))
	}

	h.Use(cors.New(cors.Config{
		AllowOrigins:     allowedOrigins,
		AllowMethods:     []string{"GET", "POST", "PUT", "DELETE", "OPTIONS"},
		AllowHeaders:     []string{"Origin", "Content-Type", "Accept", "Authorization"},
		ExposeHeaders:    []string{"Content-Length", "X-Cache"},
		AllowCredentials: true,
		MaxAge:           12 * time.Hour,
	}))

	// Register routes
	api := h.Group("/api")
	{
		// Movie routes
		api.GET("/movies", movieHandler.ListMovies)
		api.GET("/movies/:id", movieHandler.GetMovie)

		// Movie review routes
		api.GET("/movies/:id/reviews", reviewHandler.ListMovieReviews)
		api.POST("/movies/:id/reviews", middleware.AuthRequired(), reviewHandler.CreateMovieReview)
		api.DELETE("/movies/:id/reviews/:review_id", middleware.AuthRequired(), reviewHandler.DeleteMovieReview)

		// Cache routes
		cacheGroup := api.Group("/cache")
		{
			cacheGroup.GET("/stats", movieHandler.GetCacheStats)
			cacheGroup.POST("/movies/invalidate", movieHandler.InvalidateCache)
		}

		// Cinema routes
		api.GET("/cinemas", cinemaHandler.ListCinemas)
		api.GET("/providers", cinemaHandler.ListProviders)

		// Auth routes
		auth := api.Group("/auth")
		{
			auth.POST("/register", authHandler.Register)
			auth.POST("/login", authHandler.Login)
			auth.GET("/me", middleware.AuthRequired(), authHandler.Me)
		}

		// Admin routes (Restricted to admin role)
		adminGroup := api.Group("/admin", middleware.AuthRequired(), middleware.AdminRequired())
		{
			adminGroup.GET("/stats", adminHandler.GetAdminStats)
			adminGroup.POST("/scrape", adminHandler.TriggerScrape)
		}

		// User notification settings
		userGroup := api.Group("/user", middleware.AuthRequired())
		{
			userGroup.GET("/notification-channel", subHandler.GetNotificationChannel)
			userGroup.POST("/notification-channel", subHandler.UpdateNotificationChannel)
		}

		// Subscription routes
		subGroup := api.Group("/subscriptions")
		{
			subGroup.GET("", middleware.AuthRequired(), subHandler.ListSubscriptions)
			subGroup.POST("", middleware.AuthRequired(), subHandler.CreateSubscription)
			subGroup.DELETE("/:id", middleware.AuthRequired(), subHandler.DeleteSubscription)
			subGroup.POST("/:id/toggle", middleware.AuthRequired(), subHandler.ToggleSubscription)
			subGroup.POST("/check", subHandler.CheckSubscriptions)
		}
	}

	fmt.Println("🚀 ScreenScout API server starting on :8080")
	h.Spin()
}

func parseDurationEnv(key string, defaultVal time.Duration) time.Duration {
	v := os.Getenv(key)
	if v == "" {
		return defaultVal
	}
	d, err := time.ParseDuration(v)
	if err != nil {
		log.Printf("⚠️ Invalid duration for %s=%q: %v. Using default %v", key, v, err, defaultVal)
		return defaultVal
	}
	return d
}
