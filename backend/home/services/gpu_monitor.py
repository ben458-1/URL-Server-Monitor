import paramiko
import asyncio
import logging
import os
import tempfile
import json
from typing import Dict, Set
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from ..models.database_models import GPUMetricsModel, PidMetricsModel, GPUServerModel
from ..services.alert_service import alert_service

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Inline remote monitoring script (executed on GPU servers via SSH)
REMOTE_MONITOR_SCRIPT_INLINE = '''#!/usr/bin/env python3
import json, sys, time, subprocess
try:
    import pynvml
    from pynvml import *
    import psutil
except ImportError as e:
    print(json.dumps({"error": f"Missing module: {e}. Run: pip install nvidia-ml-py3 psutil"}))
    sys.exit(1)

def safe_int(v, d=0):
    try: return int(v) if v is not None else d
    except: return d

def get_pss_kb(pid):
    try:
        with open(f"/proc/{pid}/smaps_rollup") as f:
            for line in f:
                if line.startswith("Pss:"): return safe_int(line.split()[1])
    except: pass
    return None

def collect_gpu_metrics():
    result = {"host": {"memory_total_mib": 0, "memory_used_mib": 0, "memory_free_mib": 0,
                       "disk_total_mib": 0, "disk_used_mib": 0, "disk_free_mib": 0, "disk_usage_pct": 0},
              "gpus": [], "error": None, "timestamp": time.time()}
    try:
        nvmlInit()
        vm = psutil.virtual_memory()
        result["host"]["memory_total_mib"] = int(vm.total / 1048576)
        result["host"]["memory_used_mib"] = int(vm.used / 1048576)
        result["host"]["memory_free_mib"] = int(vm.available / 1048576)
        
        try:
            df_cmd = "df -h -x tmpfs -x devtmpfs -x overlay -x nfs -x cifs --total | grep total"
            df_result = subprocess.run(df_cmd, shell=True, capture_output=True, text=True, timeout=5)
            if df_result.returncode == 0 and df_result.stdout.strip():
                parts = df_result.stdout.strip().split()
                if len(parts) >= 5:
                    def parse_size(s):
                        s = s.strip()
                        if s[-1] == 'T': return int(float(s[:-1]) * 1048576)
                        elif s[-1] == 'G': return int(float(s[:-1]) * 1024)
                        elif s[-1] == 'M': return int(float(s[:-1]))
                        elif s[-1] == 'K': return int(float(s[:-1]) / 1024)
                        return int(s)
                    result["host"]["disk_total_mib"] = parse_size(parts[1])
                    result["host"]["disk_used_mib"] = parse_size(parts[2])
                    result["host"]["disk_free_mib"] = parse_size(parts[3])
                    result["host"]["disk_usage_pct"] = int(parts[4].rstrip('%'))
                else: raise Exception("df parse failed")
            else: raise Exception("df command failed")
        except:
            disk = psutil.disk_usage("/")
            result["host"]["disk_total_mib"] = int(disk.total / 1048576)
            result["host"]["disk_used_mib"] = int(disk.used / 1048576)
            result["host"]["disk_free_mib"] = int(disk.free / 1048576)
            result["host"]["disk_usage_pct"] = int(disk.percent)
        
        for i in range(nvmlDeviceGetCount()):
            h = nvmlDeviceGetHandleByIndex(i)
            name_raw = nvmlDeviceGetName(h)
            name = name_raw.decode() if isinstance(name_raw, bytes) else str(name_raw)
            uuid_raw = nvmlDeviceGetUUID(h)
            uuid = uuid_raw.decode() if isinstance(uuid_raw, bytes) else str(uuid_raw)
            mem = nvmlDeviceGetMemoryInfo(h)
            try: util = nvmlDeviceGetUtilizationRates(h); gpu_util, mem_util = safe_int(util.gpu), safe_int(util.memory)
            except: gpu_util, mem_util = 0, 0
            
            gpu_entry = {"gpu_index": i, "gpu_uuid": uuid, "gpu_name": name,
                        "gpu_memory_total_mib": int(mem.total / 1048576),
                        "gpu_memory_used_mib": int(mem.used / 1048576),
                        "gpu_memory_free_mib": int(mem.free / 1048576),
                        "gpu_utilization_pct": gpu_util, "gpu_mem_utilization_pct": mem_util,
                        "per_gpu_aggregates": {"process_ram_pss_mib": 0, "process_ram_rss_mib": 0},
                        "processes": []}
            
            procs = []
            try: procs += list(nvmlDeviceGetComputeRunningProcesses_v3(h))
            except:
                try: procs += list(nvmlDeviceGetComputeRunningProcesses(h))
                except: pass
            try: procs += list(nvmlDeviceGetGraphicsRunningProcesses_v3(h))
            except:
                try: procs += list(nvmlDeviceGetGraphicsRunningProcesses(h))
                except: pass
            
            total_pss_kb, total_rss_kb = 0, 0
            for pr in procs:
                pid = pr.pid
                used_gpu_mem_b = getattr(pr, "usedGpuMemory", 0) or 0
                proc_entry = {"pid": pid, "process_name": "N/A", "cmd": "N/A",
                             "used_mem_mib": int(used_gpu_mem_b / 1048576),
                             "process_ram_pss_mib": 0, "process_ram_rss_mib": 0}
                try:
                    p = psutil.Process(pid)
                    proc_entry["process_name"] = p.name()
                    try: proc_entry["cmd"] = " ".join(p.cmdline()) or p.exe()
                    except: proc_entry["cmd"] = proc_entry["process_name"]
                    try:
                        rss_bytes = p.memory_info().rss
                        proc_entry["process_ram_rss_mib"] = int(rss_bytes / 1048576)
                        total_rss_kb += int(rss_bytes / 1024)
                        pss_kb = get_pss_kb(pid)
                        if pss_kb:
                            proc_entry["process_ram_pss_mib"] = int(pss_kb / 1024)
                            total_pss_kb += pss_kb
                    except: pass
                except: pass
                gpu_entry["processes"].append(proc_entry)
            
            gpu_entry["per_gpu_aggregates"]["process_ram_pss_mib"] = int(total_pss_kb / 1024)
            gpu_entry["per_gpu_aggregates"]["process_ram_rss_mib"] = int(total_rss_kb / 1024)
            result["gpus"].append(gpu_entry)
        nvmlShutdown()
    except Exception as e:
        result["error"] = f"Error: {e}"
    return result

if __name__ == "__main__":
    print(json.dumps(collect_gpu_metrics(), indent=2))
'''


def run_command(ssh, cmd, timeout=10):
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode().strip()
    err = stderr.read().decode().strip()
    return out, err

def gather_host_gpu_info_v2_pynvml(host: str, username: str, key_path: str, key_passphrase: str = None, 
                          port: int = 22) -> Dict:
    """
    New implementation using pynvml + psutil on remote server
    This provides more accurate GPU metrics, proper RAM attribution (PSS), and disk I/O counters
    """
    result = {"host": host, "gpus": [], "error": None}
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    # Get SSH timeout from environment
    ssh_timeout = int(os.getenv('SSH_TIMEOUT_SECONDS', '30'))
    
    try:
        # Load RSA key from file path
        logger.debug(f"Loading RSA key from file: {key_path}")
        
        try:
            if key_passphrase and key_passphrase not in ['None', None, '']:
                logger.debug("Using RSA key with passphrase")
                pkey = paramiko.RSAKey.from_private_key_file(key_path, password=key_passphrase)
            else:
                logger.debug("Using RSA key without passphrase")
                pkey = paramiko.RSAKey.from_private_key_file(key_path)
        except Exception as e:
            result["error"] = f"Failed to load key: {e}"
            logger.error(f"RSA key loading failed from {key_path}: {e}")
            return result
        
        logger.debug(f"Connecting to {host}:{port} (timeout: {ssh_timeout}s)")
        ssh.connect(hostname=host, username=username, pkey=pkey, port=port, timeout=ssh_timeout)
        logger.debug(f"SSH connection established to {host}")
        
        # Create inline script on remote server
        remote_script_path = "/tmp/gpu_monitor_inline.py"
        
        logger.debug(f"Creating inline monitoring script on {host}")
        try:
            # Write script content directly via SSH
            script_content = REMOTE_MONITOR_SCRIPT_INLINE
            create_script_cmd = f"cat > {remote_script_path} << 'EOFSCRIPT'\n{script_content}\nEOFSCRIPT\nchmod +x {remote_script_path}"
            stdin, stdout, stderr = ssh.exec_command(create_script_cmd, timeout=10)
            stderr_output = stderr.read().decode()
            if stderr_output and "cannot create" in stderr_output.lower():
                result["error"] = f"Failed to create script: {stderr_output}"
                logger.error(f"Script creation failed: {stderr_output}")
                ssh.close()
                return result
            logger.debug(f"✓ Monitoring script created successfully")
        except Exception as e:
            result["error"] = f"Failed to create monitoring script: {e}"
            logger.error(f"Failed to create script: {e}")
            ssh.close()
            return result
        
        # Check if pynvml and psutil are installed
        logger.debug("Checking for required Python packages...")
        check_cmd = "python3 -c 'import pynvml, psutil' 2>&1"
        check_out, check_err = run_command(ssh, check_cmd)
        
        if "ModuleNotFoundError" in check_out or "ModuleNotFoundError" in check_err or "No module named" in check_out:
            logger.warning(f"⚠️  Required packages not installed on {host}")
            logger.info(f"   Attempting to install nvidia-ml-py3 and psutil...")
            
            # Try to install packages with --user first
            install_cmd = "python3 -m pip install --user nvidia-ml-py3 psutil 2>&1"
            install_out, install_err = run_command(ssh, install_cmd, timeout=60)
            
            # If externally-managed-environment error, try with --break-system-packages
            if "externally-managed-environment" in install_out or "externally-managed-environment" in install_err:
                logger.info(f"   Retrying with --break-system-packages flag (safe for these packages)...")
                install_cmd = "python3 -m pip install --break-system-packages nvidia-ml-py3 psutil 2>&1"
                install_out, install_err = run_command(ssh, install_cmd, timeout=60)
            
            if "Successfully installed" in install_out or "Requirement already satisfied" in install_out:
                logger.info(f"✓ Packages installed successfully on {host}")
            else:
                result["error"] = f"Failed to install required packages. Please manually run: pip install --break-system-packages nvidia-ml-py3 psutil"
                logger.error(f"Package installation failed: {install_out}")
                ssh.close()
                return result
        else:
            logger.debug("✓ Required packages are installed")
        
        # Run the monitoring script
        logger.info(f"Collecting GPU metrics from {host} using pynvml...")
        monitor_cmd = f"python3 {remote_script_path}"
        metrics_json, metrics_err = run_command(ssh, monitor_cmd, timeout=60)
        
        if not metrics_json or metrics_err:
            result["error"] = f"Failed to run monitoring script: {metrics_err}"
            logger.error(f"Monitoring script error: {metrics_err}")
            ssh.close()
            return result
        
        # Parse JSON output
        try:
            metrics_data = json.loads(metrics_json)
        except json.JSONDecodeError as e:
            result["error"] = f"Failed to parse JSON output: {e}"
            logger.error(f"JSON parse error. Output: {metrics_json[:500]}")
            ssh.close()
            return result
        
        if metrics_data.get("error"):
            result["error"] = metrics_data["error"]
            logger.error(f"Remote monitoring error: {metrics_data['error']}")
            ssh.close()
            return result
        
        # Extract host-level metrics
        host_metrics = metrics_data.get("host", {})
        host_mem_total = host_metrics.get("memory_total_mib", 0)
        host_mem_used = host_metrics.get("memory_used_mib", 0)
        host_mem_free = host_metrics.get("memory_free_mib", 0)
        host_disk_total = host_metrics.get("disk_total_mib", 0)
        host_disk_used = host_metrics.get("disk_used_mib", 0)
        host_disk_free = host_metrics.get("disk_free_mib", 0)
        host_disk_usage_pct = host_metrics.get("disk_usage_pct", 0)
        
        logger.info(f"✓ Host metrics: RAM {host_mem_used}/{host_mem_total} MiB, Disk {host_disk_used}/{host_disk_total} MiB ({host_disk_usage_pct}%)")
        
        # Process GPU data
        for gpu_data in metrics_data.get("gpus", []):
            gpu_index = gpu_data.get("gpu_index", 0)
            gpu_name = gpu_data.get("gpu_name", "Unknown")
            
            # Get per-GPU aggregates
            aggregates = gpu_data.get("per_gpu_aggregates", {})
            per_gpu_ram_pss = aggregates.get("process_ram_pss_mib", 0)
            per_gpu_ram_rss = aggregates.get("process_ram_rss_mib", 0)
            
            # Use PSS if available, otherwise fall back to RSS
            per_gpu_ram = per_gpu_ram_pss if per_gpu_ram_pss > 0 else per_gpu_ram_rss
            
            logger.info(f"GPU {gpu_index} ({gpu_name}): {len(gpu_data.get('processes', []))} processes, "
                       f"{per_gpu_ram:.1f} MiB RAM (PSS), "
                       f"{gpu_data.get('gpu_utilization_pct', 0)}% util")
            
            # Format processes (no disk I/O per process)
            processes = []
            for proc in gpu_data.get("processes", []):
                # Use PSS if available, otherwise RSS
                proc_ram = proc.get("process_ram_pss_mib", 0)
                if proc_ram == 0:
                    proc_ram = proc.get("process_ram_rss_mib", 0)
                
                processes.append({
                    "pid": proc.get("pid", 0),
                    "process_name": proc.get("process_name", "N/A"),
                    "cmd": proc.get("cmd", "N/A"),
                    "used_mem_mib": proc.get("used_mem_mib", 0),  # GPU memory
                    "process_ram_mib": proc_ram,  # Host RAM (PSS preferred)
                })
            
            # Build GPU entry with host metrics (disk is host-level only, not per-GPU)
            gpu_entry = {
                "gpu_index": gpu_index,
                "gpu_name": gpu_name,
                "gpu_memory_total_mib": gpu_data.get("gpu_memory_total_mib", 0),
                "gpu_memory_used_mib": gpu_data.get("gpu_memory_used_mib", 0),
                "gpu_memory_free_mib": gpu_data.get("gpu_memory_free_mib", 0),
                "gpu_utilization_pct": gpu_data.get("gpu_utilization_pct", 0),
                # Host metrics (shared across all GPUs)
                "host_memory_total_mib": host_mem_total,
                "host_memory_used_mib": host_mem_used,  # System-wide RAM used
                "host_memory_free_mib": host_mem_free,  # System-wide RAM free
                "host_disk_total_mib": host_disk_total,  # System-wide disk total
                "host_disk_used_mib": host_disk_used,  # System-wide disk used
                "host_disk_free_mib": host_disk_free,  # System-wide disk free
                "host_disk_usage_pct": host_disk_usage_pct,  # System-wide disk usage %
                # Per-GPU process aggregates (RAM only)
                "per_gpu_process_ram_mib": per_gpu_ram,
                "processes": processes
            }
            
            result["gpus"].append(gpu_entry)
        
        logger.info(f"✓ Successfully collected metrics for {len(result['gpus'])} GPUs from {host}")
        
        ssh.close()
        
    except TimeoutError as e:
        result["error"] = f"Connection timeout: {e}"
        logger.error(f"Timeout connecting to {host}:{port} - Check network connectivity and firewall rules")
        try:
            ssh.close()
        except:
            pass
    except Exception as e:
        result["error"] = f"Error: {e}"
        logger.error(f"Exception in gather_host_gpu_info_v2_pynvml: {e}", exc_info=True)
        try:
            ssh.close()
        except:
            pass
    
    return result


def gather_host_gpu_info(host: str, username: str, key_path: str, key_passphrase: str = None, 
                          port: int = 22) -> Dict:
    """
    Collect GPU metrics using pynvml + psutil on remote server
    """
    return gather_host_gpu_info_v2_pynvml(host, username, key_path, key_passphrase, port)


class GPUMonitor:
    def __init__(self):
        self.scheduler = AsyncIOScheduler()
        self.is_running = False
        self.websocket_connections: Set = set()
        self.monitoring_interval = int(os.getenv('GPU_MONITORING_INTERVAL_SECONDS', '60'))
        self.ssh_timeout = int(os.getenv('SSH_TIMEOUT_SECONDS', '30'))
    
    def add_websocket(self, websocket):
        self.websocket_connections.add(websocket)
    
    def remove_websocket(self, websocket):
        self.websocket_connections.discard(websocket)
    
    async def broadcast_metrics(self, metrics_data):
        dead_connections = set()
        for websocket in self.websocket_connections:
            try:
                await websocket.send_json({
                    "type": "gpu_metrics_update",
                    "data": metrics_data
                })
            except Exception as e:
                logger.error(f"WebSocket error: {e}")
                dead_connections.add(websocket)
        self.websocket_connections -= dead_connections
    
    async def collect_and_store_metrics(self):
        try:
            logger.info("=== Starting GPU metrics collection cycle ===")
            
            # Get all GPU servers
            gpu_servers = GPUServerModel.get_all_with_keys()
            logger.info(f"Found {len(gpu_servers)} GPU servers in database")
            
            if not gpu_servers:
                logger.warning("No GPU servers found in database")
                return
            
            all_metrics = []
            
            for server in gpu_servers:
                logger.info(f"Processing server: {server.get('server_name', 'Unknown')}")
                try:
                    # Get server with DECRYPTED RSA key content
                    server_detail = GPUServerModel.get_by_id(server['id'], decrypt_keys=True)
                    if not server_detail:
                        logger.warning(f"Server {server['server_name']} not found")
                        continue
                    
                    # Get decrypted RSA key content
                    rsa_key_content = server_detail.get('rsa_key')
                    if not rsa_key_content:
                        logger.error(f"No RSA key for {server['server_name']}")
                        continue
                    
                    logger.info(f"Connecting to {server_detail['server_ip']} as {server_detail['username']}")
                    logger.debug(f"RSA key decrypted, creating temporary file...")
                    
                    # Create temporary file with decrypted RSA key content
                    temp_key_file = None
                    try:
                        # Create temp file (will be deleted after use)
                        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='_rsa_key') as temp_file:
                            temp_file.write(rsa_key_content)
                            temp_key_file = temp_file.name
                        
                        logger.debug(f"Temporary RSA key file created: {temp_key_file}")
                        
                        # Pass temp file path to gather_host_gpu_info (same as gpu.py)
                        result = await asyncio.to_thread(
                            gather_host_gpu_info,
                            server_detail['server_ip'],
                            server_detail['username'],
                            temp_key_file,  # Pass temporary file path
                            server_detail.get('rsa_key_passphrase'),
                            server_detail['port']
                        )
                        
                        if result.get('error'):
                            logger.error(f"Error from {server['server_name']}: {result['error']}")
                            continue
                        
                        logger.info(f"Successfully collected data from {server['server_name']}, found {len(result.get('gpus', []))} GPUs")
                        
                        # Store in database
                        for gpu_data in result.get('gpus', []):
                            logger.info(f"Storing metrics for GPU {gpu_data['gpu_index']} on {result['host']}")
                            
                            # Get processes (no disk I/O rate calculation needed)
                            processes = gpu_data.get('processes', [])
                            
                            metric_data = {
                                'host': result['host'],
                                'gpu_index': gpu_data['gpu_index'],
                                'gpu_name': server_detail.get('gpu_name') or gpu_data['gpu_name'],
                                'gpu_memory_total_mib': gpu_data['gpu_memory_total_mib'],
                                'gpu_memory_used_mib': gpu_data['gpu_memory_used_mib'],
                                'gpu_memory_free_mib': gpu_data['gpu_memory_free_mib'],
                                'gpu_utilization_pct': gpu_data['gpu_utilization_pct'],
                                'host_memory_total_mib': gpu_data['host_memory_total_mib'],
                                'host_memory_used_mib': gpu_data['host_memory_used_mib'],
                                'host_memory_free_mib': gpu_data['host_memory_free_mib'],
                                'host_disk_total_mib': gpu_data.get('host_disk_total_mib', 0),
                                'host_disk_used_mib': gpu_data.get('host_disk_used_mib', 0),
                                'host_disk_free_mib': gpu_data.get('host_disk_free_mib', 0),
                                'host_disk_usage_pct': gpu_data.get('host_disk_usage_pct', 0)
                            }
                            
                            try:
                                # Insert GPU metrics
                                gpu_metrics_id = GPUMetricsModel.insert_metric(metric_data)
                                logger.info(f"✓ Inserted gpu_metrics record with ID: {gpu_metrics_id}")
                                
                                if not gpu_metrics_id:
                                    logger.error("Failed to get gpu_metrics_id after insert!")
                                    continue
                                
                                # Store processes (no disk I/O)
                                if processes:
                                    process_count = len(processes)
                                    logger.info(f"Storing {process_count} processes for GPU {gpu_data['gpu_index']}")
                                    
                                    process_data_list = [{
                                        'gpu_metrics_id': gpu_metrics_id,
                                        'pid': proc['pid'],
                                        'process_name': proc['process_name'],
                                        'cmd': proc['cmd'],
                                        'used_mem_mib': proc['used_mem_mib'],
                                        'process_ram_mib': proc.get('process_ram_mib', 0),
                                    } for proc in processes]
                                    
                                    inserted_count = PidMetricsModel.insert_processes_batch(process_data_list)
                                    logger.info(f"✓ Inserted {inserted_count} pid_metrics records (expected {process_count})")
                                    
                                    # Verify insertion
                                    if inserted_count != process_count:
                                        logger.warning(f"Mismatch: Expected {process_count}, inserted {inserted_count}")
                                else:
                                    logger.info(f"No processes running on GPU {gpu_data['gpu_index']}")
                                
                                # Add processes for WebSocket broadcast
                                all_metrics.append({**metric_data, 'processes': processes})
                                logger.info(f"✓ Successfully stored all metrics for GPU {gpu_data['gpu_index']}")
                                
                                # Check and send alerts if GPU memory usage exceeds threshold
                                try:
                                    if server_detail.get('usage_limit') and server_detail.get('alert_emails'):
                                        alert_service.check_and_send_alerts(
                                            server_id=server_detail['id'],
                                            server_name=server_detail['server_name'],
                                            server_ip=server_detail['server_ip'],
                                            gpu_index=gpu_data['gpu_index'],
                                            gpu_name=gpu_data['gpu_name'],
                                            gpu_memory_used_mib=gpu_data['gpu_memory_used_mib'],
                                            gpu_memory_total_mib=gpu_data['gpu_memory_total_mib'],
                                            usage_limit=server_detail['usage_limit'],
                                            alert_emails=server_detail['alert_emails']
                                        )
                                except Exception as alert_error:
                                    logger.error(f"Error processing alerts: {alert_error}", exc_info=True)
                                    # Don't fail the monitoring cycle if alerts fail
                                
                            except Exception as db_error:
                                logger.error(f"Database error storing GPU metrics: {db_error}", exc_info=True)
                    
                    except Exception as e:
                        logger.error(f"Error processing {server.get('server_name')}: {e}", exc_info=True)
                    
                    finally:
                        # Always delete the temporary RSA key file
                        if temp_key_file and os.path.exists(temp_key_file):
                            try:
                                os.unlink(temp_key_file)
                                logger.debug(f"Temporary RSA key file deleted: {temp_key_file}")
                            except Exception as cleanup_error:
                                logger.warning(f"Failed to delete temporary key file: {cleanup_error}")
                
                except Exception as e:
                    logger.error(f"Error processing {server.get('server_name')}: {e}", exc_info=True)
            
            # Broadcast to WebSocket clients
            if all_metrics:
                logger.info(f"Broadcasting {len(all_metrics)} metrics to {len(self.websocket_connections)} WebSocket clients")
                await self.broadcast_metrics(all_metrics)
            else:
                logger.warning("No metrics collected to broadcast")
            
            logger.info("=== GPU metrics collection cycle completed ===")
        
        except Exception as e:
            logger.error(f"Collection error: {e}", exc_info=True)
    
    def start(self):
        if not self.is_running:
            # Add interval job for regular collection
            self.scheduler.add_job(
                self.collect_and_store_metrics,
                'interval',
                seconds=self.monitoring_interval,
                id='gpu_metrics_job',
                replace_existing=True,
                max_instances=1  # Prevent overlapping executions
            )
            
            # Add one-time job to run immediately on startup
            self.scheduler.add_job(
                self.collect_and_store_metrics,
                'date',
                id='gpu_metrics_startup_job',
                replace_existing=True
            )
            
            self.scheduler.start()
            self.is_running = True
            logger.info(f"GPU monitor started - collecting immediately and then every {self.monitoring_interval} seconds")
    
    def stop(self):
        if self.is_running:
            self.scheduler.shutdown()
            self.is_running = False
            logger.info("GPU monitor stopped")

gpu_monitor = GPUMonitor()

