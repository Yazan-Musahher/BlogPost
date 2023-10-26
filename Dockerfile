# Python image from the Docker Hub
FROM python:3.9-slim

# Set the working directory in the container
WORKDIR /app

# Copy the current directory contents into the container at /app? 
COPY . /app

# Install any necessary dependencies
RUN pip install --upgrade pip
RUN pip install flask

# Expose the Flask application's port
EXPOSE 5000

# Command to run the application when the container starts
CMD ["python", "app.py"]