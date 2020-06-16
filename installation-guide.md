# Install

Requirements:

* Python 3.6 and higher
* virtualenv
* pip
* tox
* docker
* google-cloud-sdk
* Postgre SQL

## Check python and pip versions

* `$ python --version`
* `$ pip --version`

## Upgrade pip and install tox (globally)

* `$ pip install --upgrade pip`
* `$ pip install tox`

## Create target directory

* `$ mkdir -p /data/app/instance`
* `$ cd /data/app/instance`

## Checkout code

* `$ git clone https://github.com/jrxpert/python-esports-data-analyzer.git ./`

## Create rest of directory structure

* `/data/app/storage`
  * `log`
  * `tmp`

## Development mode

### Create development environment

* `$ tox -e dev` or `$ tox --recreate -e dev` for required package update
* `$ source .tox/dev/bin/activate`
* `$ python setup.py develop`

### Configuration

* In `instance/config/` copy `settings.example.py` to `settings.py` and optionally edit it.
* In `instance/lib/sql/config/` copy `settings.example.py` to `settings.py` and optionally edit it.
* In `instance/datanal/config/` copy `api_settings.example.py` to `api_settings.py` and optionally edit it.

### Run webserver

* `$ python server.py`

### Invoke tasks

Available tasks:

* `$ inv -l` - list all available Invoke commands execute
* `$ inv lint` - linter
* `$ inv test` - all tests
* `$ inv test1 -p /path/to/` - specified test
* `$ inv clean`
* `$ inv cov` - test coverage
* `$ inv dupl` - duplications

## Production mode in Docker

> python esports data analyzer uses WSGI and exposes HTTP server.

To test that HTTP server is running:

* `$ docker run -dti datanal:latest`
* `$ docker ps`
* `$ docker exec -ti <container_id> /bin/bash`
* In Docker image console
  * `$ curl -v http://127.0.0.1:8080/ping`
    * If successfull HTTP client can call one simple server method called ping() that returns `pong`.
  * `$ exit`
