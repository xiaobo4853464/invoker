import copy
import gzip

import simplejson as json
from apscheduler.schedulers.background import BackgroundScheduler
from bitstring import BitArray
from google.protobuf import json_format
from invoker.conn.conns import livetest_redis_sync
from invoker.mitm_proxy import infoc_pb2
from mitmproxy import contentviews, http

cur_save_job = [{}]
red = livetest_redis_sync()


class Recordio:

    def deserialize_recordio(self, raw_data, offset, cooked_recordio):
        record = {}
        begin = offset
        magic_num = raw_data[offset:offset + 4].decode('ascii')
        record['magic_num'] = magic_num
        offset += 4
        meta_bit_and_size = raw_data[offset:offset + 4]
        meta_bit = int(BitArray(meta_bit_and_size).bin[0])
        if meta_bit == 1:
            size = BitArray(bin=BitArray(meta_bit_and_size).bin[1:]).int
            offset += 4
            offset += 1  # skip size_checksum
            name_size = raw_data[offset]
            offset += 1
            meta_name = raw_data[offset:offset + name_size].decode('ascii')
            offset += name_size
            more_meta_and_meta_size = raw_data[offset:offset + 4]
            offset += 4
            more_meta = int(BitArray(more_meta_and_meta_size).bin[0])
            if more_meta == 1:
                meta_size = BitArray(bin=BitArray(more_meta_and_meta_size).bin[1:]).int
                meta = raw_data[offset:offset + meta_size].decode('ascii')
                offset += meta_size
                record[meta_name] = meta
                name_size2 = raw_data[offset]
                offset += 1
                meta_name2 = raw_data[offset:offset + name_size2].decode('ascii')
                offset += name_size2
                more_meta_and_meta_size2 = raw_data[offset:offset + 4]
                offset += 4
                more_meta2 = int(BitArray(more_meta_and_meta_size2).bin[0])
                if more_meta2 == 1:
                    raise NameError('more_meta2 equal 1!')
                else:
                    meta_size2 = BitArray(bin=BitArray(more_meta_and_meta_size2).bin[1:]).int
                    meta2 = raw_data[offset:offset + meta_size2].decode('ascii')
                    offset += meta_size2
                    record[meta_name2] = meta2
                    payload_size = (begin + 4 + 4 + 1 + size) - offset
                    event_message = infoc_pb2.AppEvent()
                    event_message.ParseFromString(raw_data[offset:offset + payload_size])
                    jsonevent_message = json_format.MessageToDict(event_message)
                    record['payload'] = jsonevent_message
                    cooked_recordio.append(record)
                    offset += payload_size
                    if offset < len(raw_data):
                        self.deserialize_recordio(raw_data, offset, cooked_recordio)
                    return cooked_recordio
            else:
                raise NameError('more_meta not equal 1!')
        else:
            raise NameError('meta_bit not equal 1!')


class RecordioView(contentviews.View):
    name = 'bilibili-recordio'

    def __call__(self, data, **metadata) -> contentviews.TViewResult:
        if isinstance(metadata['message'], http.HTTPRequest):
            recordio = Recordio()
            cooked_recordio = recordio.deserialize_recordio(data, 0, [])
            return 'deserialized recordio', contentviews.format_text(
                json.dumps(cooked_recordio, indent=2))


class DataFlow:

    def response(self, flow: http.HTTPFlow) -> None:
        if 'dataflow.biliapi.com/log/pbmobile/' in flow.request.pretty_url:
            data = gzip.decompress(flow.request.raw_content)
            recordio = Recordio()
            cooked_recordio = recordio.deserialize_recordio(data, 0, [])
            for x in cooked_recordio:
                if x['payload']['appInfo']['deviceId'] in cur_save_job[0]:
                    red.zadd('mitm:log:' + cur_save_job[0][x['payload']['appInfo']['deviceId']],
                             {json.dumps(x, ensure_ascii=False): x['payload']['ctime']})
        if 'bilibili.co' in flow.request.host:
            rules = red.hgetall('mock_rule:' + flow.request.path.split('?')[0])
            if rules:
                raw_query = copy.deepcopy(flow.request.query)
                raw_query.update(copy.deepcopy(flow.request.urlencoded_form))
                req = dict(raw_query)
                resp = json.loads(flow.response.text)
                for k, v in rules.items():
                    if json.loads(v)['enable']:
                        print(flow.request.host + flow.request.path.split('?')[0] +
                              ' use rule id:' + k + '\nrule:' + v)
                        try:
                            space = {'req': req, 'resp': resp}
                            exec(json.loads(v)['code'], space)
                            resp = space['resp']
                        except Exception as e:
                            print(traceback.format_exc())
                flow.response.text = json.dumps(resp, ensure_ascii=False)


def load(l):
    contentviews.add(recordio_view)


def done():
    contentviews.remove(recordio_view)


def fetch_job():
    cur_save_job[0] = red.hgetall('mitm:cur_save_job')


recordio_view = RecordioView()
addons = [DataFlow()]
scheduler = BackgroundScheduler()
scheduler.add_job(fetch_job, 'interval', seconds=1)
scheduler.start()
