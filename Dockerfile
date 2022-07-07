FROM python:3
COPY dist/concourse-gitea-pr-*.tar.gz .
RUN pip install concourse-gitea-pr-*.tar.gz && \
    mkdir -p /opt/resource && \
    for script in check in out; do ln -sv $(which $script) /opt/resource/; done
