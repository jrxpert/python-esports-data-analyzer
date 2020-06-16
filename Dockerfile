FROM alpine:3.9 AS alpine


ENV APP_DIR /data/app/instance/
ENV CONF_DIR /data/app/config/
ENV STRG_DIR /data/app/storage/
ENV VENV_DIR /data/app/venv/
ARG PY_VERSION="3.6"
ARG PY_PKG_REPO="v3.9"
ARG PG_VERSION="11"
ARG PG_PKG_REPO="v3.9"


# Install system packages
RUN apk add --update --no-cache \
    bash sudo wget


# Install locale - https://github.com/Auswaschbar/alpine-localized-docker/blob/6e53342f45c15cd6045930aca32e0d79be28eff2/Dockerfile
ENV MUSL_LOCPATH="/usr/share/i18n/locales/musl"
RUN apk --no-cache add libintl \
	&& apk --no-cache --virtual .locale_build add cmake make musl-dev gcc gettext-dev git \
	&& git clone https://gitlab.com/rilian-la-te/musl-locales \
	&& cd musl-locales && cmake -DLOCALE_PROFILE=OFF -DCMAKE_INSTALL_PREFIX:PATH=/usr . && make && make install \
	&& cd .. && rm -r musl-locales \
	&& apk del .locale_build


# Install Python3
RUN apk add --update --no-cache \
    --repository=http://dl-cdn.alpinelinux.org/alpine/${PY_PKG_REPO}/main \
    py3-cryptography \
    python3=~${PY_VERSION} python3-dev=~${PY_VERSION} py3-pip uwsgi-python3 \
    # Create symlinks for python and pip, upgrade pip and setuptools, install virtualenv
    && ln -s /usr/bin/python3 /usr/local/bin/python \
    && ln -s /usr/bin/python3-config /usr/local/bin/python-config \
    && ln -s /usr/bin/pip3 /usr/local/bin/pip \
    && pip install --upgrade --no-cache-dir pip \
    && pip install --upgrade setuptools \
    && pip install virtualenv


# Install grpcio (requires build-base, linux-headers)
RUN apk add --update --no-cache \
	build-base \
	linux-headers \
	&& pip install grpcio


# Install uwsgi (requires gcc)
RUN apk add --update --no-cache \
	gcc \
	&& pip install uwsgi


# Install Postgre SQL
RUN apk add --repository=http://dl-cdn.alpinelinux.org/alpine/${PG_PKG_REPO}/main \
	postgresql=~${PG_VERSION} \
	postgresql-client=~${PG_VERSION} \
	postgresql-dev=~${PG_VERSION} \
	postgresql-contrib=~${PG_VERSION}

# ENV for Postgre SQL initialization, also used in application code (getenv)
ENV DB_DATA /data/db
ENV DB_HOST 127.0.0.1
ENV DB_PORT 5432

# Initialize Postgre SQL
RUN mkdir -p /run/postgresql \
	&& chown -R postgres:postgres /run/postgresql \
	&& chmod 2777 /run/postgresql \
	&& mkdir -p ${DB_DATA} \
	&& chown -R postgres:postgres ${DB_DATA} \
	&& chmod 0777 ${DB_DATA} \
	&& sudo -u postgres initdb -D ${DB_DATA} \
	&& echo "listen_addresses='${DB_HOST}'" >> ${DB_DATA}/postgresql.conf \
	&& echo "port=${DB_PORT}" >> ${DB_DATA}/postgresql.conf \
	&& echo "host all  all    ${DB_HOST}/32  trust" >> ${DB_DATA}/pg_hba.conf

# Install psycopg2 (requires gcc, musl-dev, postgresql-dev)
RUN apk add --update --no-cache \
	gcc \
	musl-dev \
    && apk add --repository=http://dl-cdn.alpinelinux.org/alpine/${PG_PKG_REPO}/main \
	postgresql-dev=~${PG_VERSION} \
	&& pip install psycopg2==2.8.*


# Uninstall requirements (gcc, musl-dev, postgresql-dev, build-base and linux-headers) here - grpcio, psycopg2 and uwsgi are already built
RUN apk del --update \
	gcc \
	musl-dev \
	postgresql-dev \
	linux-headers \
	build-base


# Change root password from build argument, set chmod to 777 for socket dir "/run"
ARG alpine_root_password
RUN  echo -e "${alpine_root_password}\n${alpine_root_password}" | sudo passwd root \
    && chmod 777 /run

# Install nginx, uwsgi-python3, supervisor, mc, apache2-utils (HTTP Basic Auth)
RUN apk add --update --no-cache \
	nginx uwsgi-python3 supervisor mc apache2-utils


# Setup HTTP Basic Authentication from build arguments and set credentials in ENV
ARG nginx_http_user
ARG nginx_http_password
RUN mkdir -p /etc/apache2 \
    && sudo htpasswd -bcs /etc/apache2/.htpasswd ${nginx_http_user} "${nginx_http_password}"
ENV HTTP_USER ${nginx_http_user}
ENV HTTP_PASSWORD ${nginx_http_password}


# Create app and storage directories, create user www-data:www-data, set chown app storage to www-data
# Set chmod to tmp because of Postgre SQL COPY TO permissions problem
# Copy requirements.txt, before rest of application code for caching
RUN  mkdir -p ${APP_DIR} \
    ${STRG_DIR}log \
    ${STRG_DIR}tmp \
    && adduser --ingroup=www-data --disabled-password www-data \
    && chown -R www-data:www-data ${STRG_DIR} \
	&& chmod 777 ${STRG_DIR}tmp
COPY ./requirements.txt ${APP_DIR}


# Create virtualenv, activate, export ENV variables, install framework and requirements into it
# --system-site-packages use pre-installed grpcio and psycopg2
# grpcio and psycopg2 required packages can be uninstalled after this
RUN virtualenv ${VENV_DIR} --system-site-packages \
    && . ${VENV_DIR}bin/activate \
    && pip install -r ${APP_DIR}requirements.txt


# Copy application code, nginx webserver, supervisord, uwsgi and application configurations, 502.html, GCP account JSON
WORKDIR ${APP_DIR}
COPY ./ ${APP_DIR}
COPY docker/nginx.conf /etc/nginx/nginx.conf
COPY docker/nginx-site.conf /etc/nginx/conf.d/
COPY docker/supervisord.conf /etc/supervisord.conf
COPY docker/uwsgi.docker.ini ${CONF_DIR}uwsgi.ini
COPY docker/settings.docker.py ${APP_DIR}config/settings.py
COPY datanal/config/api_settings.example.py ${APP_DIR}datanal/config/api_settings.py
COPY docker/502.html ${CONF_DIR}502.html
COPY docker/gcp-developer.json ${CONF_DIR}gcp-developer.json
# Chown files out of APP directory
RUN chown www-data:www-data ${CONF_DIR}gcp-developer.json


# Remove cache, git, virtualenv, etc. development folders (.cache .pytest_cache .git .tox __pycache__) and docker
RUN rm -rf  ${APP_DIR}.cache \
    ${APP_DIR}.pytest_cache \
    ${APP_DIR}.git \
    ${APP_DIR}.tox \
    ${APP_DIR}docker \
    && find ${APP_DIR} -type d -regex ``.*__pycache__.*'' -exec rm -rf {} +


# Clean
RUN rm -rf /var/cache/apk/*


# ENV for Postgre SQL create user and database, also used in application code (getenv)
ENV DB_NAME datanal
ENV DB_USERNAME datanal
ENV DB_PASSWORD datanal
ENV DB_MAXCONN 50
ENV DB_LOG true

# Create database, user and table structure from script
RUN sudo -u postgres pg_ctl start -D ${DB_DATA} \
    && sudo -u postgres psql --command="CREATE USER \"${DB_USERNAME}\" WITH PASSWORD '${DB_PASSWORD}';" \
	--command="ALTER USER \"${DB_USERNAME}\" WITH SUPERUSER;" \
    --command="CREATE DATABASE \"${DB_NAME}\" WITH OWNER = \"${DB_USERNAME}\" ENCODING = 'UTF8' LC_COLLATE='C' LC_CTYPE='C' CONNECTION LIMIT = -1 TEMPLATE template0;" \
    --command="REVOKE ALL PRIVILEGES ON DATABASE \"${DB_NAME}\" FROM PUBLIC;" \
    --command="GRANT ALL PRIVILEGES ON DATABASE \"${DB_NAME}\" TO \"${DB_USERNAME}\";" \
    && sudo -u postgres psql --username=${DB_USERNAME} --dbname=${DB_NAME} --file=${APP_DIR}datanal/db/create.sql


# Setup CRON monitoring
COPY docker/crontab.txt /var/crontab.txt
RUN chmod +x ${APP_DIR}bin/run-watching-and-collecting \
	&& chmod 644 /var/crontab.txt \
	&& touch /var/log/cron.log \
	&& crontab /var/crontab.txt > /var/log/cron.log


# Expose on port 80
EXPOSE 80

# Let supervisord run uswgi application server and nginx web server
CMD ["/usr/bin/supervisord", "-c", "/etc/supervisord.conf"]
