import random

# ---------- random helpers ----------
def _chrome_ver() -> str:
    major = random.randint(118, 129)
    return f"{major}.0.{random.randint(0, 5999)}.{random.randint(10, 199)}"

def _firefox_ver() -> str:
    return f"{random.randint(112, 130)}.0"

def _webkit_ver() -> str:
    return random.choice(["605.1.15", "605.1.13", "605.1.12"])

def _ios_tuple():
    major = random.choice([15, 16, 17])
    minor = random.randint(0, 7)
    patch = random.choice([0, 1, 2, 3, 4, 5])
    return major, minor, patch

def _android_ver():
    return random.choice(["10", "11", "12", "13", "14"])

# ---------- user-agent generators ----------
def _ua_chrome_android() -> str:
    model = random.choice([
        "Pixel 8", "Pixel 7", "SM-S921B", "SM-S911U", "SM-G996B", "M2012K11AG"
    ])
    return (
        f"Mozilla/5.0 (Linux; Android {_android_ver()}; {model}) "
        f"AppleWebKit/537.36 (KHTML, like Gecko) "
        f"Chrome/{_chrome_ver()} Mobile Safari/537.36"
    )

def _ua_edge_android() -> str:
    cv = _chrome_ver()
    ev_major = cv.split(".", 1)[0]
    model = random.choice(["LE2115", "CPH2305", "SM-A536E", "Pixel 6a"])
    return (
        f"Mozilla/5.0 (Linux; Android {_android_ver()}; {model}) "
        f"AppleWebKit/537.36 (KHTML, like Gecko) "
        f"Chrome/{cv} Mobile Safari/537.36 "
        f"EdgA/{ev_major}.0.{random.randint(1000, 9999)}.{random.randint(10,199)}"
    )

def _ua_firefox_android() -> str:
    model = random.choice(["Pixel 8", "SM-S711B", "Pixel 6", "GM1911"])
    ver = _firefox_ver()
    return (
        f"Mozilla/5.0 (Android {_android_ver()}; Mobile; rv:{ver}; {model}) "
        f"Gecko/20100101 Firefox/{ver}"
    )

def _ua_safari_ios(iphone: bool = True) -> str:
    major, minor, patch = _ios_tuple()
    device = "iPhone" if iphone else "iPad"
    mobile_token = "Mobile/15E148"
    return (
        f"Mozilla/5.0 ({device}; CPU {device} OS {major}_{minor}_{patch} like Mac OS X) "
        f"AppleWebKit/{_webkit_ver()} (KHTML, like Gecko) "
        f"Version/{random.choice(['16.3','16.6','17.2','17.4','17.5'])} "
        f"{mobile_token} Safari/{_webkit_ver()}"
    )

# ---------- exported helpers ----------
def get_useragent() -> str:
    """
    Return a realistic **mobile** User-Agent string (Android/iOS/iPadOS only).
    """
    choices = [
        (_ua_chrome_android,          40),
        (_ua_edge_android,            10),
        (_ua_firefox_android,         10),
        (lambda: _ua_safari_ios(True),30),
        (lambda: _ua_safari_ios(False),10),
    ]
    funcs, weights = zip(*choices)
    return random.choices(funcs, weights=weights, k=1)[0]()