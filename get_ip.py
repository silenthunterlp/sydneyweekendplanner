import urllib.request

def get_public_ip():
    url = "https://ifconfig.io"
    req = urllib.request.Request(url, headers={"User-Agent": "curl/7.0"})
    with urllib.request.urlopen(req) as response:
        ip = response.read().decode().strip()
    return ip

if __name__ == "__main__":
    ip = get_public_ip()
    print("Your public IP:", ip)
