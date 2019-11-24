docker logs heartbeat
echo "logging docker in"
echo "$DOCKER_PASSWORD" | docker login -u "$DOCKER_USERNAME" --password-stdin
echo "pushing to docker..."
docker push mowoe/heartbeat:latest
if [ $(curl -s -o /dev/null -w "%{http_code}" http://localhost:5000/ | cut -c1-3) == "200" ]; then
	echo "success"
	exit 0
else
	curl "http://localhost:5000/"
	echo "error"
	exit 1
fi
