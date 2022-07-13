from requests.exceptions import ProxyError, ConnectionError, Timeout
import requests
import time


class Adapter:
    def __init__(self,
                 http=None, https=None, proxy_strategy=None,
                 retry_count=0, retry_time=None, timeout=None):
        """
        构造一个request adapter，并使用给定的代理策略、重试策略
        :param socks5: 启用socks5代理{host}:{port}。socks5只有在另外两项没有配置时才使用
        :param http: 启用http代理{host}:{port}
        :param https: 启用https代理{host}:{port}
        :param proxy_strategy: 代理策略。None=总是使用代理(除非没有配置)，int=仅尝试此次数的代理，失败就切换直连
        :param retry_count: 请求重试次数
        :param retry_time: 从第一次请求开始重试的最大时间，单位是秒
        :param timeout: 单次请求多久未响应视作超时，单位是秒
        """
        self.__session = requests.session()
        self.__session.headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_4) '
                          'AppleWebKit/537.36 (KHTML, like Gecko) '
                          'Chrome/80.0.3987.163 '
                          'Safari/537.36',
            'Accept-Encoding': ', '.join(('gzip', 'deflate')),
            'Accept': '*/*',
            'Connection': 'keep-alive',
        }

        self.__proxy_strategy = proxy_strategy
        self.__proxies = {}
        if https is not None:
            self.__proxies['https'] = https
        if http is not None:
            self.__proxies['http'] = http
        if len(self.__proxies) <= 0:
            self.__proxies = None

        self.__retry_count = retry_count
        self.__retry_time = retry_time
        self.__timeout = timeout

    def request(self, method, url, **kwargs):
        try_count = 0
        start_time = time.time()
        result = None
        error = None
        while result is None and (self.__retry_count is None or try_count <= self.__retry_count) and \
                (self.__retry_time is None or time.time() - start_time <= self.__retry_time):
            error = None
            try:
                if self.__proxies is not None and (self.__proxy_strategy is None or self.__proxy_strategy > try_count):
                    result = self.__session.request(method=method, url=url, timeout=self.__timeout,
                                                    proxies=self.__proxies, **kwargs)
                else:
                    result = self.__session.request(method=method, url=url, timeout=self.__timeout, **kwargs)
            except ConnectionError or Timeout as err:
                error = err
            try_count += 1

        return result, time.time() - start_time, try_count, error

    def req(self, method, url, **kwargs):
        result, _, _, error = self.request(method, url, **kwargs)
        if error is not None:
            raise error
        return result


if __name__ == '__main__':
    a = Adapter(http='http://127.0.0.1:1087', https='http://127.0.0.1:1087')
    r = a.req('GET', 'https://chan.sankakucomplex.com/post/show/16526513')
    print(r.text)
