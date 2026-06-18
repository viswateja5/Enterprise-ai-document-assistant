# --- Build Stage ---
FROM node:20-alpine AS build

WORKDIR /app

# Copy package configurations and install node packages
COPY package.json package-lock.json* ./
RUN npm install --legacy-peer-deps

# Copy application source files
COPY . .

# Pass build-time arguments to Vite compiler
ARG VITE_API_URL
ENV VITE_API_URL=$VITE_API_URL

# Compile production-ready distribution files
RUN npm run build

# --- Serve Stage ---
FROM nginx:alpine

# Copy built distribution assets to Nginx server context
COPY --from=build /app/dist /usr/share/nginx/html

# Replace standard default Nginx configuration with our custom server block
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Expose served port
EXPOSE 3000

CMD ["nginx", "-g", "daemon off;"]
