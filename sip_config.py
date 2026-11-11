import pjsua2 as pj

SIP_DOMAIN = "sip.linphone.org"
SIP_SERVER = f"sip:{SIP_DOMAIN}"

def initialize_sip(username: str, password: str) -> (pj.Endpoint, pj.AccountConfig):
    ep = pj.Endpoint()
    ep.libCreate()

    ep_cfg = pj.EpConfig()
    ep_cfg.logConfig.level = 3
    ep_cfg.logConfig.consoleLevel = 3

    ep.libInit(ep_cfg)

    udp_cfg = pj.TransportConfig()
    udp_cfg.port = 0
    ep.transportCreate(pj.PJSIP_TRANSPORT_UDP, udp_cfg)

    tcp_cfg = pj.TransportConfig()
    tcp_cfg.port = 0
    ep.transportCreate(pj.PJSIP_TRANSPORT_TCP, tcp_cfg)

    ep.libStart()

    acc_cfg = pj.AccountConfig()
    acc_cfg.idUri = f"sip:{username}@{SIP_DOMAIN}"
    acc_cfg.regConfig.registrarUri = SIP_SERVER

    auth = pj.AuthCredInfo(
        "digest",
        "*",
        username,
        0,
        password
    )

    acc_cfg.sipConfig.authCreds.append(auth)

    return ep, acc_cfg
