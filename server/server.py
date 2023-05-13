from flask import Flask, json, request, g, abort, Response
import os
from uuid import uuid4
from threading import Thread
from queue import Queue
from typing import Final
import sys
from db import DBAggregator
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


def db():
    if not hasattr(g, 'sqlite_db'):
        g.sqlite_db = DBAggregator(api.config['DATABASE'])
    return g.sqlite_db


@api.route('/user/login/', methods=['GET'])
def login():
    args = json.loads(request.json)
    try:
        return json.dumps(dict(index=db().check_user(args['login'], args['password'])))
    except KeyError:
        abort(400, 'Некорректный запрос')


@api.route('/user/reg', methods=['POST'])
def add_user():
    args = json.loads(request.json)
    try:
        return Response(status=db().add_user(args['login'], args['password'], args['invitation']))
    except KeyError:
        abort(400, 'Некорректный запрос')


@api.route('/keys/get_XTR_key/', methods=['GET'])
def get_search_result():
    # db().check_f()
    return "OK"
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
