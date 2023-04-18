import json

from module.adapter import Adapter

tag_types = {
    2: 'studio',     # 制作方信息
    3: 'copyright',  # 所属作品
    4: 'character',  # 角色
    1: 'artist',     # 画师
    8: 'medium',     # 图像信息
    9: 'meta',       # 元信息
    0: 'general',    # 内容
    5: 'genre'       # 特别内容
}

capiV2 = 'https://capi-v2.sankakucomplex.com'


def map_tag(tag):
    return {
        'type': tag_types[tag['type']],
        'name': tag['tagName'] if 'tagName' in tag else tag['name_en'] if 'name_en' in tag else tag['name'],
        'title': tag['name_ja'] if 'name_ja' in tag else None,
        'count': str(tag['post_count'])
    }


class BetaComplex:
    def __init__(self, adapter: Adapter, params: dict):
        self.__adapter = adapter
        self.__params = params

    def post(self, post_id):
        try:
            res, try_time, try_count, err = self.__adapter.request('get', '%s/posts?lang=en&page=1&limit=1&tags=id_range:%s' % (capiV2, post_id))
        except IOError as err:
            return None, 0, 0, str(err)
        if err is not None:
            return None, try_time, try_count, str(err)
        if res is None:
            return None, try_time, try_count, 'response is not exist'
        if res.status_code >= 300:
            return res.text, try_time, try_count, 'status code is %s' % (res.status_code,)
        res.encoding = 'utf-8'

        try:
            body = json.loads(res.text)
        except err:
            return None, try_time, try_count, str(err)
        if len(body) <= 0 or str(body[0]['id']) != str(post_id):
            return None, try_time, try_count, 'response json is empty, or is incorrect'

        tags = [map_tag(tag) for tag in body[0]['tags']]
        parent = [body[0]['parent_id']] if body[0]['parent_id'] is not None else []
        source = body[0]['source'] or None
        rating = body[0]['rating']
        md5 = body[0]['md5']

        if body[0]['has_children']:
            children, children_try_time, children_try_count, children_err = self.post_children(post_id)
            if children_err is not None:
                return None, children_try_time, children_try_count, children_err
        else:
            children = []

        if body[0]['in_visible_pool']:
            pools, pool_try_time, pool_try_count, pool_err = self.post_pool(post_id)
            if pool_err is not None:
                return None, pool_try_time, pool_try_count, pool_err
        else:
            pools = []

        result = {'tags': tags, 'pools': pools, 'parent': parent, 'children': children, 'source': source, 'rating': rating, 'md5': md5}

        return result, try_time, try_count, None

    def post_pool(self, post_id):
        try:
            res, try_time, try_count, err = self.__adapter.request('get', '%s/post/%s/pools?lang=en' % (capiV2, post_id))
        except IOError as err:
            return None, 0, 0, '[pool api]' + str(err)
        if err is not None:
            return None, try_time, try_count, '[pool api]' + str(err)
        if res is None:
            return None, try_time, try_count, '[pool api]response is not exist'
        if res.status_code >= 300:
            return res.text, try_time, try_count, '[pool api]status code is %s' % (res.status_code,)
        res.encoding = 'utf-8'

        try:
            body = json.loads(res.text)
        except err:
            return None, try_time, try_count, str(err)
        if len(body) <= 0:
            return [], try_time, try_count, None
        return [{'id': str(pool['id']), 'name': pool['name'], 'name_ja': pool['name_ja'] if 'name_ja' in pool else None} for pool in body], try_time, try_count, None

    def post_children(self, post_id):
        try:
            res, try_time, try_count, err = self.__adapter.request('get', '%s/posts?lang=en&page=1&limit=40&tags=parent:%s' % (capiV2, post_id))
        except IOError as err:
            return None, 0, 0, '[children api]' + str(err)
        if err is not None:
            return None, try_time, try_count, '[children api]' + str(err)
        if res is None:
            return None, try_time, try_count, '[children api]response is not exist'
        if res.status_code >= 300:
            return res.text, try_time, try_count, '[children api]status code is %s' % (res.status_code,)
        res.encoding = 'utf-8'

        try:
            body = json.loads(res.text)
        except err:
            return None, try_time, try_count, str(err)
        if len(body) <= 0:
            return [], try_time, try_count, None
        return [child['id'] for child in body], try_time, try_count, None


if __name__ == '__main__':
    a = Adapter(retry_count=1, timeout=15, http='127.0.0.1:1087')
    obj = BetaComplex(adapter=a, params={})
    r, t, c, e = obj.post(16820849)
    if e is not None:
        print('ERROR: ' + e)
    else:
        print(json.dumps(r))
    print('t=%.2f, c=%d' % (t, c))
