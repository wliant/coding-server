FROM node:20-alpine

WORKDIR /app

RUN apk add --no-cache chromium nss freetype harfbuzz ca-certificates ttf-freefont

ENV PLAYWRIGHT_BROWSERS_PATH=/ms-playwright
ENV PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD=1
ENV CHROMIUM_PATH=/usr/bin/chromium-browser

RUN npm install -g playwright@latest && \
    npx playwright install chromium --with-deps 2>/dev/null || true

COPY package.json ./
RUN npm install

COPY . .

CMD ["npx", "playwright", "test"]
