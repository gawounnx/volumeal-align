FROM node:20-alpine AS build

WORKDIR /app
ARG API_BACKEND_URL
ENV API_BACKEND_URL=$API_BACKEND_URL
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM node:20-alpine AS runtime
ENV NODE_ENV=production
WORKDIR /app
COPY --from=build /app ./
EXPOSE 3000
CMD ["npm", "start"]
