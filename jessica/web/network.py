"""Rede local explícita; não abre todas as interfaces nem aceita hosts arbitrários."""
from ipaddress import IPv4Address, IPv4Network
import socket
import re
from urllib.parse import urlsplit

PRIVATE_NETWORKS = tuple(IPv4Network(cidr) for cidr in ("10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16"))


def valid_host(value):
    try:
        address = IPv4Address(value)
    except (ValueError, TypeError) as exc:
        raise ValueError("Use um IPv4 local, não um domínio ou endereço público.") from exc
    if not address.is_loopback and not any(address in network for network in PRIVATE_NETWORKS):
        raise ValueError("Somente loopback ou IPv4 de rede privada são permitidos neste protótipo.")
    return str(address)


def local_addresses():
    entries = socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET, socket.SOCK_STREAM)
    addresses = set()
    for entry in entries:
        try:
            address = valid_host(entry[4][0])
            if not IPv4Address(address).is_loopback:
                addresses.add(address)
        except ValueError:
            continue
    return sorted(addresses, key=IPv4Address)


def choose_local_address():
    addresses = local_addresses()
    if not addresses:
        raise ValueError("Nenhum IPv4 privado encontrado. Conecte o PC a uma rede local e tente novamente.")
    print("Rede local experimental, sem HTTPS. Use somente Wi-Fi privado e confiável.")
    for index, address in enumerate(addresses, 1):
        print(f"{index}: {address}")
    choice = input("Escolha o endereço do PC [1]; 0 cancela: ").strip() or "1"
    if choice == "0":
        raise ValueError("Acesso de rede cancelado; nenhum servidor iniciado.")
    if not choice.isdecimal() or not 1 <= int(choice) <= len(addresses):
        raise ValueError("Escolha inválida; nenhum servidor iniciado.")
    return addresses[int(choice) - 1]


def allowed_hosts(host, port):
    names = [valid_host(host)]
    if host == "127.0.0.1":
        names.append("localhost")
    values = {f"{name}:{port}" for name in names}
    if port == 80:
        values.update(names)
    return values


def allowed_origins(host, port):
    names = [valid_host(host)]
    if host == "127.0.0.1":
        names.append("localhost")
    return [f"http://{name}{':' + str(port) if port != 80 else ''}" for name in names]


def external_origin(value):
    """Origem HTTPS explícita; nunca obtida de cabeçalhos encaminhados."""
    if not isinstance(value, str) or not value or any(c.isspace() or ord(c) < 33 or ord(c) > 126 for c in value):
        raise ValueError("Informe uma origem HTTPS ASCII, sem espaços.")
    try:
        parsed = urlsplit(value)
        host, port = parsed.hostname, parsed.port
        if (parsed.scheme != "https" or not host or parsed.username is not None
                or parsed.password is not None or parsed.path or "?" in value or "#" in value
                or len(host) > 253 or not re.fullmatch(r"[a-z0-9.-]+", host)):
            raise ValueError()
        for label in host.split("."):
            if not re.fullmatch(r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?", label):
                raise ValueError()
        if all(label.isdecimal() for label in host.split(".")):
            IPv4Address(host)
        if parsed.netloc.endswith(":") or port is not None and not 1 <= port <= 65535:
            raise ValueError()
    except ValueError as exc:
        raise ValueError("Use https://dominio[:porta], sem caminho, usuário, query ou fragmento.") from exc
    return f"https://{host}{':' + str(port) if port not in (None, 443) else ''}"


def configure_transport(httpd, origin=None):
    host, port = httpd.server_address[:2]
    if origin is not None:
        origin = external_origin(origin)
        if not IPv4Address(host).is_loopback:
            raise ValueError("Modo proxy HTTPS exige backend em loopback; não combine com LAN.")
        httpd.allowed_hosts = {urlsplit(origin).netloc}
        httpd.external_origin = origin
        httpd.notification_origins = [origin]
    else:
        httpd.allowed_hosts = allowed_hosts(host, port)
        httpd.external_origin = None
        httpd.notification_origins = allowed_origins(host, port)
