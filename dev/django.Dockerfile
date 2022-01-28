FROM python:3.8-slim
# Install system librarires for Python packages:
# * psycopg2
RUN apt-get update && \
    apt-get install --no-install-recommends --yes \
        libpq-dev gcc libc6-dev curl unzip \
        libgl1-mesa-glx libxt6 libglib2.0-0 && \
    rm -rf /var/lib/apt/lists/*

RUN curl -sL https://deb.nodesource.com/setup_16.x  | bash - && \
    apt-get update && \
    apt-get install --yes --no-install-recommends \
    nodejs && \
    npm install -g npm@latest && \
    npm --version && \
    node --version && \
    npm install -g yarn && \
    yarn --version

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

RUN curl -L -o /tmp/shapeworks.zip https://github.com/SCIInstitute/ShapeWorks/releases/download/v6.0.0/ShapeWorks-v6.0.0-linux.zip && \
    unzip -d /opt /tmp/shapeworks.zip && rm /tmp/shapeworks.zip
ENV PATH $PATH:/opt/ShapeWorks-v6.0.0-linux/bin

# Only copy the setup.py, it will still force all install_requires to be installed,
# but find_packages() will find nothing (which is fine). When Docker Compose mounts the real source
# over top of this directory, the .egg-link in site-packages resolves to the mounted directory
# and all package modules are importable.
COPY ./setup.py /opt/django-project/setup.py
RUN pip install -U pip
RUN pip install --editable /opt/django-project[dev]

# Use a directory name which will never be an import name, as isort considers this as first-party.
WORKDIR /opt/django-project
