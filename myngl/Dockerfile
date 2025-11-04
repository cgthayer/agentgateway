FROM ubuntu:24.04

RUN rm -f /var/cache/apt/archives/*.deb /var/cache/apt/archives/partial/*.deb /var/cache/apt/*.bin || true
RUN apt update
RUN apt install -y strace
RUN apt install -y python3 python3-pip python3-venv

# Set environment variables to disable pip's rich output and threading issues
ENV PIP_PROGRESS_BAR=off
# ENV PIP_NO_CACHE_DIR=1
ENV PIP_DISABLE_PIP_VERSION_CHECK=1
ENV PYTHONUNBUFFERED=1
ENV RUST_BACKTRACE=full

# ENV UV_CACHE_DIR=/tmp/.cache
# RUN mkdir $UV_CACHE_DIR && chmod a+rw $UV_CACHE_DIR

WORKDIR /app

RUN python3 -m venv .venv
ENV VIRTUAL_ENV=/app/.venv
ENV PATH="$VIRTUAL_ENV/bin:$PATH"
RUN pip install uv

# Configure pip to avoid threading issues globally
# RUN pip config --global set global.progress_bar off

COPY pyproject.toml .
COPY README.md .

RUN uv cache dir
RUN uv pip install -q --upgrade pip
RUN uv pip install -q hatchling editables
RUN --mount=type=cache,target=/tmp/.cache,id=uv-cache-myngl \
    uv --no-progress pip install -e .

# note the .venv is excluded in .dockerignore
COPY . .

# MCP: for connecting to the trino(s)
RUN apt install -y curl
RUN curl -fsSL https://raw.githubusercontent.com/tuannvm/mcp-trino/main/install.sh | bash
ENV PATH="/root/.local/bin:$PATH"

EXPOSE 3030
CMD ["/app/app.py"]
