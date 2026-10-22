FROM osrf/ros:noetic-desktop-full-focal@sha256:f138c82f326f179e8510eb03f40ee7ccaf16538e5577ab8550af74c4e12616de

SHELL ["/bin/bash", "-o", "pipefail", "-c"]

ARG DEBIAN_FRONTEND=noninteractive
ARG USER_UID=1000
ARG USER_GID=1000

ENV LANG=C.UTF-8 \
    LC_ALL=C.UTF-8 \
    ROS_DISTRO=noetic \
    ROS_MASTER_URI=http://localhost:11311 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

COPY docker/dependencies/apt.txt /tmp/uav-apt.txt
COPY docker/dependencies/python.txt /tmp/uav-python.txt

RUN printf '%s\n' \
      'Acquire::Retries "5";' \
      'Acquire::http::Timeout "60";' \
      'Acquire::https::Timeout "60";' \
      > /etc/apt/apt.conf.d/80-uav-network

RUN apt-get update \
    && xargs -r apt-get install -y --no-install-recommends < /tmp/uav-apt.txt \
    && rm -rf /var/lib/apt/lists/* /tmp/uav-apt.txt

RUN python3 -m pip install --retries 10 --timeout 60 --no-cache-dir --upgrade 'pip<25'
RUN python3 -m pip install --retries 10 --timeout 60 --no-cache-dir -r /tmp/uav-python.txt \
    && rm -rf /root/.cache/pip /tmp/uav-python.txt
RUN /opt/ros/noetic/lib/mavros/install_geographiclib_datasets.sh

RUN set -eux; \
    if ! getent group "${USER_GID}" >/dev/null; then groupadd --gid "${USER_GID}" ghj; fi; \
    if getent passwd "${USER_UID}" >/dev/null; then \
      existing_user=$(getent passwd "${USER_UID}" | cut -d: -f1); \
      usermod --login ghj --home /home/ghj --move-home "$existing_user"; \
      usermod --gid "${USER_GID}" ghj; \
    else \
      useradd --uid "${USER_UID}" --gid "${USER_GID}" --create-home --shell /bin/bash ghj; \
    fi; \
    printf '%s\n' 'ghj ALL=(root) NOPASSWD: /usr/bin/apt, /usr/bin/apt-get, /usr/bin/dpkg, /usr/bin/rosdep' > /etc/sudoers.d/ghj-dev; \
    chmod 0440 /etc/sudoers.d/ghj-dev; \
    install -d -o "${USER_UID}" -g "${USER_GID}" /home/ghj/catkin_ws /home/ghj/PX4-Autopilot /home/ghj/sitl_sim /home/ghj/.ros/log

COPY docker/scripts/*.sh /usr/local/bin/
COPY docker/entrypoint.sh /usr/local/bin/uav-sim-entrypoint
RUN chmod 0755 /usr/local/bin/*.sh /usr/local/bin/uav-sim-entrypoint

USER ghj
WORKDIR /home/ghj/catkin_ws
ENTRYPOINT ["/usr/local/bin/uav-sim-entrypoint"]
CMD ["sleep", "infinity"]
