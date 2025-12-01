# Use Node.js 23.10 Alpine image
FROM node:23.10-alpine

# Set working directory
WORKDIR /app

# Copy package files
COPY package*.json ./

# Install dependencies
RUN npm ci

# Copy application code
COPY . .

# Wartosci przekazywane z docker-compose.yml przez build args
ARG NEXT_PUBLIC_API_URL
ARG NEXT_PUBLIC_WS_URL

# Build the application
RUN npm run build

# Expose port
EXPOSE 3000

# Run the application
CMD ["npm", "start"]