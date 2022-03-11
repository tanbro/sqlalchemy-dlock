# 用于在 Docker 中运行测试:
# eg:
# docker run -it --rm -v "$(pwd):/work" -w /work --env-file .env python /bin/bash /work/scripts/run-tests.sh

set -e

docker-compose up --rm --abort-on-container-exit