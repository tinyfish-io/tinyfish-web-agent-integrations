# Base image: node-24-lts from the TinyFish Golden Images standard, pinned by
# digest. Apify builds and runs this image; it needs nothing from Apify's own
# base images.
FROM node:24-bookworm-slim@sha256:3638d9a6fe4030bd716be989438248074489337ba3275657f93595428be4fc03 AS builder

WORKDIR /app
COPY package*.json ./
RUN npm ci --audit=false

COPY tsconfig*.json ./
COPY src ./src
RUN npm run build

# The image that runs: production dependencies and the compiled code only.
FROM node:24-bookworm-slim@sha256:3638d9a6fe4030bd716be989438248074489337ba3275657f93595428be4fc03

ENV NODE_ENV=production
RUN mkdir /app && chown node:node /app
USER node
WORKDIR /app

COPY --chown=node:node package*.json ./
RUN npm ci --omit=dev --omit=optional --audit=false && npm cache clean --force

COPY --from=builder --chown=node:node /app/dist ./dist

CMD ["node", "dist/main.js"]
