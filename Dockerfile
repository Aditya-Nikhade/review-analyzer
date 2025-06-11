# Dockerfile

# Use an official Python runtime as a parent image.
# Using python:3.9-slim is a good balance of size and functionality.
FROM python:3.9-slim

# Set the working directory inside the container.
# All subsequent commands will be run from this directory.
WORKDIR /app

# Copy the file that lists our Python dependencies.
COPY requirements.txt .

# Install the dependencies.
# --no-cache-dir makes the image smaller.
RUN pip install --no-cache-dir -r requirements.txt

# Copy all the application code and data from your local machine
# into the /app directory inside the container.
# The .dockerignore file will prevent venv, etc., from being copied.
COPY . .

# Expose port 5000. This tells Docker that the container will listen
# on this port for the web application.
EXPOSE 5000

# The default command to run when the container starts.
# We will often override this, but it's good practice to have a default.
# Here, we default to starting the web server with gunicorn.
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "2", "app:app"]