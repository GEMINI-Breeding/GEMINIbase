# Use Redis Alpine as base image for smaller size
FROM redis:7.2-alpine

# Add Labels
# LABEL maintainer="Pranav Ghate"
# LABEL description="Gemini Logger based on Redis"

# # Create directory for Redis data
# RUN mkdir -p /data && chown redis:redis /data


# # Copy custom Redis configuration
# COPY redis.conf /usr/local/etc/redis/redis.conf
# RUN chown redis:redis /usr/local/etc/redis/redis.conf \
#     && chmod 644 /usr/local/etc/redis/redis.conf \
#     && sed -i \
#        -e "s/\${REDIS_PORT}/6379/g" \
#        -e "s/\${REDIS_MAX_MEMORY}/256mb/g" \
#        -e "s/\${REDIS_PASSWORD}/defaultpassword/g" \
#        /usr/local/etc/redis/redis.conf


# # Replace variables in Redis configuration
# RUN sed -i "s|{{REDIS_PORT}}|${REDIS_PORT}|g" /usr/local/etc/redis/redis.conf \
#     && sed -i "s|{{REDIS_MAX_MEMORY}}|${REDIS_MAX_MEMORY}|g" /usr/local/etc/redis/redis.conf \
#     && sed -i "s|{{REDIS_PASSWORD}}|${REDIS_PASSWORD}|g" /usr/local/etc/redis/redis.conf

# # Switch to non-root user
# USER redis

# # Define volume for data persistence
# VOLUME /data

# # Expose Redis port
# EXPOSE ${REDIS_PORT}

# # Healthcheck
# HEALTHCHECK --interval=10s --timeout=5s --retries=3 \
#     CMD redis-cli --raw ping || exit 1

# # Set the command to run Redis server with explicit config path
# CMD redis-server /usr/local/etc/redis/redis.conf \
#     --requirepass "${REDIS_PASSWORD}" \
#     --port ${REDIS_PORT} \
#     --maxmemory ${REDIS_MAX_MEMORY}
# Baked in so the production stack needs no source checkout (the dev stack
# bind-mounts the same file over it).
COPY redis.conf /usr/local/etc/redis/redis.conf
