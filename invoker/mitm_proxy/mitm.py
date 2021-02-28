import asyncio
import logging
import threading

from invoker.mitm_proxy import addon
from mitmproxy import ctx, options, proxy
from mitmproxy.tools.web.master import WebMaster


class MitmWraper(object):
    mitmweb = None
    thread = None

    def loop_in_thread(self, loop, mitmweb):
        asyncio.set_event_loop(loop)
        mitmweb.run()

    def start(self):
        opts = options.Options(listen_host='0.0.0.0',
                               listen_port=8080,
                               confdir='~/.mitmproxy',
                               ssl_insecure=True)
        pconf = proxy.config.ProxyConfig(opts)
        self.mitmweb = WebMaster(opts)
        self.mitmweb.server = proxy.server.ProxyServer(pconf)
        self.mitmweb.addons.add(addon)
        ctx.options.web_host = '0.0.0.0'
        loop = asyncio.get_event_loop()
        self.thread = threading.Thread(target=self.loop_in_thread, args=(loop, self.mitmweb))

        try:
            self.thread.start()
        except KeyboardInterrupt:
            self.mitmweb.shutdown()


logging.disable(logging.INFO)
mitm_wraper = MitmWraper()
mitm_wraper.start()
