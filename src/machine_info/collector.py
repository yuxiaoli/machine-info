import datetime
import platform
import socket
import uuid
import os
import sys
import getpass
import psutil
import distro

# Helper to get current time in ISO 8601 format
def get_iso_now():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()

def get_meta():
    is_admin = False
    try:
        if platform.system() == 'Windows':
            import ctypes
            is_admin = ctypes.windll.shell32.IsUserAnAdmin() != 0
        else:
            is_admin = os.geteuid() == 0
    except Exception:
        pass

    return {
        "collected_at": get_iso_now(),
        "collector": {
            "name": "machine-info",
            "version": "0.1.0",
            "build": "dev",
            "commit": "unknown"
        },
        "collection_scope": {
            "tier": "safe",
            "includes": ["all"],
            "excludes": []
        },
        "execution_context": {
            "user": getpass.getuser(),
            "effective_user": getpass.getuser(), # simplification
            "is_admin": is_admin,
            "is_root": is_admin if platform.system() != 'Windows' else False,
            "permissions": []
        }
    }

def get_identity():
    boot_timestamp = psutil.boot_time()
    boot_time = datetime.datetime.fromtimestamp(boot_timestamp, datetime.timezone.utc)
    uptime_seconds = int((datetime.datetime.now(datetime.timezone.utc) - boot_time).total_seconds())

    # Try to get a stable machine ID
    machine_id_val = str(uuid.uuid4()) # Fallback
    try:
        if platform.system() == 'Linux':
            if os.path.exists('/etc/machine-id'):
                with open('/etc/machine-id', 'r') as f:
                    machine_id_val = f.read().strip()
            elif os.path.exists('/var/lib/dbus/machine-id'):
                with open('/var/lib/dbus/machine-id', 'r') as f:
                    machine_id_val = f.read().strip()
        elif platform.system() == 'Windows':
            import winreg
            try:
                with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Cryptography") as key:
                    machine_id_val, _ = winreg.QueryValueEx(key, "MachineGuid")
            except Exception:
                pass
        elif platform.system() == 'Darwin':
            # Could use ioreg, but keeping it simple for now
            pass
    except Exception:
        pass

    return {
        "machine": {
            "id": machine_id_val,
            "name": socket.gethostname(),
            "tags": [],
            "roles": []
        },
        "hostname": socket.getfqdn(),
        "domain": "", # hard to get reliably cross-platform without more heavy lifting
        "workgroup": "",
        "timezone": str(datetime.datetime.now(datetime.timezone.utc).astimezone().tzinfo),
        "locale": {
            "language": "en", # Simplified
            "encoding": "UTF-8"
        },
        "uptime_seconds": uptime_seconds,
        "boot_time": boot_time.isoformat(),
        "uuids": {
            "machine_id": machine_id_val,
            "product_uuid": "" # requires dmidecode or similar
        },
        "serials": {
            "system_serial": "" # requires root/admin usually
        }
    }

def get_os():
    system = platform.system().lower()
    os_info = {
        "family": "unknown",
        "name": "unknown",
        "version": "unknown",
        "build": "",
        "kernel": {
            "version": platform.release(),
            "release": platform.version(),
            "arch": platform.machine(),
            "boot_params": [],
            "modules": []
        }
    }

    if system == 'linux':
        os_info['family'] = 'linux'
        try:
            os_info['name'] = distro.name()
            os_info['version'] = distro.version()
            os_info['build'] = distro.build_number()
        except Exception:
            pass
    elif system == 'windows':
        os_info['family'] = 'windows'
        os_info['name'] = f"Windows {platform.release()}"
        os_info['version'] = platform.version()
        os_info['build'] = platform.version().split('.')[-1] if '.' in platform.version() else ""
    elif system == 'darwin':
        os_info['family'] = 'macos'
        os_info['name'] = f"macOS {platform.mac_ver()[0]}"
        os_info['version'] = platform.mac_ver()[0]
    
    return os_info

def get_hardware():
    # CPU
    cpu_info = {
        "model": platform.processor(),
        "vendor": "",
        "architecture": platform.machine(),
        "physical_cores": psutil.cpu_count(logical=False) or 1,
        "logical_cores": psutil.cpu_count(logical=True) or 1,
        "base_mhz": 0.0,
        "max_mhz": 0.0,
        "features": []
    }
    
    try:
        freq = psutil.cpu_freq()
        if freq:
            cpu_info['base_mhz'] = freq.current
            cpu_info['max_mhz'] = freq.max
    except Exception:
        pass

    # Memory
    mem = psutil.virtual_memory()
    swap = psutil.swap_memory()
    memory_info = {
        "total_bytes": mem.total,
        "swap_total_bytes": swap.total,
        "dimms": [] # Detailed DIMM info usually requires dmidecode/wmic
    }

    # Storage
    volumes = []
    filesystems = []
    
    try:
        partitions = psutil.disk_partitions(all=False)
        for p in partitions:
            fs_info = {
                "mount_point": p.mountpoint,
                "fs_type": p.fstype,
                "device": p.device,
                "options": p.opts.split(',') if p.opts else [],
                "total_bytes": 0,
                "used_bytes": 0
            }
            try:
                usage = psutil.disk_usage(p.mountpoint)
                fs_info['total_bytes'] = usage.total
                fs_info['used_bytes'] = usage.used
            except Exception:
                pass
            filesystems.append(fs_info)
            
            # Simple volume mapping (1:1 with mount for now)
            volumes.append({
                "name": os.path.basename(p.device) or p.device,
                "device": p.device,
                "type": "unknown", # difficult to determine without OS-specific tools
                "size_bytes": fs_info['total_bytes']
            })
    except Exception:
        pass

    return {
        "cpu": cpu_info,
        "memory": memory_info,
        "storage": {
            "volumes": volumes,
            "filesystems": filesystems,
            "encryption": [],
            "health": []
        },
        "gpu": {
            "present": False, # Requires external tools or libraries like GPUtil
            "adapters": []
        }
    }

def get_network():
    interfaces = []
    
    try:
        addrs = psutil.net_if_addrs()
        stats = psutil.net_if_stats()
        
        for name, addr_list in addrs.items():
            if_info = {
                "name": name,
                "type": "unknown",
                "mac": "",
                "mtu": 0,
                "link_speed_mbps": 0,
                "addresses": [],
                "dns": { "resolvers": [] }
            }
            
            # Stats
            if name in stats:
                st = stats[name]
                if_info['mtu'] = st.mtu
                if_info['link_speed_mbps'] = st.speed
                if st.isup:
                    pass # could add status field if schema allowed
            
            # Addresses
            for addr in addr_list:
                if addr.family == psutil.AF_LINK:
                    if_info['mac'] = addr.address
                elif addr.family == socket.AF_INET:
                    if_info['addresses'].append({
                        "address": addr.address,
                        "family": "ipv4",
                        "scope": "unknown", # difficult to determine scope portably
                        "source": "unknown"
                    })
                elif addr.family == socket.AF_INET6:
                    if_info['addresses'].append({
                        "address": addr.address.split('%')[0], # remove scope id if present
                        "family": "ipv6",
                        "scope": "unknown",
                        "source": "unknown"
                    })
            
            interfaces.append(if_info)
    except Exception:
        pass

    return {
        "interfaces": interfaces,
        "ip_addresses": [], # Optional aggregate, skipping for now
        "external_ips": [],
        "geoip": {},
        "dns": {
            "resolvers": [],
            "search_domains": []
        },
        "proxy": {},
        "routes": [],
        "firewall": { "enabled": False }, # Placeholder
        "vpn": { "active": False }
    }

def get_software():
    # Detect Python
    python_runtimes = [{
        "version": platform.python_version(),
        "path": sys.executable,
        "default": True
    }]
    
    # Simple env vars
    env_vars = {}
    if 'PATH' in os.environ:
        env_vars['PATH'] = os.environ['PATH']
    
    return {
        "env": env_vars,
        "package_managers": [],
        "installed_packages": [],
        "runtimes": {
            "python": python_runtimes,
            "nodejs": [],
            "java": [],
            "go": [],
            "rust": [],
            "dotnet": []
        },
        "cli_apps": [],
        "editors_and_ides": [],
        "container_runtimes": []
    }

def get_runtime():
    # Resource Usage
    cpu_load = psutil.getloadavg() if hasattr(psutil, "getloadavg") else (0.0, 0.0, 0.0)
    net_io = psutil.net_io_counters()
    disk_io = psutil.disk_io_counters()
    
    resource_usage = {
        "cpu_load_1m": cpu_load[0],
        "cpu_load_5m": cpu_load[1],
        "cpu_load_15m": cpu_load[2],
        "memory_used_bytes": psutil.virtual_memory().used,
        "disk_read_bytes": disk_io.read_bytes if disk_io else 0,
        "disk_write_bytes": disk_io.write_bytes if disk_io else 0,
        "net_rx_bytes": net_io.bytes_recv if net_io else 0,
        "net_tx_bytes": net_io.bytes_sent if net_io else 0
    }
    
    # Opened Ports (simplified)
    opened_ports = []
    try:
        # Requires root/admin for full list usually
        connections = psutil.net_connections(kind='inet')
        for conn in connections:
            if conn.status == 'LISTEN':
                opened_ports.append({
                    "protocol": "tcp" if conn.type == socket.SOCK_STREAM else "udp",
                    "address": conn.laddr.ip,
                    "port": conn.laddr.port,
                    "service": "unknown"
                })
                if len(opened_ports) > 50: # Limit output
                    break
    except Exception:
        pass
        
    return {
        "opened_ports": opened_ports,
        "services": [],
        "processes": [], # Too heavy to include all by default without filtering
        "resource_usage": resource_usage,
        "schedulers": [],
        "containers": [],
        "vms": []
    }

def get_security():
    users = []
    try:
        for u in psutil.users():
            users.append({
                "name": u.name,
                "uid": 0, # psutil doesn't always give uid
                "gid": 0,
                "home": "",
                "shell": "",
                "is_admin": False
            })
    except Exception:
        pass
        
    return {
        "users": users,
        "groups": [],
        "ssh": {
            "enabled": False, # Would need to check service status
            "config": "",
            "public_keys": []
        },
        "auth": {},
        "secure_boot": { "enabled": False, "status": "unknown" },
        "tpm": { "present": False },
        "av_edr": [],
        "vulnerability_scan": {}
    }

def collect_all():
    return {
        "meta": get_meta(),
        "identity": get_identity(),
        "os": get_os(),
        "hardware": get_hardware(),
        "network": get_network(),
        "software": get_software(),
        "runtime": get_runtime(),
        "security": get_security()
    }
