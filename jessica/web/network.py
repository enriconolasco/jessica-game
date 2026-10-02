"""Rede local explícita; não abre todas as interfaces nem aceita hosts arbitrários."""
from ipaddress import IPv4Address, IPv4Network
import socket

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
