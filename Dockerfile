FROM pgvector/pgvector:pg16

# Set default environment variables
ENV POSTGRES_DB=screenscout
ENV POSTGRES_USER=postgres
ENV POSTGRES_PASSWORD=postgres

# Expose default PostgreSQL port
EXPOSE 5432
