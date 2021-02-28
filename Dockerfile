FROM python

RUN apt install curl

RUN pip install -U -i http://livetest.bilibili.co/devpi/root/dev --trusted-host livetest.bilibili.co pip invoker devpi

RUN ln -sf /usr/share/zoneinfo/Asia/Shanghai /etc/localtime

CMD [ "python", "-V" ]
