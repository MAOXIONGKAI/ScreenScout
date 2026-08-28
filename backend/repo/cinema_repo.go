package repo

import (
	"context"
	"fmt"
	"strings"

	"github.com/jackc/pgx/v5/pgxpool"
	"github.com/maoxiongkai/screenscout-backend/model"
)

// CinemaRepo provides database access for cinema data.
type CinemaRepo struct {
	Pool *pgxpool.Pool
}

// NewCinemaRepo creates a new CinemaRepo.
func NewCinemaRepo(pool *pgxpool.Pool) *CinemaRepo {
	return &CinemaRepo{Pool: pool}
}

// ListCinemas returns all cinemas, optionally filtered by provider name.
// Provider maps to cinema name: GV → "Golden Village", SHAW → "Shaw Theatres" / "Shaw Theatre"
func (r *CinemaRepo) ListCinemas(ctx context.Context, provider string) ([]model.Cinema, error) {
	var query string
	var args []interface{}

	if strings.TrimSpace(provider) != "" {
		providerUpper := strings.ToUpper(strings.TrimSpace(provider))
		if providerUpper == "GV" || strings.Contains(providerUpper, "GOLDEN") {
			query = `SELECT id, name, branch, postal_code, address, created_at
			         FROM cinemas WHERE name ILIKE '%Golden Village%' ORDER BY branch`
		} else if providerUpper == "SHAW" || strings.Contains(providerUpper, "SHAW") {
			query = `SELECT id, name, branch, postal_code, address, created_at
			         FROM cinemas WHERE name ILIKE '%Shaw%' ORDER BY branch`
		} else {
			query = `SELECT id, name, branch, postal_code, address, created_at
			         FROM cinemas WHERE name ILIKE $1 OR branch ILIKE $1 ORDER BY branch`
			args = append(args, "%"+provider+"%")
		}
	} else {
		query = `SELECT id, name, branch, postal_code, address, created_at
		         FROM cinemas ORDER BY name, branch`
	}

	rows, err := r.Pool.Query(ctx, query, args...)
	if err != nil {
		return nil, fmt.Errorf("list cinemas: %w", err)
	}
	defer rows.Close()

	var cinemas []model.Cinema
	for rows.Next() {
		var c model.Cinema
		if err := rows.Scan(&c.ID, &c.Name, &c.Branch, &c.PostalCode, &c.Address, &c.CreatedAt); err != nil {
			return nil, fmt.Errorf("scan cinema: %w", err)
		}
		cinemas = append(cinemas, c)
	}

	return cinemas, nil
}

// ListProviders returns the distinct list of movie providers.
func (r *CinemaRepo) ListProviders(ctx context.Context) ([]string, error) {
	query := `SELECT DISTINCT provider FROM movies ORDER BY provider`
	rows, err := r.Pool.Query(ctx, query)
	if err != nil {
		return nil, fmt.Errorf("list providers: %w", err)
	}
	defer rows.Close()

	var providers []string
	for rows.Next() {
		var p string
		if err := rows.Scan(&p); err != nil {
			return nil, fmt.Errorf("scan provider: %w", err)
		}
		providers = append(providers, p)
	}

	return providers, nil
}

// mapProviderToName maps provider code to cinema name.
func mapProviderToName(provider string) string {
	switch strings.ToUpper(strings.TrimSpace(provider)) {
	case "GV":
		return "Golden Village"
	case "SHAW":
		return "Shaw Theatres"
	default:
		return ""
	}
}
