FROM nvidia/cuda:11.8.0-base-ubuntu20.04

ENV DEBIAN_FRONTEND=noninteractive


WORKDIR /src
COPY app/ ./app
COPY models/ ./models
COPY settings ./settings
COPY requirements.txt ./

RUN apt-get update && \
    apt-get install -y build-essential zlib1g-dev libncurses5-dev libgdbm-dev \
    libnss3-dev libssl-dev libreadline-dev libffi-dev libbz2-dev liblzma-dev libpython3-stdlib wget

RUN wget https://www.python.org/ftp/python/3.11.8/Python-3.11.8.tar.xz && \
    tar -xf Python-3.11.8.tar.xz && \
    cd Python-3.11.8 && \
    ./configure --enable-optimizations --with-ensurepip=install && \
    make -j $(nproc) && \
    make install

# Clean up unnecessary files
RUN rm -rf /tmp/Python-3.11.8*

RUN apt-get install -y python3-pip && \
pip install -r requirements.txt

CMD ["python", "-m", "app.main"]

