# Use the official Python image from the Docker Hub
FROM python:3.9-slim

# Set the working directory inside the container
WORKDIR /app

# Copy the current directory contents into the container at /app
COPY . /app/

# Install any needed dependencies specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Expose the port the app runs on (Flask default is 5000)
EXPOSE 5000

# Set the environment variable to specify the Flask app entry point
ENV FLASK_APP=app.py

# Command to run Flask app (make sure it binds to all interfaces)
CMD ["flask", "run", "--host=0.0.0.0", "--port=5000"]