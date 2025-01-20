# https://github.com/tursodatabase/libsql/blob/main/Dockerfile
### -- Build extensions --- ###

FROM ghcr.io/tursodatabase/libsql-server:latest AS build_ext

RUN apt-get update \
    && apt-get install -y \
        build-essential \
        git \
        libsqlite3-dev \
        libssl-dev \
        make \
        pkg-config \
        unzip \
        wget \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

RUN wget https://github.com/Kitware/CMake/releases/download/v3.31.4/cmake-3.31.4.tar.gz && tar -xvzf cmake-3.31.4.tar.gz && cd cmake-3.31.4 && ./bootstrap && make -j$(nproc) && make install
RUN git clone --recursive https://github.com/abiliojr/fts5-snowball && cd fts5-snowball && make
RUN git clone https://github.com/wangfenjin/simple && cd simple && mkdir build && cd build && cmake .. && make -j 12 && make install
RUN mkdir sqld_ext && cp fts5-snowball/*.so sqld_ext/ && cp simple/build/src/*.so sqld_ext/
RUN cd sqld_ext && sha256sum *.so > trusted.lst

### -- Runtime --- ###

FROM ghcr.io/tursodatabase/libsql-server:latest
COPY --from=build_ext /var/lib/sqld/sqld_ext /var/lib/sqld/sqld_ext

CMD ["/bin/sqld", "--extensions-path", "sqld_ext"]
