package main

import (
	"context"
	"fmt"
	"log"
	"os"
	"time"

	"github.com/cloudwego/hertz/pkg/app/server"
	"github.com/hertz-contrib/cors"
	"github.com/jackc/pgx/v5/pgxpool"
	"github.com/maoxiongkai/screenscout-backend/handler"
	"github.com/maoxiongkai/screenscout-backend/middleware"
	"github.com/maoxiongkai/screenscout-backend/repo"
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

	// Initialize repositories
	movieRepo := repo.NewMovieRepo(pool)
	cinemaRepo := repo.NewCinemaRepo(pool)
	userRepo := repo.NewUserRepo(pool)

	// Ensure users table exists
	if err := userRepo.EnsureUserTable(ctx); err != nil {
		log.Printf("Warning: ensure user table failed: %v", err)
	} else {
		fmt.Println("✓ Users table verified")
	}

	// Initialize handlers
	movieHandler := handler.NewMovieHandler(movieRepo)
	cinemaHandler := handler.NewCinemaHandler(cinemaRepo)
	authHandler := handler.NewAuthHandler(userRepo)

	// Create Hertz server
	h := server.Default(server.WithHostPorts(":8080"))

	// CORS middleware — allow Next.js frontend
	h.Use(cors.New(cors.Config{
		AllowOrigins:     []string{"http://localhost:3000", "http://127.0.0.1:3000"},
		AllowMethods:     []string{"GET", "POST", "PUT", "DELETE", "OPTIONS"},
		AllowHeaders:     []string{"Origin", "Content-Type", "Accept", "Authorization"},
		ExposeHeaders:    []string{"Content-Length"},
		AllowCredentials: true,
		MaxAge:           12 * time.Hour,
	}))

	// Register routes
	api := h.Group("/api")
	{
		// Movie routes
		api.GET("/movies", movieHandler.ListMovies)
		api.GET("/movies/:id", movieHandler.GetMovie)

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
	}

	fmt.Println("🚀 ScreenScout API server starting on :8080")
	h.Spin()
}
