# Use the same Python version as your local environment
FROM python:3.10.12-slim

# Set the working directory in the container
WORKDIR /app

# Copy the current directory contents into the container at /app
COPY . /app


RUN pip install --no-cache-dir -r requirements.txt

EXPOSE 5000

# Command to run the application when the container starts
CMD ["python", "app.py"]
