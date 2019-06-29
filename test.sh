if [ $(curl -s -o /dev/null -w "%{http_code}" http://localhost:5000/ | cut -c1-3) == "200" ]; then
	curl "http://localhost:5000/"
	echo "success"
else
	echo "error" >&2
fi
