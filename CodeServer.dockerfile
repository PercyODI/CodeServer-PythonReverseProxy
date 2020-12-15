FROM codercom/code-server:latest

USER root
RUN addgroup --gid 1024 codeservergroup

# RUN useradd -g 1024 codeserver
RUN usermod -a -G 1024 coder
USER coder
# WORKDIR /home/coder/project