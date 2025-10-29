FROM quay.io/astronomer/astro-runtime:10.8.0

USER root
ENV JAVA_HOME=/usr/lib/jvm/java-17-openjdk-amd64
ENV PATH="${JAVA_HOME}/bin:${PATH}"
USER astro