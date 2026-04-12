FROM node:20-alpine

WORKDIR /app

COPY package.json package-lock.json ./

RUN npm install --silent

COPY . .

EXPOSE 3000

ENV REACT_APP_API_URL=http://localhost:8000

CMD ["npm", "start"]
