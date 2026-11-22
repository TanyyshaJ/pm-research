FROM node:22-bookworm-slim AS build
WORKDIR /app
COPY package*.json ./
COPY apps/web/package.json apps/web/package.json
RUN npm ci
COPY apps/web apps/web
ENV API_URL=http://api:8000
RUN npm run build
WORKDIR /app/apps/web
EXPOSE 3000
CMD ["npm", "run", "start"]
