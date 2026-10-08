FROM ubuntu:24.04 AS build

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    cmake \
    g++ \
    make \
    qtbase5-dev \
    poppler-utils \
    dpkg-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /src
COPY native_app ./native_app
COPY packaging ./packaging

RUN CXX=/usr/bin/g++ CC=/usr/bin/gcc \
    cmake -S native_app -B build/native_app -DCMAKE_BUILD_TYPE=Release \
    && cmake --build build/native_app --parallel

RUN mkdir -p /artifact \
    && bash packaging/build_deb.sh \
    && cp dist/*.deb /artifact/

FROM ubuntu:24.04 AS runtime

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
    libqt5widgets5 \
    libqt5gui5 \
    libqt5core5a \
    poppler-utils \
    && rm -rf /var/lib/apt/lists/*

COPY --from=build /src/build/native_app/manual-notes-compiler /usr/local/bin/manual-notes-compiler

WORKDIR /workspace
ENTRYPOINT ["manual-notes-compiler"]
