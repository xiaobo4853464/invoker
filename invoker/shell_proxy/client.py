import grpc

from invoker.shell_proxy import Proxy_pb2, Proxy_pb2_grpc


class ShellClient:

    def __init__(self, ip):
        channel = grpc.insecure_channel(ip + ':39999')
        self.stub = Proxy_pb2_grpc.ProxyStub(channel)

    def execute(self, *cmd):
        response = self.stub.Execute(Proxy_pb2.Cmd(cmd=cmd))
        return response.info, response.err
