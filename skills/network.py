import asyncio
import logging
import socket
import subprocess

import httpx

from skills.base import BaseSkill

log = logging.getLogger("zari")


class NetworkSkill(BaseSkill):
    priority = 85
    timeout = 15.0

    async def execute(self, query: str) -> dict | None:
        text = query.lower().strip()
        if not text:
            return None

        if any(w in text for w in ["ip", "mening ip", "address"]):
            return await self._get_public_ip()

        if any(w in text for w in ["ping", "ping qil", "tekshir"]):
            return await self._ping(text)

        if any(w in text for w in ["dns", "domain"]):
            return await self._dns_lookup(text)

        return None

    async def _get_public_ip(self) -> dict:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get("https://api.ipify.org?format=json")
                data = resp.json()
                ip = data["ip"]

            hostname = socket.gethostname()
            local_ip = ""
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                s.connect(("8.8.8.8", 80))
                local_ip = s.getsockname()[0]
                s.close()
            except Exception:
                pass

            response = f"Tashqi IP: {ip}"
            if local_ip:
                response += f"\nMahalliy IP: {local_ip}"
            response += f"\nHostname: {hostname}"
            return {"response": response, "context": f"{ip} | {local_ip}", "source": "network"}
        except Exception as e:
            log.warning("IP xatosi: %s", e)
            return {"response": "IP manzilni olishda xatolik.", "context": "", "source": "network"}

    async def _ping(self, text: str) -> dict:
        host = text.replace("ping", "").replace("ping qil", "").replace("tekshir", "").strip()
        host = host.split()[-1] if host.split() else "8.8.8.8"

        try:
            proc = await asyncio.create_subprocess_exec(
                "ping",
                "-c",
                "2",
                "-W",
                "3",
                host,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=10)
            output = stdout.decode() or stderr.decode()

            if "ms" in output:
                lines = [line.strip() for line in output.split("\n") if "ms" in line]
                response = f"{host} ga ping:\n" + "\n".join(lines[:3])
            else:
                response = f"{host} ga ulanish yo'q."
            return {"response": response, "context": output[:300], "source": "network"}
        except TimeoutError:
            return {"response": f"{host} ga ping timeout (10 soniya).", "context": "", "source": "network"}
        except Exception as e:
            log.warning("Ping xatosi: %s", e)
            return {"response": f"Ping xatosi: {host}", "context": "", "source": "network"}

    async def _dns_lookup(self, text: str) -> dict:
        parts = text.replace("dns", "").replace("domain", "").strip().split()
        if not parts:
            return None
        domain = parts[-1]
        if not domain or "." not in domain:
            return None

        try:
            result = socket.getaddrinfo(domain, 80)
            ips = list(set(r[4][0] for r in result))
            response = f"{domain} uchun DNS:\n" + "\n".join(f"  * {ip}" for ip in ips[:5])
            return {"response": response, "context": str(ips), "source": "network"}
        except socket.gaierror:
            return {"response": f"{domain} uchun DNS topilmadi.", "context": "", "source": "network"}
        except Exception as e:
            log.warning("DNS xatosi: %s", e)
            return {"response": f"DNS xatosi: {domain}", "context": "", "source": "network"}
