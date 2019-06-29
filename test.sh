curl "http://localhost:5000/"
if [ $(curl -s -o /dev/null -w "%{http_code}" http://localhost:5000/ | cut -c1-3) == "200" ]; then
	echo "success"
	exit 0
else
	echo "error" >&2
	exit 1
fi
