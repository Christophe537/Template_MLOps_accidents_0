# Use an offical Python image
FROM python:3.9

RUN pip install --upgrade pip
RUN mkdir -p /app/src
RUN mkdir -p /app/app
WORKDIR /app/app

# Copy app files into the container
COPY . /app/app

# Install useful dependencies
RUN python -m pip install -r /app/app/requirements.txt

# ADD DIRECTORY  "src" to PYTHONPATH
ENV PYTHONPATH "${PYTHONPATH}:/app/src"

# Launch the API
CMD ["uvicorn", "main:api", "--host", "0.0.0.0", "--port", "8000"]
