FROM nvcr.io/nvidia/deepstream:6.1.1-devel
WORKDIR /home/deepstream_demo
RUN apt-get update
ARG DEBIAN_FRONTEND=noninteractive

RUN apt install -y libgstreamer1.0-dev libgstreamer-plugins-base1.0-dev ubuntu-restricted-extras build-essential \
    cmake git libgtk2.0-dev pkg-config libavcodec-dev libavformat-dev libswscale-dev \
    libtbb2 libtbb-dev libjpeg-dev libpng-dev libtiff-dev libdc1394-22-dev \
    nasm libx265-dev libnuma-dev libx264-dev python3-gi python3-dev python3-gst-1.0 python-gi-dev git python-dev \
    python3 python3-pip python3.8-dev cmake g++ build-essential libglib2.0-dev \
    libglib2.0-dev-bin libgstreamer1.0-dev libtool m4 autoconf automake libgirepository1.0-dev libcairo2-dev \
    tesseract-ocr


# 1.3 Initialization of submodules

RUN git clone https://github.com/NVIDIA-AI-IOT/deepstream_python_apps
WORKDIR /home/deepstream_demo/deepstream_python_apps
RUN git submodule update --init
RUN git checkout v1.1.4

# 1.4 Installing Gst-python
RUN apt-get install -y apt-transport-https ca-certificates
RUN update-ca-certificates
WORKDIR /home/deepstream_demo/deepstream_python_apps/3rdparty/gst-python/
RUN ./autogen.sh
RUN make
RUN make install

# 2.1.1 Quick build (x86-ubuntu-20.04 | python 3.8 | Deepstream 6.1.1)

WORKDIR /home/deepstream_demo/deepstream_python_apps/bindings
RUN mkdir build
WORKDIR /home/deepstream_demo/deepstream_python_apps/bindings/build
RUN cmake ..
RUN make

# 3.1 Installing the pip wheel
RUN pip3 install ./pyds-1.1.4-py3-none*.whl

WORKDIR /home/deepstream_demo/app