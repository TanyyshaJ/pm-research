"""Bounded public-page fetcher, with DNS pinning and redirect validation."""
import hashlib
import ipaddress
import re
import socket
import time
from urllib.parse import urljoin, urlsplit, urlunsplit
import httpx
from bs4 import BeautifulSoup
from .provider import ResearchError

def public_target(url):
    try:
        parts = urlsplit(url)
        if parts.scheme not in ('http', 'https') or not parts.hostname or parts.username or parts.password:
            raise ValueError()
        port = parts.port or (443 if parts.scheme == 'https' else 80)
        if port != (443 if parts.scheme == 'https' else 80):
            raise ValueError()
        addresses = socket.getaddrinfo(parts.hostname, port, type=socket.SOCK_STREAM)
        ips = list(dict.fromkeys(a[4][0] for a in addresses))
        if not ips or any(not ipaddress.ip_address(ip).is_global for ip in ips):
            raise ValueError()
        ip = ips[0]
        pinned_host = f'[{ip}]' if ':' in ip else ip
        pinned = urlunsplit((parts.scheme, pinned_host, parts.path or '/', parts.query, ''))
        canonical = urlunsplit((parts.scheme, parts.netloc.lower(), parts.path or '/', parts.query, ''))
        return canonical, pinned, parts.hostname
    except (ValueError, OSError):
        raise ResearchError('Source URL is invalid, unreachable or not on the public web.') from None

def fetch_source(url, run_id):
    deadline = time.monotonic() + 30
    try:
        with httpx.Client(timeout=httpx.Timeout(8, connect=5), trust_env=False, follow_redirects=False) as client:
            for _ in range(4):
                canonical, pinned, host = public_target(url)
                with client.stream('GET', pinned,
                    headers={'Host': host, 'User-Agent': 'FieldnotesResearch/0.2 (public research)'},
                    extensions={'sni_hostname': host}) as response:
                    if response.status_code in (301, 302, 303, 307, 308):
                        url = urljoin(canonical, response.headers.get('location', ''))
                        continue
                    if response.status_code != 200:
                        raise ResearchError(f'Source unavailable (HTTP {response.status_code}).')
                    content_type = response.headers.get('content-type', '')
                    if not any(t in content_type for t in ('text/html', 'text/plain', 'application/xhtml')):
                        raise ResearchError('Source is not a supported HTML or text page.')
                    chunks, size = [], 0
                    for chunk in response.iter_bytes():
                        size += len(chunk)
                        if size > 1000000 or time.monotonic() > deadline:
                            raise ResearchError('Source exceeded the size or time limit.')
                        chunks.append(chunk)
                    raw = b''.join(chunks).decode(response.encoding or 'utf-8', errors='replace')
                soup = BeautifulSoup(raw, 'html.parser')
                title = soup.title.get_text(' ', strip=True) if soup.title else host
                for tag in soup(['script', 'style', 'nav', 'footer', 'header', 'noscript', 'form']):
                    tag.decompose()
                main = soup.find('main') or soup.find('article') or soup
                text = re.sub(r'\s+', ' ', main.get_text(' ', strip=True)).strip()[:24000]
                if len(text) < 150:
                    raise ResearchError('Source has too little readable content (it may require JavaScript or sign-in).')
                source_id = 'src_' + hashlib.sha256(f'{run_id}:{canonical}'.encode()).hexdigest()[:24]
                return {'id': source_id, 'url': canonical, 'title': title[:300], 'content': text,
                    'content_hash': hashlib.sha256(text.encode()).hexdigest(), 'retrieved_at': int(time.time())}
            raise ResearchError('Source redirected too many times.')
    except (httpx.HTTPError, UnicodeError):
        raise ResearchError('Source could not be downloaded securely.') from None
