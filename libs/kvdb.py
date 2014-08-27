# -*- coding: utf-8 -*-
import sae.kvdb


KVDB_KEYS = [
    'openid',
    'times',
    'success',
    'failure',
    'success_rate',
    'average_times',
    'digits',
    'tips',
]


class KVClient(sae.kvdb.KVClient):

    def set_multi(self, keys, values, key_prefix=''):
        if len(keys) == len(values):
            for key, value in zip(keys, values):
                self.set(key_prefix + '_' + key, value)