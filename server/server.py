import asyncio
import time
from hashlib import sha256

from flask import Flask, json, request, g, abort, Response
import os
from uuid import uuid4
from threading import Thread
from queue import Queue
from typing import Final
import sys
from werkzeug.datastructures import FileStorage
import variables
from db import DBAggregator
import cryption_algorithms as ca
from uuid import uuid4


# ADD_NEW_THREAD_IN_QUEUE: Final[int] = 1

# threading_queue = Queue()
api = Flask(__name__)
api.config.from_object(__name__)
api.config.update(dict(
    DATABASE=os.path.join(api.root_path, 'base.db'),
    DATA_FOLDER='data_directory',
    SECRET_KEY='DEV_KEY',
    USERNAME='admin',
    PASSWORD='default'
))
api.config.from_envvar('FLASKR_SETTINGS', silent=True)
base = DBAggregator(api.config['DATABASE'])


@api.route('/user/login/', methods=['GET'])
def login():
    args = json.loads(request.json)
    try:
        return json.dumps(dict(index=base.check_user(args['login'], args['password'])))
    except KeyError:
        abort(400, 'Некорректный запрос')


@api.route('/user/invite/', methods=['GET'])
def invite_user():
    try:
        return json.dumps(base.invite_user(json.loads(request.json).get('user_id')))
    except KeyError:
        abort(400, 'Некорректный запрос')


@api.route('/user/reg', methods=['POST'])
def add_user():
    args = json.loads(request.json)
    try:
        return Response(status=base.add_user(args['login'], args['password'], args['invitation']))
    except KeyError:
        abort(400, 'Некорректный запрос')


@api.route('/key/asymmetric/', methods=['GET'])
def get_asymmetric_key():
    try:
        xtr = ca.XTR(variables.TEST, variables.TEST_PRECISION, variables.XTR_KEY_BIT_SIZE)
        open_key = xtr.generate_key()
        el_gamal_key = xtr.get_el_gamal_key()
        key_index = base.reg_el_gamal_key(open_key[0], el_gamal_key[0])
        return json.dumps(dict(p=open_key[0], q=open_key[1], tr=open_key[2], tr_k=el_gamal_key[1], key_index=key_index))
    except KeyError:
        abort(400, 'Некорректный запрос')


@api.route('/file', methods=['POST'])
def upload_file():
    FileStorage(request.files.get('file')).save(os.path.join(variables.DATA_DIR, request.form['name']))
    return 'OK'


@api.route('/file/info', methods=['POST'])
def upload_file_info():
    args = json.loads(request.json)
    try:
        base.upload_file(args['new_name'], args['old_name'], args['owner'], args['mode'], args['vector'])
        xtr_value = base.get_xtr_values(args['key_index'])
        sym_key = bytes(pair[0] ^ pair[1] for pair in zip(bytes(args['sym_key'].encode('utf-8')),
                                                          ca.XTR.get_symmetric_key_back(xtr_value[0], xtr_value[1],
                                                                                        args['tr_g_b'])))
        base.add_sym_key(sha256(args['new_name'].encode('utf-8')).hexdigest(), str(sym_key))
        return 'OK'
    except KeyError:
        abort(400, 'Некорректный запрос')


# @api.route('/keys/get_XTR_key/', methods=['GET'])
# def get_search_result():
#     return "OK"
    # db = get_db()
    # if (search_info := db.execute(f'select * from SearchRequest where search_id = "{search_id}"').fetchone()) is None:
    #     abort(400, 'Несуществующий ID')
    # if not search_info[-1]:
    #     return json.dumps(dict(finished=False))
    # if (paths := db.execute(f'select path from PathToFile where parent_index = {search_info[0]}').fetchall()) is None:
    #     return json.dumps(dict(finished=True, paths=[]))
    # return json.dumps(dict(finished=True, paths=list(path['path'] for path in paths)))


# @api.route('/searches/<search_id>', methods=['GET'])
# def get_search_result(search_id):
#     db = get_db()
#     if (search_info := db.execute(f'select * from SearchRequest where search_id = "{search_id}"').fetchone()) is None:
#         abort(400, 'Несуществующий ID')
#     if not search_info[-1]:
#         return json.dumps(dict(finished=False))
#     if (paths := db.execute(f'select path from PathToFile where parent_index = {search_info[0]}').fetchall()) is None:
#         return json.dumps(dict(finished=True, paths=[]))
#     return json.dumps(dict(finished=True, paths=list(path['path'] for path in paths)))
#
#
# @api.route('/search', methods=['POST'])
# def add_search():
#     search_id = uuid4()
#     db = get_db()
#     db.execute(f'insert into SearchRequest(search_id) values ("{search_id}")')
#     db.commit()
#     search_bd_id = db.execute(f'select data_index from SearchRequest where search_id="{search_id}"')\
#         .fetchone()['data_index']
#     threading_queue.put(ADD_NEW_THREAD_IN_QUEUE)
#     Thread(target=check_files, args=(threading_queue, api.config, search_bd_id, json.loads(request.get_json())
#                                      if request.is_json else {})).start()
#     return json.dumps(dict(search_id=search_id))
#
#
# @api.route('/init_db', methods=['GET'])
# def init_db_by_request():
#     init_db()
#     return "OK"


if __name__ == '__main__':
    api.run(debug=True, threaded=True)
