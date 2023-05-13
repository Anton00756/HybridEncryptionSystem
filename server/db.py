import sqlite3
import os
from typing import Optional


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
        """
        create table SystemUser (
    user_id integer primary key autoincrement,
    login varchar(40) not null,
    password varchar(64) not null,
    invitation varchar(36) DEFAULT(NULL)
);
        """
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

"""
self.cursor.execute(f'insert Student(Mail, Pass, PersonName) values("{mail}", "{hash_pass(password)}", '
                            f'"{name}")')
        self.cursor.connection.commit()
        
        
self.cursor.execute(f'select PersonID, UserType from LoginTable where Mail = "{mail}" and '
                            f'Pass = "{hash_pass(password)}"')
        answer = self.cursor.fetchone()
        if answer is not None:
            self.user_id = answer[0]
            if answer[1] == User.STUDENT:
                self.user_group = "Student"
            else:
                self.user_group = "Worker"
            return answer[1]
        return None
"""

