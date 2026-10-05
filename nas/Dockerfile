# SPDX-License-Identifier: AGPL-3.0-or-later
# Lo justo para calcular la previsión y publicarla: Python con numpy y Pillow
# (el radar), git y ssh (para empujar a gh-pages con la clave de despliegue).
FROM debian:12-slim

ENV DEBIAN_FRONTEND=noninteractive \
    TZ=Europe/Madrid \
    LC_ALL=C.UTF-8

RUN apt-get update && apt-get install -y --no-install-recommends \
      ca-certificates curl git openssh-client tzdata tini \
      python3 python3-numpy python3-pil \
 && ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone \
 && rm -rf /var/lib/apt/lists/*

RUN useradd -u 1000 -m -s /bin/bash jjdeharo

COPY reloj.sh /usr/local/bin/reloj.sh
RUN chmod +x /usr/local/bin/reloj.sh

USER 1000
WORKDIR /proyecto
ENTRYPOINT ["/usr/bin/tini", "--"]
CMD ["/usr/local/bin/reloj.sh"]
