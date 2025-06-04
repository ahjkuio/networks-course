import argparse
from ftplib import FTP
from pathlib import Path
import sys


def list_files(ftp: FTP):
    ftp.retrlines('NLST')


def upload_file(ftp: FTP, local_path: Path):
    if not local_path.exists():
        print(f'Файл {local_path} не найден')
        return
    with local_path.open('rb') as f:
        ftp.storbinary(f'STOR {local_path.name}', f)
    print('Файл загружен')


def download_file(ftp: FTP, remote_name: str, dest: Path):
    with dest.open('wb') as f:
        ftp.retrbinary(f'RETR {remote_name}', f.write)
    print('Файл скачан')


def main():
    parser = argparse.ArgumentParser(description='Простой FTP клиент')
    parser.add_argument('host')
    parser.add_argument('-P', '--port', type=int, default=21)
    parser.add_argument('-u', '--user', default='anonymous')
    parser.add_argument('-p', '--password', default='anonymous@')
    sub = parser.add_subparsers(dest='cmd', required=True)

    sub.add_parser('list')

    up = sub.add_parser('upload')
    up.add_argument('file', type=Path)

    dl = sub.add_parser('download')
    dl.add_argument('remote')
    dl.add_argument('dest', type=Path)

    args = parser.parse_args()
    ftp = FTP()
    ftp.connect(args.host, args.port)
    ftp.login(args.user, args.password)
    ftp.set_pasv(False)

    if args.cmd == 'list':
        list_files(ftp)
    elif args.cmd == 'upload':
        upload_file(ftp, args.file)
    elif args.cmd == 'download':
        download_file(ftp, args.remote, args.dest)

    ftp.quit()


if __name__ == '__main__':
    main() 