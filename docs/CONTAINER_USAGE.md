# Container Usage

This project now includes a reproducible container path for the native manual GUI app.

## Build Image

```bash
./scripts/build_container.sh
```

This builds:

```text
manual-notes-compiler:local
```

## Run GUI App

On a Linux desktop with X11:

```bash
./scripts/run_container_gui.sh
```

The script mounts the current project at:

```text
/workspace
```

So the app can open folders such as:

```text
/workspace/computer_networks
/workspace/dsa_solutions
/workspace/datawarehousing
```

## Docker Compose

Alternative:

```bash
docker compose up --build
```

## Extract .deb

```bash
./scripts/extract_deb_from_container.sh
```

The package is copied to:

```text
dist/
```

## Host Requirements

- Docker daemon running.
- X11 display available.
- `DISPLAY` environment variable set.
- If needed, allow local Docker X11 access:

```bash
xhost +local:docker
```

## Current Limitation In This Session

Docker is installed here, but pulling `ubuntu:24.04` failed due DNS/network access. The files are ready; the image build needs Docker Hub access or a preloaded `ubuntu:24.04` image.
