from hashlib import sha256
from flask import Flask, json, request, g, abort, Response, send_file
import os
from werkzeug.datastructures import FileStorage
import variables
from db import DBAggregator
import cryption_algorithms as ca
from client.file_manager import convert_bytes, convert_str


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
    xtr = ca.XTR(variables.TEST, variables.TEST_PRECISION, variables.XTR_KEY_BIT_SIZE)
    open_key = xtr.generate_key()
    el_gamal_key = xtr.get_el_gamal_key()
    key_index = base.reg_el_gamal_key(open_key[0], el_gamal_key[0])
    return json.dumps(dict(p=open_key[0], q=open_key[1], tr=open_key[2], tr_k=el_gamal_key[1], key_index=key_index))


@api.route('/file', methods=['POST'])
def upload_file():
    try:
        FileStorage(request.files.get('file')).save(os.path.join(variables.DATA_DIR, request.form['name']))
        return 'OK'
    except KeyError:
        abort(400, 'Некорректный запрос')


@api.route('/file/info', methods=['POST'])
def upload_file_info():
    args = json.loads(request.json)
    try:
        base.upload_file(args['new_name'], args['old_name'], args['owner'], args['mode'],
                         "" if args['vector'] is None else args['vector'])
        xtr_value = base.get_xtr_values(args['key_index'])
        sym_key = bytes(pair[0] ^ pair[1] for pair in zip(convert_str(args['sym_key']),
                                                          ca.XTR.get_symmetric_key_back(xtr_value[0], xtr_value[1],
                                                                                        args['tr_g_b'])))
        base.add_sym_key(sha256(args['new_name'].encode('utf-8')).hexdigest(), convert_bytes(sym_key))
        return 'OK'
    except KeyError:
        abort(400, 'Некорректный запрос')


@api.route('/files/', methods=['GET'])
def get_server_files():
    return json.dumps(base.get_server_files())


@api.route('/file/<file_id>', methods=['GET'])
def download_file(file_id: int):
    try:
        return send_file(os.path.join(variables.DATA_DIR, base.get_file_name(file_id)), as_attachment=True)
    except FileNotFoundError:
        abort(400, 'Некорректный запрос')


@api.route('/file/info/', methods=['GET'])
def download_file_info():
    args = json.loads(request.json)
    try:
        sym_key = base.get_sym_key(args['file_id'])
        trace, key = ca.XTR.get_symmetric_key(args['p'], args['q'], args['tr'], args['tr_k'])
        key = bytes(pair[0] ^ pair[1] for pair in zip(key, convert_str(sym_key)))
        file_data = base.get_file_data(args['file_id'])
        return json.dumps(dict(key=convert_bytes(key), tr=trace, mode=file_data[0], init_vector=file_data[1]))
    except KeyError:
        abort(400, 'Некорректный запрос')


@api.route('/file/delete/<file_id>', methods=['DELETE'])
def delete_file(file_id: int):
    try:
        file_name = base.delete_file(file_id)
        os.remove(os.path.join(variables.DATA_DIR, file_name))
        return 'OK'
    except FileNotFoundError:
        abort(400, 'Некорректный запрос')


if __name__ == '__main__':
    api.run(debug=True, threaded=True)
