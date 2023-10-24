import json
import logging
import pickle
import uuid
from hashlib import md5
from pathlib import Path
from typing import Union

import httpx

headers = {
    "Content-Type": "application/json",
    "X-Unity-Version": "2017.4.39f1",
    "User-Agent": "Dalvik/2.1.0 (Linux; U; Android 11; KB2000 Build/RP1A.201005.001)",
}

pass_server = "https://passport.arknights.global"
auth_server = "https://as.arknights.global"
game_server = "https://gs.arknights.global:8443"
version_url = "https://ark-us-static-online.yo-star.com/assetbundle/official/Android/version"

logging.basicConfig(level=logging.INFO, format="[Arknights] %(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


class LoginExpiredException(Exception):
    pass


class LoginFailedException(Exception):
    pass


class Arknights:

    def __init__(
        self,
        email: str,
        device_id: str = "",
        device_id2: str = "",
        relogin: bool = False,
        use_cache: bool = True,
        debug: bool = False,
        session_dir: Union[str, Path] = Path().cwd().joinpath("session"),
    ):
        self.email = email
        self.device_id = device_id or str(uuid.uuid4()).replace("-", "")
        self.device_id2 = device_id2 or str(uuid.uuid4()).replace("-", "")[:16]
        self.session_dir = Path(session_dir)
        self.relogin = relogin
        self.use_cache = use_cache
        self.http = httpx.Client(
            headers=headers
        )
        self.access_token = ""
        self.uid = ""
        self.nickname = ""
        self.secret = ""
        self.seqnum = 1

        if debug:
            logger.setLevel(logging.DEBUG)

    def postPs(self, path: str, data: dict = None, **kwargs) -> httpx.Response:
        """Post to Passport Server"""
        req = self.http.post(pass_server + path, json=data, **kwargs)
        return req.json()

    def postAs(self, path: str, data: dict = None, **kwargs) -> httpx.Response:
        """Post to Auth Server"""
        req = self.http.post(auth_server + path, json=data, **kwargs)
        return req.json()

    def postGs(self, path: str, data: dict = None, **kwargs) -> httpx.Response:
        """Post to Game Server"""
        req = self.http.post(game_server + path, json=data, headers=self.getGsHeaders(), **kwargs)
        return req.json()

    def getGsHeaders(self):
        """get Game Server headers"""
        self.seqnum += 1
        headers["uid"] = self.uid
        headers["secret"] = self.secret
        headers["seqnum"] = str(self.seqnum)
        return headers

    def dump_session(self):
        """Dump session to file"""
        logger.debug(f"Dumping session to {self.session_file}")
        if self.use_cache:
            self.session_dir.mkdir(parents=True, exist_ok=True)
            with open(self.session_file, "wb") as f:
                pickle.dump(
                    (
                        self.device_id,
                        self.device_id2,
                        self.email,
                        self.session_token,
                        self.session_uid,
                        self.uid,
                        self.nickname,
                        self.secret,
                        self.seqnum,
                        self.res_version,
                        self.client_version
                    ),
                    f,
                )

    def load_session(self):
        """Load session from file"""
        logger.debug(f"Loading session from {self.session_file}")
        with open(self.session_file, "rb") as f:
            session = pickle.load(f)
        (
            self.device_id,
            self.device_id2,
            self.email,
            self.session_token,
            self.session_uid,
            self.uid,
            self.nickname,
            self.secret,
            self.seqnum,
            self.res_version,
            self.client_version
        ) = session
        self.seqnum += 1
        session = self.postGs("/account/syncData", {"platform": 1})
        self.dump_session()
        if session.get("statusCode", 0) == 401:
            self.session_file.unlink()
            self.loginWithToken()
        elif session.get("statusCode", 0) != 0:
            raise LoginFailedException(f"Failed to login\nResult: {session}")

    def loginWithToken(self):
        token_data = self.postPs("/user/login", {
            "uid": self.session_uid,
            "captcha_id": "",
            "gen_time": "",
            "storeId": "googleplay",
            "captcha_output": "",
            "deviceId": self.device_id,
            "pass_token": "",
            "platform": "android",
            "lot_number": "",
            "token": self.session_token,
        })
        logger.debug(f"token_data: {token_data}")

        auth_token = self.postAs("/u8/user/v1/getToken", {
            "appId": "1",
            "channelId": "3",
            "deviceId": self.device_id,
            "deviceId2": "",
            "deviceId3": "",
            "extension": json.dumps({
                "uid": self.session_uid,
                "token": token_data["accessToken"]
            }),
            "platform": 1,
            "sign": None,
            "subChannel": "3",
            "worldId": "3"
        })
        logger.debug(f"auth_token: {auth_token}")

        secret_data = self.postGs("/account/login", {
            "assetsVersion": self.res_version,
            "clientVersion": self.client_version,
            "deviceId": self.device_id,
            "deviceId2": "",
            "deviceId3": "",
            "networkVersion": "1",
            "platform": 1,
            "token": auth_token["token"],
            "uid": auth_token["uid"]
        })
        logger.debug(f"secret_data: {secret_data}")

        try:
            self.uid = auth_token["uid"]
            self.secret = secret_data["secret"]
        except KeyError:
            raise LoginFailedException(f"Failed to login\nResult: {secret_data}")

        sync_data = self.postGs("/account/syncData", {"platform": 1})
        logger.debug(f"sync_data: {sync_data}")
        self.nickname = sync_data["user"]["status"]["nickName"]
        self.dump_session()

    def login(self):
        """Login to Arknights"""

        mask_email = self.email[:2] + "*" * (len(self.email) - 4) + self.email[-2:]
        logger.info(f"Logging in {mask_email}")

        res = self.http.get(version_url).json()
        self.res_version = res["resVersion"]
        self.client_version = res["clientVersion"]
        self.session_file = self.session_dir.joinpath(f"{md5(self.email.encode()).hexdigest()}.pickle")

        if self.session_file.exists() and self.use_cache:
            try:
                self.load_session()
                return
            except LoginFailedException:
                self.session_file.unlink()

        logger.debug("No session file found. Logging in...")

        self.postPs("/account/yostar_auth_request", {"account": self.email, "platform": "android", "authlang": "en"})

        code = input("Enter code from email: ")
        yostar_data = self.postPs("/account/yostar_auth_submit", {"code": code, "account": self.email})
        logger.debug(f"yostar_data: {yostar_data}")

        session_data = self.postPs("/user/yostar_createlogin", {
            "yostar_username": self.email,
            "deviceId": self.device_id,
            "yostar_token": yostar_data["yostar_token"],
            "createNew": "0",
            "channelId": "googleplay",
            "yostar_uid": yostar_data["yostar_uid"],
        })
        logger.debug(f"session_data: {session_data}")

        self.session_token = session_data["token"]
        self.session_uid = session_data["uid"]
        self.loginWithToken()

    def updateData(self):
        """Update data"""
        return self.postGs("/account/updateData", {"platform": 1})

    def getSyncData(self):
        """get sync data"""
        return self.postGs("/account/syncData", {"platform": 1})

    def close(self):
        """Close httpx session"""
        self.http.close()
        self.dump_session()
