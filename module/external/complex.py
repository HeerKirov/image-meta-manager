import re
from bs4 import BeautifulSoup
from module.adapter import Adapter

tag_types = {
    'tag-type-studio': 'studio',        # 制作方信息
    'tag-type-copyright': 'copyright',  # 所属作品
    'tag-type-character': 'character',  # 角色
    'tag-type-artist': 'artist',        # 画师
    'tag-type-medium': 'medium',        # 图像信息
    'tag-type-meta': 'meta',            # 元信息
    'tag-type-general': 'general',      # 内容
    'tag-type-genre': 'genre'           # 特别内容
}

host = 'https://chan.sankakucomplex.com'


class Complex:
    def __init__(self, adapter: Adapter, params: dict):
        self.__adapter = adapter
        self.__params = params
        self.login()

    def login(self):
        username = self.__params['username'] if 'username' in self.__params else ''
        password = self.__params['password'] if 'password' in self.__params else ''
        if username and password:
            try:
                form = {'user[name]': username, 'user[password]': password}
                res, try_time, try_count, err = self.__adapter.request('post', '%s/user/authenticate' % (host,), data=form)
            except IOError as err:
                return None, 0, 0, str(err)
            if err is not None:
                print('Complex login failed.' + str(err))
            elif res is None:
                print('Complex login failed but response is not exist.')
            elif res.status_code >= 400:
                print('Complex login failed. status code is ' + str(res.status_code))
            else:
                print('Complex login succeed. username: ' + self.__params['username'])
                print()

    def post(self, post_id):
        try:
            res, try_time, try_count, err = self.__adapter.request('get', '%s/post/show/%s' % (host, post_id))
        except IOError as err:
            return None, 0, 0, str(err)
        if err is not None:
            return None, try_time, try_count, str(err)
        if res is None:
            return None, try_time, try_count, 'response is not exist'
        if res.status_code >= 300:
            return res.text, try_time, try_count, 'status code is %s' % (res.status_code,)
        res.encoding = 'utf-8'

        def find_tags():
            ret = []
            sidebar = soup.find('ul', id='tag-sidebar')
            for tag in sidebar.find_all('li'):
                href = tag.find('a', itemprop='keywords')
                tag_type = tag_types.get(tag['class'][0], None)
                tag_name = href.string
                tag_title = href.get('title', None)
                post_count = tag.find('span', class_='post-count').string
                ret.append({'type': tag_type, 'name': tag_name, 'title': tag_title, 'count': post_count})
            return ret

        def find_preview(div_id):
            ret = []
            preview = soup.find('div', id=div_id)
            if preview is not None:
                for span in preview.find_all('span'):
                    id_ = span['id'][1:]
                    ret.append(id_)
            return ret

        def find_pool():
            ret = []
            reg = re.compile('pool([0-9]+)')
            div_pools = soup.find_all('div', class_='status-notice', id=reg)
            for p in div_pools:
                matcher = reg.match(p['id'])
                pool_id = matcher.group(1)
                pool_name = p.find('a').string
                ret.append({'id': pool_id, 'name': pool_name})
            return ret

        try:
            soup = BeautifulSoup(res.text, 'html.parser')
            tags = find_tags()
            pools = find_pool()
            parent = find_preview('parent-preview')
            children = find_preview('child-preview')
        except Exception as err:
            return None, try_time, try_count, str(err)
        result = {'tags': tags, 'pools': pools, 'parent': parent, 'children': children}

        return result, try_time, try_count, None


if __name__ == '__main__':
    p = {'username': '', 'password': ''}
    obj = Complex(adapter=Adapter(retry_count=1, timeout=15, http='127.0.0.1:1087'), params=p)
    r, t, c, e = obj.post(31622750)
    if e is not None:
        print('ERROR: ' + e)
    else:
        import json
        print(json.dumps(r, indent=2, ensure_ascii=False))
    print('t=%.2f, c=%d' % (t, c))
