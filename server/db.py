import os
import sqlite3
from hashlib import sha256
from typing import Optional, Dict, Tuple, List
from uuid import uuid4


def conn(function):
    def f(self, *args, **kwargs):
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        self.cursor = connection.cursor()
        result = function(self, *args, **kwargs)
        connection.close()
        return result

    return f


class DBAggregator:
    def __init__(self, path: bytes):
        self.path = path
        if not os.path.exists(path):
            with open(path, 'w'):
                pass
            connection = sqlite3.connect(self.path)
            connection.row_factory = sqlite3.Row
            with open('init.sql', mode='r') as f:
                connection.cursor().executescript(f.read())
            connection.commit()
            connection.close()

        self.cursor: Optional[sqlite3.Cursor] = None

    @conn
    def check_user(self, login: str, password: str) -> Optional[int]:
        self.cursor.execute(f'select user_id from SystemUser where login = "{login}" and password = "{password}"')
        answer = self.cursor.fetchone()
        if answer is not None:
            return answer[0]
        return None

    @conn
    def add_user(self, login: str, password: str, invitation: str) -> int:
        self.cursor.execute(f'select user_id from SystemUser where login = "{login}"')
        if self.cursor.fetchone() is not None:
            return 201
        self.cursor.execute(f'select user_id from SystemUser where invitation = "{invitation}"')
        if self.cursor.fetchone() is None:
            return 202
        self.cursor.execute(f'insert into SystemUser(login, password) values("{login}", "{password}")')
        self.cursor.connection.commit()
        return 200

    @conn
    def invite_user(self, user_id: int) -> Dict:
        self.cursor.execute(f'select invitation from SystemUser where user_id = {user_id}')
        if (invitation := self.cursor.fetchone()[0]) is not None:
            return dict(invitation=invitation, generated=False)
        invitation = uuid4()
        self.cursor.execute(f'update SystemUser set invitation = "{invitation}" where user_id = {user_id}')
        self.cursor.connection.commit()
        return dict(invitation=invitation, generated=True)

    @conn
    def reg_el_gamal_key(self, p: int, k: int) -> int:
        self.cursor.execute(f'insert into AsymmetricKey(p_value, k_value) values("{p}", "{k}")')
        self.cursor.connection.commit()
        return self.cursor.execute(f'select max(key_id) from AsymmetricKey').fetchone()[0]

    @conn
    def upload_file(self, system_name: str, file_name: str, owner: int, crypt_mode: int, init_vector: str) -> None:
        self.cursor.execute(f'insert into UploadFile(system_file_name, file_name, owner, crypt_mode, init_vector)'
                            f'values("{system_name}", "{file_name}", {owner}, {crypt_mode}, "{init_vector}")')
        self.cursor.connection.commit()

    @conn
    def add_sym_key(self, name: str, key: str) -> None:
        self.cursor.execute(f'insert into SymmetricKey(file_hash, file_key) values("{name}", "{key}")')
        self.cursor.connection.commit()

    @conn
    def get_xtr_values(self, index: int) -> Tuple[int, int]:
        result = self.cursor.execute(f'select p_value, k_value from AsymmetricKey where key_id = {index}').fetchone()
        self.cursor.execute(f'delete from AsymmetricKey where key_id = {index}')
        self.cursor.connection.commit()
        return int(result[0]), int(result[1])

    @conn
    def get_server_files(self) -> List[Dict]:
        return [dict(row) for row in self.cursor.execute(f'select file_id, file_name, (select login from SystemUser '
                                                         f'where user_id = owner) as user, upload_time from '
                                                         f'UploadFile').fetchall()]

    @conn
    def delete_file(self, file_id: int) -> str:
        file_name = self.cursor.execute(f'select system_file_name from UploadFile where '
                                        f'file_id = {file_id}').fetchone()[0]
        self.cursor.execute(f'delete from UploadFile where file_id = {file_id}')
        self.cursor.connection.commit()
        file_hash = sha256(file_name.encode('utf-8')).hexdigest()
        self.cursor.execute(f'delete from SymmetricKey where file_hash = "{file_hash}"')
        self.cursor.connection.commit()
        return file_name

    @conn
    def get_file_name(self, file_id: int) -> str:
        return self.cursor.execute(f'select system_file_name from UploadFile where file_id = {file_id}').fetchone()[0]

    @conn
    def get_sym_key(self, file_id: int) -> str:
        file_hash = sha256(self.cursor.execute(f'select system_file_name from UploadFile where file_id = {file_id}')
                           .fetchone()[0].encode('utf-8')).hexdigest()
        return self.cursor.execute(f'select file_key from SymmetricKey where file_hash = "{file_hash}"').fetchone()[0]

    @conn
    def get_file_data(self, file_id: int) -> Tuple[int, str]:
        return tuple(self.cursor.execute(f'select crypt_mode, init_vector from UploadFile where '
                                         f'file_id = {file_id}').fetchone())
