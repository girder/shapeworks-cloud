FROM python:3.8-slim
# Install system librarires for Python packages:
# * psycopg2
RUN apt-get update && \
    apt-get install --no-install-recommends --yes \
    libpq-dev gcc libc6-dev curl unzip \
    libgl1-mesa-glx libxt6 libglib2.0-0 \
    libqt5core5a \
    && \
    rm -rf /var/lib/apt/lists/*

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Only copy the setup.py, it will still force all install_requires to be installed,
# but find_packages() will find nothing (which is fine). When Docker Compose mounts the real source
# over top of this directory, the .egg-link in site-packages resolves to the mounted directory
# and all package modules are importable.
COPY ./setup.py /opt/django-project/setup.py
COPY ./swcc/setup.py /opt/django-project/swcc/setup.py
RUN pip install -U pip && \
    pip install --editable /opt/django-project[dev] && \
    pip install --editable /opt/django-project/swcc

# install_shapeworks.sh for DeepSSM python api. This must be run from within a conda environment
# install conda
ENV PATH=/opt/conda/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
ENV LDFLAGS=-L/opt/conda/lib
RUN curl https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh -o /tmp/Miniconda3-latest-Linux-x86_64.sh \
    && bash /tmp/Miniconda3-latest-Linux-x86_64.sh -b -p /opt/conda \
    && ln -s /opt/conda/etc/profile.d/conda.sh /etc/profile.d/conda.sh \
    && conda update -n base -c defaults conda \
    && conda install pip \
    && echo ". /opt/conda/etc/profile.d/conda.sh" >> ~/.bashrc \
    && echo "conda activate base" >> ~/.bashrc

RUN export url=$(curl -s https://api.github.com/repos/SCIInstitute/ShapeWorks/releases | grep -o "http.*dev-linux.*.gz"); \
    curl -L -o /tmp/shapeworks.tgz $url
RUN mkdir /opt/shapeworks && \
    tar -zxvf /tmp/shapeworks.tgz -C /opt/shapeworks --strip-components 1 && \
    rm /tmp/shapeworks.tgz

# Run install_shapeworks.sh
SHELL ["conda", "run", "/bin/bash", "-c"]
RUN cd /opt/shapeworks ; ls ; source install_shapeworks.sh ; conda clean -t -y
SHELL ["conda", "run", "-n", "shapeworks", "bin/bash", "-c"]

# ensure that DeepSSMUtils is loaded
COPY /shapeworks_cloud/test.py ./
RUN python ./test.py

ENV PATH $PATH:/opt/shapeworks/bin
ENV LD_LIBRARY_PATH $LD_LIBRARY_PATH:/opt/shapeworks/lib

# Use a directory name which will never be an import name, as isort considers this as first-party.
WORKDIR /opt/django-project
