FROM apache/hive:4.0.0

USER root

ADD https://jdbc.postgresql.org/download/postgresql-42.7.4.jar /opt/hive/lib/postgres.jar
RUN cp /opt/hadoop/share/hadoop/tools/lib/hadoop-aws-3.3.6.jar /opt/hive/lib/ \
    && cp /opt/hadoop/share/hadoop/tools/lib/aws-java-sdk-bundle-1.12.367.jar /opt/hive/lib/ \
    && chmod 0644 /opt/hive/lib/postgres.jar /opt/hive/lib/hadoop-aws-3.3.6.jar /opt/hive/lib/aws-java-sdk-bundle-1.12.367.jar

USER hive
