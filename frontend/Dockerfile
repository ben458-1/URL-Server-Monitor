# ---------- Stage 1: Build ----------
FROM node:18 AS builder

WORKDIR /app

# Install dependencies
COPY package*.json ./
RUN npm install

# Copy rest of the files and build
COPY . .
RUN npm run build


# ---------- Stage 2: Serve ----------
FROM nginx:1.24.0-alpine

# Custom Nginx config
COPY server-conf/default.conf /etc/nginx/conf.d/default.conf

# Copy built frontend files
COPY --from=builder /app/build /usr/share/nginx/html

EXPOSE 8001

CMD ["nginx", "-g", "daemon off;"]
