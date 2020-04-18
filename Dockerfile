# Dockerfile may have two Arguments: tag, branch
# tag - tag for the Base image, (e.g. 1.14.0-py3 for tensorflow)
# branch - user repository branch to clone (default: master, other option: test)
ARG tag=1.14.0-py3

# Base image, e.g. tensorflow/tensorflow:tag
FROM tensorflow/tensorflow:${tag}

MAINTAINER Daniel Garcia Diaz (IFCA) <garciad@ifca.unican.es>
LABEL version='0.0.1'
## Project to provide data from Sentinel-2 or Landsat 8 satellite
## Project to perform super-resolution on satellite imagery

## Install tools
RUN  apt-get update && \
  apt-get install -y --reinstall build-essential && \
    apt-get install -y git && \
    apt-get install -y curl python3-setuptools python3-pip python3-wheel


## Install spatial packages (python APIs)
#Install gdal
RUN apt update && \
  apt install -y gdal-bin python3-gdal

# Install netCDF4
RUN apt-get update -y
RUN apt-get install -y python3-netcdf4

## Python package
RUN pip3 install xmltodict

## Onedata
RUN exec 3<> /etc/apt/sources.list.d/onedata.list && \
    echo "deb [arch=amd64] http://packages.onedata.org/apt/ubuntu/1902 xenial main" >&3 && \
    echo "deb-src [arch=amd64] http://packages.onedata.org/apt/ubuntu/1902 xenial main" >&3 && \
    exec 3>&-
RUN curl http://packages.onedata.org/onedata.gpg.key | apt-key add -
RUN apt-get update && curl http://packages.onedata.org/onedata.gpg.key | apt-key add -
RUN apt-get install oneclient=19.02.1-1~xenial -y

## GitHUB Repositories
RUN mkdir wq_sat

RUN ls

# What user branch to clone (!)
ARG branch=master

## git clone and Install sat package
RUN cd ./wq_sat && \
    git clone https://github.com/garciadd/sat.git

## Create config file
RUN exec 3<> ./wq_sat/sat/sat_modules/config.py && \
    echo "#Onedata config" >&3 && \
    echo "onedata_mode = 1" >&3 && \
    echo "onedata_token = \"$ONEDATA_TOKEN\"" >&3 && \
    echo "onedata_url = \"https://vm027.pub.cloud.ifca.es\"" >&3 && \
    echo "onedata_api = \"/api/v3/oneprovider/\"" >&3 && \
    echo "onedata_user = \"user\"" >&3 && \
    echo "onedata_space = \"XDC_LifeWatch\"" >&3 && \
    echo "datasets_path = \"/onedata/output/XDC_LifeWatch\"" >&3 && \
    echo "#Sentinel credentials" >&3 && \
    echo "sentinel_pass = {'username':\"lifewatch\", 'password':\"xdc_lfw_data\"}" >&3 && \
    echo "#Landsat credentials" >&3 && \
    echo "landsat_pass = {'username':\"lifewatch\", 'password':\"xdc_lfw_data2018\"}" >&3 && \
    exec 3>&-

## api installation
RUN cd ./wq_sat/sat && \
    python3 setup.py install


# clone and Install atcor package
RUN cd ./wq_sat && \
    git clone -b $branch https://github.com/garciadd/atcor.git && \
    cd  atcor && \
    python3 setup.py install


# clone and Install atcor package
RUN cd ./wq_sat && \
    git clone -b $branch https://github.com/garciadd/wq_server.git


### Jupyterlab
RUN pip3 --no-cache-dir install jupyter jupyterlab && \
    python3 -m ipykernel.kernelspec


## For Jupyter terminal
ENV SHELL /bin/bash
EXPOSE 8888

# Open Jupyter port
# REMINDER: Tensorflow Docker Images already EXPOSE ports 6006 and 8888

