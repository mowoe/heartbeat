docker logs heartbeat
echo "logging docker in"
echo "$DOCKER_PASSWORD" | docker login -u "$DOCKER_USERNAME" --password-stdin
echo "pushing to docker..."
docker push mowoe/heartbeat:latest
