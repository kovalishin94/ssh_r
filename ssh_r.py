import socket
import select
import sys
import threading
import paramiko
import configparser


def handler(chan, host, port):
    sock = socket.socket()
    try:
        sock.connect((host, port))
    except Exception:
        return

    while True:
        r, w, x = select.select([sock, chan], [], [])
        if sock in r:
            data = sock.recv(1024)
            if len(data) == 0:
                break
            chan.send(data)
        if chan in r:
            data = chan.recv(1024)
            if len(data) == 0:
                break
            sock.send(data)
    chan.close()
    sock.close()


def reverse_forward_tunnel(server_port, remote_host, remote_port, transport):
    transport.request_port_forward("", server_port)
    while True:
        chan = transport.accept(1000)
        if chan is None:
            continue
        thr = threading.Thread(
            target=handler, args=(chan, remote_host, remote_port)
        )
        thr.setDaemon(True)
        thr.start()

def read_config(config_file: str):
    config = configparser.ConfigParser()
    config.read(config_file)
    connect_settings = {
        "hostname": config.get("settings", "host"),
        "port": config.get("settings", "ssh_port"),
        "username": config.get("settings", "username"),
        "key_filename": config.get("settings", "key_filename"),
        "passphrase": config.get("settings", "passphrase")
    }
    local_port = config.get("settings", "local_port")
    remote_port = config.get("settings", "remote_port")
        
    return connect_settings, local_port, remote_port

if __name__ == "__main__":
    connect_settings, local_port, remote_port = read_config("config.ini")

    client = paramiko.SSHClient()
    client.load_system_host_keys()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    try:
        client.connect(**connect_settings)
    except Exception as e:
        print(f"Failed to connect {e}")
        sys.exit(1)

    try:
        reverse_forward_tunnel(
            remote_port, "localhost", local_port, client.get_transport()
        )
    except KeyboardInterrupt:
        print("C-c: Port forwarding stopped.")
        sys.exit(0)