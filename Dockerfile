# Dockerfile

# 1. Use an official Python image as the base (slim is a smaller, more secure option)
FROM python:3.10-slim

# 2. Set the working directory for all subsequent instructions
WORKDIR /app

# 3. Copy the dependency file into the container at /app
COPY requirements.txt .

# 4. Install the dependencies
RUN pip install --no-cache-dir -r requirements.txt

# 5. Copy the rest of your application code into the container
# The dot '.' refers to the current local directory and the current container working directory (/app)
COPY . .

# 6. Expose the port your application listens on (optional, required for web apps)
# EXPOSE 8000

# 7. Define the command to run your application when the container starts
# Replace 'main.py' with the name of your project's primary script or entry point
#Todo: change main.py to your entry point file
CMD ["python", "main.py"]