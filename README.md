# 可以使用`pip`安装本项目  

## 设置默认镜像源为[公司私服](http://livetest.bilibili.co/devpi/root/dev)  

```sh
cat > ~/.pip/pip.conf << EOF
[global]
index-url = http://livetest.bilibili.co/devpi/root/dev/+simple/
[install]
trusted-host = livetest.bilibili.co
EOF
```

`pip install invoker`  

## 或者安装时指定镜像源  

`pip install -i http://livetest.bilibili.co/devpi/root/dev --trusted-host livetest.bilibili.co invoker`
