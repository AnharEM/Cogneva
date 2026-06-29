FROM node:20-alpine AS builder

WORKDIR /app
# Install build tools required by node-gyp for native dependencies like better-sqlite3
RUN apk add --no-cache python3 make g++
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build
RUN npm prune --production

FROM node:20-alpine
WORKDIR /app
COPY --from=builder /app/build build/
COPY --from=builder /app/node_modules node_modules/
COPY package.json .

# Define the host and port for adapter-node
ENV HOST=0.0.0.0
ENV PORT=3000
EXPOSE 3000

CMD ["node", "build"]
