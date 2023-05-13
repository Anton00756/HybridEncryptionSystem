drop table if exists SystemUser;
create table SystemUser (
    user_id integer primary key autoincrement,
    login varchar(40) not null,
    password varchar(64) not null,
    invitation varchar(36) DEFAULT(NULL)
);

drop table if exists UploadFile;
create table UploadFile (
    file_id integer primary key autoincrement,
    system_file_name varchar(40) not null,
    file_name varchar(256) not null,
    file_key varchar(256) not null,
    owner integer not null,
    upload_time timestamp DEFAULT(CURRENT_TIMESTAMP),
    FOREIGN KEY(owner) REFERENCES SystemUser(user_id)
);

drop table if exists DownloadFile;
create table DownloadFile (
    data_id integer primary key autoincrement,
    file_id integer not null,
    owner integer not null,
    download_file timestamp DEFAULT(CURRENT_TIMESTAMP),
    FOREIGN KEY(file_id) REFERENCES UploadFile(file_id),
    FOREIGN KEY(owner) REFERENCES SystemUser(user_id)
);