# Use an official Python runtime as a parent image
FROM python:3.11-slim

# Set the working directory in the container
WORKDIR /app

# Install uv
RUN pip install uv

# Copy the requirements file into the container at /app
COPY requirements.txt .
COPY pyproject.toml .

# Install any needed packages specified in requirements.txt
RUN uv pip install --system --no-cache-dir -r requirements.txt

# Copy the rest of the application's code into the container at /app
COPY . .

# Make the run script executable
RUN chmod +x ./run.sh

# Expose port 5000 to the outside world
EXPOSE 5000

# Command to run the application
CMD ["./run.sh"]
