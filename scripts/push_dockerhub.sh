#!/usr/bin/env bash
# Push the local image to Docker Hub.
#   DOCKERHUB_USER=koalalive ./scripts/push_dockerhub.sh
#   DOCKERHUB_USER=koalalive DOCKERHUB_TOKEN=xxx ./scripts/push_dockerhub.sh
set -euo pipefail
cd "$(dirname "$0")/.."

USERNAME="${DOCKERHUB_USER:-}"
TOKEN="${DOCKERHUB_TOKEN:-}"
IMAGE_LOCAL="${IMAGE_LOCAL:-neurodaily:local}"
REPO="${REPO:-neurodaily}"
TAG="${TAG:-latest}"
DATE_TAG="$(date +%Y%m%d)"

[ -n "$USERNAME" ] || { echo "usage: DOCKERHUB_USER=<name> [DOCKERHUB_TOKEN=<token>] $0"; exit 1; }
docker info >/dev/null 2>&1 || { echo "FAIL: docker daemon not running"; exit 1; }
docker image inspect "$IMAGE_LOCAL" >/dev/null 2>&1 || { echo "FAIL: $IMAGE_LOCAL not found (build first)"; exit 1; }

if [ -n "$TOKEN" ]; then
  printf '%s' "$TOKEN" | docker login -u "$USERNAME" --password-stdin
else
  docker login -u "$USERNAME"
fi

docker tag "$IMAGE_LOCAL" "$USERNAME/$REPO:$TAG"
docker tag "$IMAGE_LOCAL" "$USERNAME/$REPO:$DATE_TAG"
docker push "$USERNAME/$REPO:$TAG"
docker push "$USERNAME/$REPO:$DATE_TAG"
echo "OK pushed docker.io/$USERNAME/$REPO:$TAG and :$DATE_TAG"
