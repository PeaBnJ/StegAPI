# Step 1: Use the official Python image as the base image
FROM python:3.9-slim

# Step 2: Set the working directory to /app inside the container
WORKDIR /app

# Step 3: Copy the backend's requirements.txt file to the container
COPY backend/requirements.txt /app/requirements.txt

# Step 4: Install the backend dependencies
RUN pip install --no-cache-dir -r /app/requirements.txt

# Step 5: Copy the backend app folder into the container
COPY backend/app /app/app

# Step 6: Copy the frontend folder into the container (make sure the frontend folder exists in your project)
COPY frontend /app/frontend

# Step 7: Install any necessary tools for serving the frontend (optional for FastAPI)
RUN apt-get update && apt-get install -y \
    npm \
    && rm -rf /var/lib/apt/lists/*

# Step 8: Optionally, you can build the frontend here if you're using a JavaScript framework (e.g., React, Vue, etc.)
# RUN npm install --prefix /app/frontend && npm run build --prefix /app/frontend

# Step 9: Expose the port the app will run on (default FastAPI is 8000)
EXPOSE 8080

# Step 10: Start the FastAPI app using uvicorn
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]