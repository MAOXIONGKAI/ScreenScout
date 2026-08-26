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
	"github.com/maoxiongkai/screenscout-backend/repo"
)

func main() {
	// Database connection
	dbURL := os.Getenv("DATABASE_URL")
	if dbURL == "" {
		dbURL = "postgresql://postgres:postgres@localhost:5432/screenscout"
	}

	ctx := context.Background()
	pool, err := pgxpool.New(ctx, dbURL)
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

	// Initialize handlers
	movieHandler := handler.NewMovieHandler(movieRepo)
	cinemaHandler := handler.NewCinemaHandler(cinemaRepo)

	// Create Hertz server
	h := server.Default(server.WithHostPorts(":8080"))

	// CORS middleware — allow Next.js frontend
	h.Use(cors.New(cors.Config{
		AllowOrigins:     []string{"http://localhost:3000", "http://127.0.0.1:3000"},
		AllowMethods:     []string{"GET", "POST", "PUT", "DELETE", "OPTIONS"},
		AllowHeaders:     []string{"Origin", "Content-Type", "Accept"},
		ExposeHeaders:    []string{"Content-Length"},
		AllowCredentials: true,
		MaxAge:           12 * time.Hour,
	}))

	// Register routes
	api := h.Group("/api")
	{
		api.GET("/movies", movieHandler.ListMovies)
		api.GET("/movies/:id", movieHandler.GetMovie)
		api.GET("/cinemas", cinemaHandler.ListCinemas)
		api.GET("/providers", cinemaHandler.ListProviders)
	}

	fmt.Println("🚀 ScreenScout API server starting on :8080")
	h.Spin()
}
