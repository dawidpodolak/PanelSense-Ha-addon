ARG BUILD_FROM
FROM $BUILD_FROM
# FROM ghcr.io/home-assistant/amd64-base:3.15
WORKDIR /usr/src/app

# Copy in the root filesystem for s6-overlay
COPY rootfs /
RUN chmod a+x /etc/services.d/PanelSense/run
RUN chmod a+x /etc/services.d/PanelSense/finish

# Install dependencies
RUN apk add --no-cache \
    python3 \
    py3-pip

COPY senseapp /usr/src/app/senseapp
COPY requirements.txt /tmp/requirements.txt
COPY config.yaml /
ENV SENSE_APP=/usr/src/app/senseapp/sense.py
ENV HASS_WS_ADDRESS="ws://supervisor/core/websocket"

# Install python dependencies
RUN pip3 install --upgrade pip
RUN pip3 install --no-cache-dir -r /tmp/requirements.txt
